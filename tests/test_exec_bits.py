"""Exec-bit guard (tools/check_exec_bits.py) — spec 0002, CB-1..CB-5.

Each test builds a throw-away git repository under pytest's tmp_path (outside the repo) and runs
the tool as a subprocess, exactly as scripts/check does.
"""
import os
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
TOOL = REPO / "tools" / "check_exec_bits.py"
SHEBANG = "#!/bin/sh\necho hi\n"


# Isolated from the caller's git: no GIT_DIR / GIT_INDEX_FILE leaking in (e.g. check run from a
# hook would otherwise write the real index) and no global/system config (e.g. core.fsmonitor
# would start a daemon — docs/testing.md, Resource hygiene).
ENV = {k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")}
ENV.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)


def git(cwd, *args, stdin=None):
    return subprocess.run(
        ["git", *args], cwd=cwd, input=stdin, env=ENV, capture_output=True, text=True, check=True,
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q")
    return tmp_path


def add(repo, path, content, executable=False):
    file = repo / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(content, newline="\n")
    git(repo, "add", "--", path)
    git(repo, "update-index", "--chmod=+x" if executable else "--chmod=-x", "--", path)


def run_tool(cwd, env=ENV, *args):
    return subprocess.run(
        [sys.executable, str(TOOL), *args], cwd=cwd, env=env, capture_output=True, text=True,
    )


# --- CB-1 -----------------------------------------------------------------------------------

def test_reports_shebang_file_without_exec_bit(repo):
    """CB-1: a tracked 100644 file starting with '#!' fails the check, named with its fix."""
    add(repo, "scripts/build", SHEBANG)
    add(repo, "tools/run me.sh", SHEBANG)

    result = run_tool(repo)

    assert result.returncode == 1
    assert "scripts/build" in result.stdout
    assert "git update-index --chmod=+x scripts/build" in result.stdout
    assert "tools/run me.sh" in result.stdout
    assert "git update-index --chmod=+x 'tools/run me.sh'" in result.stdout


def test_report_is_utf8_and_keeps_non_ascii_paths(repo):
    """CB-1: the path is printed as it is — also non-ASCII — in UTF-8 on every platform."""
    add(repo, "araçlar/çalıştır.sh", SHEBANG)

    result = subprocess.run([sys.executable, str(TOOL)], cwd=repo, env=ENV, capture_output=True)

    assert result.returncode == 1
    out = result.stdout.decode("utf-8")  # strict: a non-UTF-8 byte raises
    assert "araçlar/çalıştır.sh starts with '#!' but is 100644" in out


@pytest.mark.skipif(sys.platform == "win32", reason="NTFS cannot hold a non-UTF-8 file name")
def test_report_keeps_non_utf8_path_bytes(repo):
    """CB-1: a non-UTF-8 file name (possible on POSIX) is printed byte for byte."""
    name = b"bad\xff.sh"
    with open(os.path.join(os.fsencode(repo), name), "wb") as f:
        f.write(SHEBANG.encode())
    subprocess.run([b"git", b"add", b"--", name], cwd=repo, env=ENV, check=True)
    subprocess.run([b"git", b"update-index", b"--chmod=-x", b"--", name], cwd=repo, env=ENV,
                   check=True)

    result = subprocess.run([sys.executable, str(TOOL)], cwd=repo, env=ENV, capture_output=True)

    assert result.returncode == 1
    assert b"exec-bits: bad\xff.sh starts with" in result.stdout


@pytest.mark.skipif(sys.platform == "win32", reason="NTFS cannot hold a non-UTF-8 file name")
def test_repository_root_with_non_utf8_bytes_is_handled(tmp_path):
    """CB-1: a repository whose own root path is not UTF-8 (POSIX) is checked, not crashed."""
    root = os.path.join(os.fsencode(tmp_path), b"repo\xff")
    os.mkdir(root)
    subprocess.run([b"git", b"init", b"-q"], cwd=root, env=ENV, check=True)
    with open(os.path.join(root, b"build"), "wb") as f:
        f.write(SHEBANG.encode())
    subprocess.run([b"git", b"add", b"--", b"build"], cwd=root, env=ENV, check=True)
    subprocess.run([b"git", b"update-index", b"--chmod=-x", b"--", b"build"], cwd=root, env=ENV,
                   check=True)

    result = subprocess.run([sys.executable, str(TOOL)], cwd=root, env=ENV, capture_output=True)

    assert result.returncode == 1, result.stderr
    assert b"exec-bits: build starts with" in result.stdout


@pytest.mark.skipif(sys.platform == "win32", reason="Windows drops trailing spaces from names")
def test_repository_root_with_surrounding_spaces_is_kept(tmp_path):
    """CB-1: only git's newline is cut from the root path; its own spaces stay."""
    root = tmp_path / " repo "
    root.mkdir()
    git(root, "init", "-q")
    add(root, "build", SHEBANG)

    result = run_tool(root)

    assert result.returncode == 1, result.stderr
    assert "exec-bits: build starts with" in result.stdout


def test_ignores_symlink_and_submodule_entries(repo):
    """CB-1: symlink (120000) and submodule (160000) entries are not judged."""
    add(repo, "scripts/ok", SHEBANG, executable=True)
    sha = git(repo, "hash-object", "-w", "--stdin", stdin="scripts/ok")
    git(repo, "update-index", "--add", "--cacheinfo", f"120000,{sha},link-to-script")
    git(repo, "update-index", "--add", "--cacheinfo", f"160000,{sha},vendor/sub")
    # Shebang content at both paths: only the mode filter keeps them out of the report
    # (e.g. a symlink checked out as a plain file with core.symlinks=false).
    (repo / "link-to-script").write_text(SHEBANG, newline="\n")
    (repo / "vendor").mkdir()
    (repo / "vendor" / "sub").write_text(SHEBANG, newline="\n")

    result = run_tool(repo)

    assert result.returncode == 0, result.stdout
    assert "link-to-script" not in result.stdout
    assert "vendor/sub" not in result.stdout


# --- CB-2 -----------------------------------------------------------------------------------

def test_passes_when_every_shebang_file_is_executable(repo):
    """CB-2: every shebang file is 100755 → the check passes silently."""
    add(repo, "scripts/build", SHEBANG, executable=True)
    add(repo, "scripts/test", SHEBANG, executable=True)

    result = run_tool(repo)

    assert result.returncode == 0
    assert "exec-bits:" not in result.stdout


def test_current_repository_passes():
    """CB-2: this repository is in the passing state today.

    CB-5: a copy without .git (e.g. a zip) skips with the note instead. Judged by .git, not by
    git: an unreadable .git (dubious ownership) must stay red, never pass as a skip. The ceiling
    matches scripts/check.conf: a copy inside another repository never judges the outer one.
    """
    result = run_tool(REPO, {**ENV, "GIT_CEILING_DIRECTORIES": str(REPO.parent)})
    assert result.returncode == 0, result.stdout
    if (REPO / ".git").exists():  # a directory, or a file in a linked worktree
        assert "skipped" not in result.stdout
    else:
        assert "skipped - not a git work tree" in result.stdout


# --- CB-3 -----------------------------------------------------------------------------------

def test_ignores_templates_under_adapters(repo):
    """CB-3: shebang templates under adapters/ are not executed in place and are not reported."""
    add(repo, "adapters/claude-code/.claude/hooks/hook.sh", SHEBANG)

    result = run_tool(repo)

    assert result.returncode == 0
    assert "adapters/" not in result.stdout


def test_subdirectory_argument_is_judged_from_the_repo_root(repo):
    """CB-1/CB-3: started from a subdirectory, paths and the adapters/ exclusion stay root-based."""
    add(repo, "adapters/claude-code/hook.sh", SHEBANG)
    add(repo, "scripts/build", SHEBANG)

    result = run_tool(repo, ENV, str(repo / "adapters"))

    assert result.returncode == 1
    assert "exec-bits: scripts/build " in result.stdout
    assert "hook.sh" not in result.stdout


# --- CB-4 -----------------------------------------------------------------------------------

def test_ignores_files_without_shebang(repo):
    """CB-4: files that do not start with '#!' are never reported, whatever their mode."""
    add(repo, "app.py", "print('hi')\n")
    add(repo, "scripts/check.conf", "# conf\nlint: true\n")
    add(repo, "notes/readme.md", " #! not at the start\n")

    result = run_tool(repo)

    assert result.returncode == 0
    assert "exec-bits:" not in result.stdout


# --- CB-5 -----------------------------------------------------------------------------------

def test_skips_outside_a_git_work_tree(tmp_path):
    """CB-5: outside a git work tree the check is skipped with a note, not failed."""
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / "script").write_text(SHEBANG)

    result = run_tool(plain, env={**ENV, "GIT_CEILING_DIRECTORIES": str(tmp_path)})

    assert result.returncode == 0
    assert "skipped - not a git work tree (" in result.stdout  # git's own reason is named


def test_missing_directory_argument_is_a_usage_error(tmp_path):
    """CB-5 boundary: a non-existent [dir] is a usage error (exit 2), never a silent skip."""
    result = run_tool(tmp_path, ENV, str(tmp_path / "does-not-exist"))

    assert result.returncode == 2
    assert "not a directory" in result.stderr
    assert "skipped" not in result.stdout


@pytest.mark.skipif(sys.platform == "win32" or os.geteuid() == 0,
                    reason="needs POSIX permissions that bind (not root)")
def test_unenterable_directory_is_not_reported_as_missing_git(repo):
    """CB-5 boundary: only a missing git is a skip; a directory git cannot enter is red."""
    locked = repo / "locked"
    locked.mkdir()
    locked.chmod(0)
    try:
        result = run_tool(repo, ENV, str(locked))
    finally:
        locked.chmod(0o755)  # let pytest clean tmp_path up

    assert result.returncode != 0
    assert "skipped" not in result.stdout


def test_skips_when_git_is_not_installed(repo):
    """CB-5: without a git executable the check is skipped with a note, not failed."""
    add(repo, "scripts/build", SHEBANG)
    env = {k: v for k, v in ENV.items() if k.upper() != "PATH"}
    env["PATH"] = ""

    result = run_tool(repo, env=env)

    assert result.returncode == 0
    assert "skipped - git is not installed" in result.stdout
