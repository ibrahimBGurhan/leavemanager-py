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


# --- spec 0003: an unreadable .git fails the step -------------------------------------------

def make_unreadable(root, case):
    """A .git under root that git cannot read; returns the env (with ceiling) to run git in."""
    env = {**ENV, "GIT_CEILING_DIRECTORIES": str(root.parent)}
    if case == "dubious":
        git(root, "init", "-q")
        env["GIT_TEST_ASSUME_DIFFERENT_OWNER"] = "1"
    elif case == "corrupt-head":
        git(root, "init", "-q")
        (root / ".git" / "HEAD").write_text("garbage\n")
    elif case == "dangling-gitfile":
        (root / ".git").write_text(f"gitdir: {root / 'nowhere'}\n")
    elif case == "empty-git-dir":
        (root / ".git").mkdir()
    return env


def git_reason(cwd, env):
    """First line of git's own error for this directory; asserts git really fails there."""
    result = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd, env=env,
                            capture_output=True, text=True)
    assert result.returncode != 0, "setup: git can read this repository"
    return result.stderr.strip().splitlines()[0]


@pytest.mark.parametrize("case", ["dubious", "corrupt-head", "dangling-gitfile", "empty-git-dir"])
def test_unreadable_git_fails_the_step(tmp_path, case):
    """0003 CB-1..CB-3: a .git git cannot read is red with git's reason, never a skip."""
    env = make_unreadable(tmp_path, case)
    reason = git_reason(tmp_path, env)

    result = run_tool(tmp_path, env)

    assert result.returncode == 1
    lines = result.stdout.splitlines()
    assert len(lines) == 1 and lines[0].startswith("exec-bits:")
    assert reason in lines[0]
    assert "skipped" not in result.stdout


def test_unreadable_git_is_found_from_a_subdirectory(tmp_path):
    """0003 CB-1: a [dir] below the unreadable .git gets the same red."""
    env = make_unreadable(tmp_path, "corrupt-head")
    sub = tmp_path / "sub"
    sub.mkdir()

    result = run_tool(tmp_path, env, str(sub))

    assert result.returncode == 1
    assert result.stdout.startswith("exec-bits:")


def test_git_missing_wins_over_an_unreadable_git(tmp_path):
    """0003 PB-2: without git, a .git cannot be judged, so the check is skipped."""
    env = make_unreadable(tmp_path, "corrupt-head")
    env = {k: v for k, v in env.items() if k.upper() != "PATH"}
    env["PATH"] = ""

    result = run_tool(tmp_path, env)

    assert result.returncode == 0
    assert "skipped - git is not installed" in result.stdout


def test_unreadable_git_above_the_ceiling_is_not_judged(tmp_path):
    """0003 PB-1: a .git above the project root (the ceiling) is never looked at."""
    outer = tmp_path / "outer"
    (outer / ".git").mkdir(parents=True)
    inner = outer / "inner"
    inner.mkdir()

    result = run_tool(inner, {**ENV, "GIT_CEILING_DIRECTORIES": str(outer)})

    assert result.returncode == 0
    assert "skipped - not a git work tree" in result.stdout


# --- spec 0004: the ceiling is compared by its physical path -----------------------------------

def outer_repo_with_inner_dir(tmp_path):
    """An outer dir holding a .git, with an inner dir to run in. The long name has a distinct
    8.3 short name; "outer" would be its own short name and prove nothing."""
    outer = tmp_path / "outer-with-a-long-name"
    (outer / ".git").mkdir(parents=True)
    inner = outer / "inner"
    inner.mkdir()
    return outer, inner


@pytest.mark.skipif(sys.platform != "win32", reason="8.3 short names exist only on Windows")
def test_ceiling_given_as_a_short_name_is_honoured(tmp_path):
    """0004 PB-1/PB-2: a short-name ceiling still stops the search above the project root."""
    import ctypes
    outer, inner = outer_repo_with_inner_dir(tmp_path)
    buf = ctypes.create_unicode_buffer(32768)
    ctypes.windll.kernel32.GetShortPathNameW(str(outer), buf, len(buf))
    if not buf.value or buf.value.lower() == str(outer).lower():
        pytest.skip("8.3 short names are disabled on this volume")

    result = run_tool(inner, {**ENV, "GIT_CEILING_DIRECTORIES": buf.value})

    assert result.returncode == 0
    assert "skipped - not a git work tree" in result.stdout
    assert "exec-bits:" not in result.stdout


def test_ceiling_given_through_a_symlink_is_honoured(tmp_path):
    """0004 PB-1/PB-2: a ceiling reached through a symlink still stops the search."""
    outer, inner = outer_repo_with_inner_dir(tmp_path)
    link = tmp_path / "link"
    try:
        link.symlink_to(outer, target_is_directory=True)
    except OSError as e:
        if sys.platform != "win32":
            raise  # POSIX must run this case (CI), never skip it
        pytest.skip(f"no privilege to create symlinks on Windows ({e.winerror})")

    result = run_tool(inner, {**ENV, "GIT_CEILING_DIRECTORIES": str(link)})

    assert result.returncode == 0
    assert "skipped - not a git work tree" in result.stdout
    assert "exec-bits:" not in result.stdout
