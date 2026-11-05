"""Data survives a restart: SQLite storage behind the storage layer — spec 0017 (ADR-0001).

End-to-end tests start the real app.py in a child process with DATABASE_PATH pointing into a
pytest tmp dir and LEAVEMANAGER_STORAGE removed (the shared suite runs on the memory storage,
plan 0017 Risk 1). A "restart" is a second child process on the same file (spec S-2). The real
date is used in the child; the examples do not depend on it. Nothing is written inside the repo.
"""
import datetime as dt
import hashlib
import json
import os
import pathlib
import sqlite3
import stat
import subprocess
import sys

import pytest

import app as leave_app
from conftest import table_rows, visible_text
from storage.sqlite import SqliteStorage

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = dt.date
MSG_EMPLOYEE_NOT_FOUND = "Seçilen personel bulunamadı."

CHILD = r'''
import json, sys
import app
app.app.config["WTF_CSRF_ENABLED"] = False  # the subject here is storage, not CSRF (0011)
client = app.app.test_client()
out = []
for action in json.loads(sys.argv[1]):
    if action[0] == "get":
        resp = client.get(action[1])
    else:
        resp = client.post(action[1], data=action[2])
    out.append([resp.status_code, resp.get_data(as_text=True)])
print(json.dumps(out))
'''


def child_env(db, seed=None):
    env = {k: v for k, v in os.environ.items()
           if k not in ("LEAVEMANAGER_STORAGE", "DATABASE_PATH", "SEED_DEMO_DATA", "LOG_LEVEL")}
    env.update(PYTHONPATH=str(ROOT), PYTHONIOENCODING="utf-8", DATABASE_PATH=str(db))
    if seed is not None:
        env["SEED_DEMO_DATA"] = seed
    return env


def run_app(tmp_path, db, actions, seed=None):
    """Start app.py in a child process, run the actions, return [(status, html), ...]."""
    proc = subprocess.run([sys.executable, "-c", CHILD, json.dumps(actions)], cwd=tmp_path,
                          env=child_env(db, seed), capture_output=True, encoding="utf-8",
                          timeout=60)
    assert proc.returncode == 0, proc.stderr
    return [tuple(r) for r in json.loads(proc.stdout)]


def start_app(tmp_path, db):
    """Start app.py expecting it to fail; returns the finished process."""
    return subprocess.run([sys.executable, "-c", "import app"], cwd=tmp_path,
                          env=child_env(db), capture_output=True, encoding="utf-8", timeout=60)


def rows(html):
    return table_rows(html)


NEW_MEHMET = {"employee_id": "2", "start": "2026-11-16", "end": "2026-11-18", "reason": "Tatil"}


# --- AC-1 -----------------------------------------------------------------------------------

def test_data_survives_restart(tmp_path):
    db = tmp_path / "leave.db"
    first = run_app(tmp_path, db, [["post", "/new", NEW_MEHMET], ["post", "/requests/2/approve", {}],
                                   ["get", "/"], ["get", "/requests"]], seed="1")
    assert first[0][0] == 302 and first[1][0] == 302
    second = run_app(tmp_path, db, [["get", "/"], ["get", "/requests"]])
    assert rows(second[0][1]) == rows(first[2][1])
    assert visible_text(second[0][1]) == visible_text(first[2][1])
    requests = rows(second[1][1])[1:]
    assert requests[1][-1].startswith("Onaylandi")       # #2
    assert requests[8][:5] == ["Mehmet Demir", "2026-11-16", "2026-11-18", "3", "Tatil"]
    assert requests[8][-1].startswith("Beklemede")       # #9


# --- AC-2 -----------------------------------------------------------------------------------

def test_fields_and_types_round_trip(tmp_path):
    db = tmp_path / "leave.db"
    store = SqliteStorage(db)
    store.add_employee({"id": 1, "name": "Şükrü Öztürk", "department": "İK",
                        "hire_date": D(2019, 2, 28)})
    request_id = store.next_request_id()
    store.add_request({"id": request_id, "employee_id": 1, "start": D(2026, 12, 1),
                       "end": D(2026, 12, 3), "reason": "İzin; 'test' -- x", "status": "Beklemede"})
    store.close()
    reopened = SqliteStorage(db)
    assert reopened.employees() == [{"id": 1, "name": "Şükrü Öztürk", "department": "İK",
                                     "hire_date": D(2019, 2, 28)}]
    assert reopened.requests() == [{"id": request_id, "employee_id": 1, "start": D(2026, 12, 1),
                                    "end": D(2026, 12, 3), "reason": "İzin; 'test' -- x",
                                    "status": "Beklemede"}]
    assert isinstance(reopened.requests()[0]["start"], dt.date)
    reopened.close()
    with sqlite3.connect(db) as raw:
        tables = sorted(r[0] for r in raw.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"))
    raw.close()
    assert tables == ["employees", "requests"]  # the quoted text did not touch the schema


def test_lists_keep_insertion_order_not_id_order(tmp_path):
    """Review F-5: the contract says "in insertion order"; SQLite keeps it apart from the id."""
    store = SqliteStorage(tmp_path / "leave.db")
    for emp_id in (5, 3):
        store.add_employee({"id": emp_id, "name": "K%d" % emp_id, "department": "IT",
                            "hire_date": D(2020, 1, 6)})
    for request_id in (7, 4):
        store.add_request({"id": request_id, "employee_id": 5, "start": D(2026, 12, 1),
                           "end": D(2026, 12, 1), "reason": "x", "status": "Beklemede"})
    assert [e["id"] for e in store.employees()] == [5, 3]
    assert [r["id"] for r in store.requests()] == [7, 4]
    store.close()


# --- AC-3 -----------------------------------------------------------------------------------

def test_empty_database_screens(tmp_path):
    db = tmp_path / "leave.db"
    home, requests, form, post = run_app(tmp_path, db, [
        ["get", "/"], ["get", "/requests"], ["get", "/new"], ["post", "/new", NEW_MEHMET]])
    text = visible_text(home[1])
    for counter in ("Bekleyen: 0", "Onaylanan: 0", "Reddedilen: 0"):
        assert counter in text
    assert rows(home[1]) == [["Ad", "Birim", "Hak", "Kullanilan", "Kalan", "Bekleyen"]]
    assert rows(requests[1]) == [["Personel", "Baslangic", "Bitis", "Gun", "Neden", "Durum"]]
    assert form[0] == 200 and "<option" not in form[1] and "Kaydet" in form[1]
    assert post[0] == 400 and MSG_EMPLOYEE_NOT_FOUND in visible_text(post[1])
    after = run_app(tmp_path, db, [["get", "/requests"]])
    assert len(rows(after[0][1])) == 1  # still only the header: nothing was saved


# --- AC-4 -----------------------------------------------------------------------------------

def test_demo_data_only_when_empty(tmp_path):
    db = tmp_path / "leave.db"
    first = run_app(tmp_path, db, [["post", "/requests/4/reject", {}], ["get", "/requests"],
                                   ["get", "/"]], seed="1")
    assert len(rows(first[1][1])) == 1 + 8
    assert len(rows(first[2][1])) == 1 + 5
    second = run_app(tmp_path, db, [["get", "/requests"], ["get", "/"]], seed="1")
    assert rows(second[0][1]) == rows(first[1][1])      # not seeded again, #4 still rejected
    assert rows(second[0][1])[4][-1].startswith("Reddedildi")
    assert rows(second[1][1]) == rows(first[2][1])


def test_seeded_data_is_kept_without_a_write(tmp_path):
    """Review F-3: a first start with SEED_DEMO_DATA=1 that only reads still stores the demo data."""
    db = tmp_path / "leave.db"
    run_app(tmp_path, db, [["get", "/"]], seed="1")
    requests, home = run_app(tmp_path, db, [["get", "/requests"], ["get", "/"]])
    assert len(rows(requests[1])) == 1 + 8
    assert len(rows(home[1])) == 1 + 5


@pytest.mark.parametrize("seed", ["0", "yes", "", None], ids=["zero", "yes", "empty", "unset"])
def test_seed_flag_values(tmp_path, seed):
    db = tmp_path / "leave.db"
    home, = run_app(tmp_path, db, [["get", "/"]], seed=seed)
    assert len(rows(home[1])) == 1


# --- AC-5 -----------------------------------------------------------------------------------

def test_request_number_continues_after_restart(tmp_path):
    db = tmp_path / "leave.db"
    run_app(tmp_path, db, [["post", "/new", NEW_MEHMET]], seed="1")
    second = run_app(tmp_path, db, [
        ["post", "/new", {**NEW_MEHMET, "start": "2026-11-23", "end": "2026-11-23"}],
        ["post", "/requests/10/approve", {}], ["post", "/requests/9/reject", {}]])
    assert [status for status, _ in second] == [302, 302, 302]  # #9 kept, the new one is #10


# --- AC-6 -----------------------------------------------------------------------------------

def test_default_database_path():
    assert pathlib.Path(leave_app.database_path({})) == ROOT / "instance" / "leavemanager.db"
    assert leave_app.database_path({"DATABASE_PATH": "x/y.db"}) == "x/y.db"


def test_missing_folder_is_created(tmp_path):
    db = tmp_path / "a" / "b" / "leave.db"
    run_app(tmp_path, db, [["get", "/"]])
    assert db.is_file()


# --- AC-7 -----------------------------------------------------------------------------------

def test_unwritable_path_stops_the_app(tmp_path):
    blocker = tmp_path / "not-a-folder"
    blocker.write_text("x", encoding="utf-8")
    db = blocker / "leave.db"                     # its parent is a file: cannot be created
    proc = start_app(tmp_path, db)
    assert proc.returncode != 0
    errors = [line for line in proc.stderr.splitlines() if " ERROR app.storage: " in line]
    assert len(errors) == 1 and str(db) in errors[0]
    assert "Traceback" not in proc.stderr
    assert "bellek deposu" not in proc.stderr     # no fall back to memory


def test_read_only_database_stops_the_app(tmp_path):
    """Review F-1: an existing file that cannot be written stops the app at start-up, instead of
    serving pages and failing every write with a 500."""
    db = tmp_path / "leave.db"
    SqliteStorage(db, seed_records=([], [])).close()
    os.chmod(db, stat.S_IREAD)
    try:
        proc = start_app(tmp_path, db)
    finally:
        os.chmod(db, stat.S_IREAD | stat.S_IWRITE)
    assert proc.returncode != 0
    errors = [line for line in proc.stderr.splitlines() if " ERROR app.storage: " in line]
    assert len(errors) == 1 and str(db) in errors[0]
    assert "Traceback" not in proc.stderr


def test_newer_schema_stops_the_app(tmp_path):
    db = tmp_path / "leave.db"
    with sqlite3.connect(db) as raw:
        raw.execute("PRAGMA user_version = 99")
    raw.close()
    before = hashlib.sha256(db.read_bytes()).hexdigest()
    proc = start_app(tmp_path, db)
    assert proc.returncode != 0
    errors = [line for line in proc.stderr.splitlines() if " ERROR app.storage: " in line]
    assert len(errors) == 1
    assert "şema sürümü 99" in errors[0] and "bu uygulama 1" in errors[0]  # review F-4
    assert hashlib.sha256(db.read_bytes()).hexdigest() == before


# --- AC-9 -----------------------------------------------------------------------------------

def test_shared_suite_runs_on_the_memory_storage():
    """Plan 0017 Risk 1/2: the suite never opens a database file inside the repo."""
    assert os.environ.get("LEAVEMANAGER_STORAGE") == "memory"
    assert type(leave_app.storage).__name__ == "MemoryStorage"
