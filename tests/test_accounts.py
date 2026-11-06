"""User accounts and the `hesap-ac` command-line tool — spec 0018 (ADR-0002).

The tool runs in-process through Flask's CLI runner on a SqliteStorage in a pytest tmp dir: the
`storage` and `accounts` seams are swapped with monkeypatch (plan 0018 Risk 5). The runner feeds
the hidden password prompts from its input and does not echo them. The "database cannot open"
case runs the real `flask --app app hesap-ac` in a child process. Nothing is written in the repo.
"""
import ast
import logging
import os
import pathlib
import subprocess
import sys

import pytest

import app as leave_app
from domain.accounts import AccountService
from storage.demo import demo_employees, demo_requests
from storage.memory import MemoryStorage
from storage.sqlite import SqliteStorage

ROOT = pathlib.Path(__file__).resolve().parent.parent
PASSWORD = "gizli parola 1"          # 14 characters, used only in tests
OTHER = "baska parola 22"


@pytest.fixture
def db(tmp_path, monkeypatch):
    """The tool's storage: a SQLite file with the demo employees (ids 1-5)."""
    path = tmp_path / "leave.db"
    store = SqliteStorage(path, seed_records=(demo_employees(), demo_requests()))
    monkeypatch.setattr(leave_app, "storage", store)
    monkeypatch.setattr(leave_app, "accounts", AccountService(store, leave_app.hasher))
    yield path
    store.close()


def run_tool(*args, passwords=(PASSWORD, PASSWORD)):
    feed = "".join(p + "\n" for p in passwords)
    return leave_app.app.test_cli_runner().invoke(args=["hesap-ac", *args], input=feed)


def stored_accounts():
    return leave_app.storage.accounts()


def reopen(path):
    leave_app.storage.close()
    store = SqliteStorage(path)
    try:
        return store.accounts()
    finally:
        store.close()


# --- AC-1 -----------------------------------------------------------------------------------

def test_cli_creates_ik_and_personel_accounts_that_survive_reopen(db, monkeypatch):
    ik = run_tool("--eposta", "ik@firma.com", "--rol", "IK")
    personel = run_tool("--eposta", "ayse@firma.com", "--rol", "Personel", "--personel", "1",
                        passwords=(OTHER, OTHER))
    assert ik.exit_code == 0 and personel.exit_code == 0, ik.output + personel.output
    accounts = reopen(db)
    assert [(a["email"], a["role"], a["employee_id"], a["active"], a["failed_attempts"],
             a["locked_until"]) for a in accounts] == [
        ("ik@firma.com", "IK", None, True, 0, None),
        ("ayse@firma.com", "Personel", 1, True, 0, None)]


# --- AC-2 -----------------------------------------------------------------------------------

def test_cli_password_prompts_are_hidden(db):
    result = run_tool("--eposta", "ik@firma.com", "--rol", "IK")
    assert result.exit_code == 0
    assert "Şifre: " in result.output and "Şifre (tekrar): " in result.output
    assert PASSWORD not in result.output


def test_cli_mismatched_passwords_create_nothing(db):
    result = run_tool("--eposta", "ik@firma.com", "--rol", "IK", passwords=(PASSWORD, OTHER))
    assert result.exit_code != 0
    assert "Şifreler eşleşmiyor." in result.output
    assert stored_accounts() == []


@pytest.mark.parametrize("option", ["--sifre", "--password", "--parola"])
def test_cli_takes_no_password_option(db, option):
    result = run_tool("--eposta", "ik@firma.com", "--rol", "IK", option, PASSWORD)
    assert result.exit_code != 0
    assert stored_accounts() == []


def test_cli_ignores_password_in_the_environment(db, monkeypatch):
    monkeypatch.setenv("PASSWORD", PASSWORD)
    monkeypatch.setenv("SIFRE", PASSWORD)
    result = run_tool("--eposta", "ik@firma.com", "--rol", "IK", passwords=())
    assert result.exit_code != 0       # it still asks; with no input the prompt is aborted
    assert stored_accounts() == []


# --- AC-3 -----------------------------------------------------------------------------------

@pytest.mark.parametrize("password, ok", [("a" * 11, False), ("abcdefghijkl", True)],
                         ids=["11", "12-lowercase"])
def test_password_length_boundary(db, password, ok):
    result = run_tool("--eposta", "ik@firma.com", "--rol", "IK", passwords=(password, password))
    if ok:
        assert result.exit_code == 0 and len(stored_accounts()) == 1
    else:
        assert result.exit_code != 0
        assert "Şifre en az 12 karakter olmalı." in result.output
        assert stored_accounts() == []


def test_password_spaces_are_part_of_it(db):
    password = " abcdefghij "          # 12 with the spaces, 10 without
    result = run_tool("--eposta", "ik@firma.com", "--rol", "IK", passwords=(password, password))
    assert result.exit_code == 0
    stored = stored_accounts()[0]["password_hash"]
    assert leave_app.hasher.verify(stored, password)
    assert not leave_app.hasher.verify(stored, password.strip())


# --- AC-4 -----------------------------------------------------------------------------------

def test_plain_password_is_nowhere(db, caplog):
    caplog.set_level(logging.DEBUG)
    result = run_tool("--eposta", "ik@firma.com", "--rol", "IK")
    assert result.exit_code == 0
    stored = stored_accounts()[0]["password_hash"]
    assert PASSWORD not in stored
    leave_app.storage.close()
    files = [f for f in db.parent.iterdir() if f.name.startswith(db.name)]
    assert files
    for f in files:
        assert PASSWORD.encode("utf-8") not in f.read_bytes()
    assert PASSWORD not in result.output and stored not in result.output
    for record in caplog.records:
        assert PASSWORD not in record.getMessage() and stored not in record.getMessage()


def test_hash_verifies_only_the_right_password(db):
    run_tool("--eposta", "ik@firma.com", "--rol", "IK")
    stored = stored_accounts()[0]["password_hash"]
    assert leave_app.hasher.verify(stored, PASSWORD)
    assert not leave_app.hasher.verify(stored, OTHER)
    assert not leave_app.hasher.verify(stored, PASSWORD.upper())


def test_same_password_different_hashes(db):
    run_tool("--eposta", "a@firma.com", "--rol", "IK")
    run_tool("--eposta", "b@firma.com", "--rol", "IK")
    first, second = (a["password_hash"] for a in stored_accounts())
    assert first != second
    assert leave_app.hasher.verify(first, PASSWORD) and leave_app.hasher.verify(second, PASSWORD)


# --- AC-5 -----------------------------------------------------------------------------------

def test_email_is_normalized_and_unique(db):
    assert run_tool("--eposta", "  Ali.Veli@Firma.com ", "--rol", "IK").exit_code == 0
    assert [a["email"] for a in stored_accounts()] == ["ali.veli@firma.com"]
    again = run_tool("--eposta", "ali.veli@FIRMA.com", "--rol", "IK")
    assert again.exit_code != 0
    assert "Bu e-posta adresiyle bir hesap zaten var: ali.veli@firma.com" in again.output
    assert len(stored_accounts()) == 1


@pytest.mark.parametrize("email", ["alifirma.com", "ali@@firma.com", "a@b@firma.com",
                                   "@firma.com", "ali@", "ali veli@firma.com", "ali@fir\tma.com",
                                   "", "   "])
def test_malformed_emails_rejected(db, email):
    result = run_tool("--eposta", email, "--rol", "IK")
    assert result.exit_code != 0
    assert "Geçersiz e-posta adresi" in result.output
    assert "Şifre" not in result.output          # asked before the password (plan Risk 4)
    assert stored_accounts() == []


# --- AC-6 -----------------------------------------------------------------------------------

@pytest.mark.parametrize("role, employee, message", [
    ("Mudur", "", "Bilinmeyen rol: 'Mudur'. Geçerli roller: Personel, Yonetici, IK."),
    ("", "", "Bilinmeyen rol: ''."),
    ("Personel", "", "Personel hesabı bir personele bağlanmalı: --personel <numara>."),
    ("Yonetici", "", "Yonetici hesabı bir personele bağlanmalı: --personel <numara>."),
    ("Personel", "99", "Personel bulunamadı: 99."),
    ("IK", "99", "Personel bulunamadı: 99."),
    ("Yonetici", "abc", "Personel bulunamadı: abc."),
], ids=["unknown-role", "no-role", "personel-unlinked", "yonetici-unlinked", "personel-missing",
        "ik-missing", "not-a-number"])
def test_role_and_employee_rules(db, role, employee, message):
    args = ["--eposta", "x@firma.com", "--rol", role]
    if employee:
        args += ["--personel", employee]
    result = run_tool(*args)
    assert result.exit_code != 0
    assert message in result.output
    assert "Hesap oluşturulmadı." in result.output
    assert "Şifre" not in result.output
    assert stored_accounts() == []


def test_employee_with_an_account_gets_no_second_one(db):
    assert run_tool("--eposta", "ayse@firma.com", "--rol", "Personel", "--personel", "1").exit_code == 0
    second = run_tool("--eposta", "ayse2@firma.com", "--rol", "Yonetici", "--personel", "1")
    assert second.exit_code != 0
    assert "Bu personelin zaten bir hesabı var: 1." in second.output
    assert [a["email"] for a in stored_accounts()] == ["ayse@firma.com"]


def test_role_spelling_is_normalized(db):
    assert run_tool("--eposta", "ik@firma.com", "--rol", "ik").exit_code == 0
    assert run_tool("--eposta", "mehmet@firma.com", "--rol", "YONETICI",
                    "--personel", "2").exit_code == 0
    assert [a["role"] for a in stored_accounts()] == ["IK", "Yonetici"]


@pytest.mark.parametrize("first, second", [
    (("ik@firma.com", None), ("ik@firma.com", None)),
    (("ayse@firma.com", 1), ("ayse2@firma.com", 1)),
], ids=["same-email", "same-employee"])
def test_concurrent_tool_runs_create_one_account(db, monkeypatch, first, second):
    """Review F-1: another `hesap-ac` saves the same email / employee after this run checked.
    The database refuses the second one; the tool says so in Turkish, exits 1, no traceback."""
    store = leave_app.storage
    store.add_account({"email": first[0], "password_hash": "h", "role": "Personel",
                       "employee_id": first[1], "active": True, "failed_attempts": 0,
                       "locked_until": None})
    monkeypatch.setattr(store, "accounts", lambda: [])   # this run's checks saw no account yet
    role = "Personel" if second[1] else "IK"
    args = ["--eposta", second[0], "--rol", role] + (["--personel", "1"] if second[1] else [])
    result = run_tool(*args)
    assert result.exit_code == 1
    assert "Hesap kaydedilemedi (veritabanı:" in result.output
    assert "Hesap oluşturulmadı." in result.output
    assert "Traceback" not in result.output and not isinstance(result.exception, AssertionError)
    assert PASSWORD not in result.output
    assert [a["email"] for a in reopen(db)] == [first[0]]   # a fresh read of the file


# --- AC-7 -----------------------------------------------------------------------------------
# --- AC-7 -----------------------------------------------------------------------------------

def test_cli_success_output_and_single_info_log(db, caplog):
    caplog.set_level(logging.INFO)
    result = run_tool("--eposta", "ik@firma.com", "--rol", "IK")
    assert result.exit_code == 0
    assert "Hesap oluşturuldu: ik@firma.com (IK)" in result.output
    infos = [r for r in caplog.records if r.levelno == logging.INFO]
    assert [(r.name, r.getMessage()) for r in infos] == [
        ("domain.accounts", "hesap oluşturuldu: ik@firma.com (IK)")]


def test_cli_refuses_memory_storage():
    assert isinstance(leave_app.storage, MemoryStorage)   # the suite's own storage
    result = run_tool("--eposta", "ik@firma.com", "--rol", "IK")
    assert result.exit_code != 0
    assert "Bellek deposu" in result.output and "Hesap oluşturulmadı." in result.output
    assert "Şifre" not in result.output
    assert leave_app.storage.accounts() == []


def test_cli_stops_when_database_cannot_open(tmp_path):
    blocker = tmp_path / "not-a-folder"
    blocker.write_text("x", encoding="utf-8")
    db = blocker / "leave.db"                      # its parent is a file: cannot be created
    env = {k: v for k, v in os.environ.items()
           if k not in ("LEAVEMANAGER_STORAGE", "DATABASE_PATH", "SEED_DEMO_DATA", "LOG_LEVEL")}
    env.update(PYTHONPATH=str(ROOT), PYTHONIOENCODING="utf-8", DATABASE_PATH=str(db))
    proc = subprocess.run([sys.executable, "-m", "flask", "--app", "app", "hesap-ac",
                           "--eposta", "ik@firma.com", "--rol", "IK"],
                          cwd=tmp_path, env=env, input="", capture_output=True,
                          encoding="utf-8", timeout=60)
    assert proc.returncode != 0
    errors = [line for line in proc.stderr.splitlines() if " ERROR app.storage: " in line]
    assert len(errors) == 1 and str(db) in errors[0]
    assert "Traceback" not in proc.stderr
    assert "Hesap oluşturuldu" not in proc.stdout + proc.stderr


# --- AC-9 -----------------------------------------------------------------------------------

def test_demo_seed_creates_no_accounts(tmp_path):
    store = leave_app.build_storage({"DATABASE_PATH": str(tmp_path / "leave.db"),
                                     "SEED_DEMO_DATA": "1"})
    try:
        assert len(store.employees()) == 5 and store.accounts() == []
    finally:
        store.close()
    assert MemoryStorage().accounts() == []


def production_files():
    return [ROOT / "app.py"] + sorted(f for layer in ("domain", "storage", "web")
                                      for f in (ROOT / layer).rglob("*.py"))


def calls(path, name):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call)
            and ((isinstance(n.func, ast.Name) and n.func.id == name)
                 or (isinstance(n.func, ast.Attribute) and n.func.attr == name))]


def test_no_default_account_or_password_in_code():
    """Accounts are added only by AccountService.create_account; hashes are made only by the
    hasher, from the password given to it — never from a literal."""
    rel = {f.relative_to(ROOT).as_posix(): f for f in production_files()}
    adders = {name for name, f in rel.items() if calls(f, "add_account")}
    assert adders == {"domain/accounts.py"}
    hashers = {name for name, f in rel.items() if calls(f, "generate_password_hash")}
    assert hashers == {"app.py"}
    for f in rel.values():
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and getattr(n.func, "attr", getattr(n.func, "id", "")) in (
                    "generate_password_hash", "create_account", "hash"):
                assert not any(isinstance(a, ast.Constant) for a in n.args), (f, n.lineno)
