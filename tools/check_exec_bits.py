"""Exec-bit guard — spec 0002 (issue #5).

Reports every tracked file that starts with '#!' but is committed as 100644, because Linux CI
cannot execute it (PR #1: "Permission denied", exit 126). Reads modes from the git index, not the
file system: Windows has no exec bit, and the index is what CI checks out.

    python tools/check_exec_bits.py [dir]    # any directory inside the repo; default: cwd

Exit 0 = clean (or skipped outside a git work tree), 1 = violations found, 2 = [dir] is not a
directory.
"""
import pathlib
import shlex
import subprocess
import sys

# Templates copied by scripts/init (which applies chmod +x itself); never executed in place.
EXCLUDED_PREFIXES = ("adapters/",)


def git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, check=True).stdout


def tracked_non_executable_files(repo):
    """(path, ...) of regular 100644 files in the index; symlinks and submodules are skipped."""
    for entry in git(repo, "ls-files", "-s", "-z").split(b"\0"):
        if not entry:
            continue
        meta, path = entry.split(b"\t", 1)
        if meta.split(b" ", 1)[0] == b"100644":
            yield path.decode("utf-8", "surrogateescape")


def starts_with_shebang(file):
    try:
        with open(file, "rb") as f:
            return f.read(2) == b"#!"
    except OSError:  # listed in the index but missing from the work tree
        return False


def main(argv):
    # UTF-8 everywhere: a Windows pipe would otherwise use the ANSI code page and garble paths.
    # surrogateescape: a non-UTF-8 file name (POSIX) is written back byte for byte, so the
    # printed fix command still works when copied.
    sys.stdout.reconfigure(encoding="utf-8", errors="surrogateescape")
    start = pathlib.Path(argv[1]) if len(argv) > 1 else pathlib.Path.cwd()
    if not start.is_dir():
        # a usage error, not a skip: otherwise it would surface as "git is not installed"
        print(f"exec-bits: not a directory: {start}", file=sys.stderr)
        return 2
    try:
        # paths, the adapters/ exclusion and the fix command are all relative to the repo root
        top = git(start, "rev-parse", "--show-toplevel").strip()
        repo = pathlib.Path(top.decode("utf-8", "surrogateescape"))
    except FileNotFoundError:  # [dir] exists (checked above), so only git itself can be missing
        print("NOTE: exec-bit check skipped - git is not installed")
        return 0
    except subprocess.CalledProcessError as e:
        # name git's own reason, so an unexpected skip (e.g. safe.directory) is visible
        reason = e.stderr.decode("utf-8", "replace").strip().splitlines()
        print("NOTE: exec-bit check skipped - not a git work tree"
              + (f" ({reason[0]})" if reason else ""))
        return 0

    violations = [
        path for path in tracked_non_executable_files(repo)
        if not path.startswith(EXCLUDED_PREFIXES) and starts_with_shebang(repo / path)
    ]
    for path in violations:
        print(f"exec-bits: {path} starts with '#!' but is 100644"
              f" - fix: git update-index --chmod=+x {shlex.quote(path)}")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
