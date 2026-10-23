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


def git(cwd, *args, stdin=None):
    return subprocess.run(
        ["git", *args], cwd=cwd, input=stdin, capture_output=True, text=True, check=True,
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


def run_tool(cwd, env=None):
    return subprocess.run(
        [sys.executable, str(TOOL)], cwd=cwd, env=env, capture_output=True, text=True,
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

    result = subprocess.run([sys.executable, str(TOOL)], cwd=repo, capture_output=True)

    assert result.returncode == 1
    out = result.stdout.decode("utf-8")  # strict: a non-UTF-8 byte raises
    assert "araçlar/çalıştır.sh starts with '#!' but is 100644" in out


def test_ignores_symlink_and_submodule_entries(repo):
    """CB-1: symlink (120000) and submodule (160000) entries are not judged."""
    add(repo, "scripts/ok", SHEBANG, executable=True)
    sha = git(repo, "hash-object", "-w", "--stdin", stdin="scripts/ok")
    git(repo, "update-index", "--add", "--cacheinfo", f"120000,{sha},link-to-script")
    git(repo, "update-index", "--add", "--cacheinfo", f"160000,{sha},vendor/sub")

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
    """CB-2: this repository is in the passing state today."""
    result = run_tool(REPO)
    assert result.returncode == 0, result.stdout


# --- CB-3 -----------------------------------------------------------------------------------

def test_ignores_templates_under_adapters(repo):
    """CB-3: shebang templates under adapters/ are not executed in place and are not reported."""
    add(repo, "adapters/claude-code/.claude/hooks/hook.sh", SHEBANG)

    result = run_tool(repo)

    assert result.returncode == 0
    assert "adapters/" not in result.stdout


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

    result = run_tool(plain, env={**os.environ, "GIT_CEILING_DIRECTORIES": str(tmp_path)})

    assert result.returncode == 0
    assert "skipped" in result.stdout


def test_skips_when_git_is_not_installed(repo):
    """CB-5: without a git executable the check is skipped with a note, not failed."""
    add(repo, "scripts/build", SHEBANG)
    env = {k: v for k, v in os.environ.items() if k.upper() != "PATH"}
    env["PATH"] = ""

    result = run_tool(repo, env=env)

    assert result.returncode == 0
    assert "skipped" in result.stdout
