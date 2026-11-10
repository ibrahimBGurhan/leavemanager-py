"""Storage contract tests — spec 0016 (ADR-0001).

Every storage implementation must pass these. Today the list holds only MemoryStorage; spec 0017
adds SqliteStorage without changing the tests. The tests use their own storage instance (never
the app's `leave_app.storage`) and look at relative change (before/after), not at the opening
data, so a storage that starts empty passes them too (plan 0016 Risk 2). Only behavior the domain
relies on is pinned; MemoryStorage-only details (a live list object, the opening records) are not
(plan 0016 Risk 1).
"""
import datetime as dt
import threading

import pytest

from storage.memory import MemoryStorage
from storage.sqlite import SqliteStorage

FACTORIES = [pytest.param(MemoryStorage, id="memory"),
             pytest.param(lambda: SqliteStorage(":memory:"), id="sqlite")]  # spec 0017

D = dt.date


@pytest.fixture(params=FACTORIES)
def store(request):
    return request.param()


def employee(emp_id, name="Test Kisi"):
    return {"id": emp_id, "name": name, "department": "IT", "hire_date": D(2020, 1, 6)}


def leave_request(store, employee_id, status="Beklemede", reason="x"):
    request_id = store.next_request_id()
    record = {"id": request_id, "employee_id": employee_id, "start": D(2026, 11, 16),
              "end": D(2026, 11, 18), "reason": reason, "status": status}
    store.add_request(record)
    return record


def ids(records):
    return [r["id"] for r in records]


def status_of(store, request_id):
    return next(r for r in store.requests() if r["id"] == request_id)["status"]


# --- employees --------------------------------------------------------------------------------

def test_added_employee_is_listed_last_with_its_fields(store):
    before = ids(store.employees())
    store.add_employee(employee(100, "Yeni Kisi"))
    store.add_employee(employee(101, "Diger Kisi"))
    after = store.employees()
    assert ids(after) == before + [100, 101]
    new = after[-2]
    assert (new["id"], new["name"], new["department"], new["hire_date"]) == (
        100, "Yeni Kisi", "IT", D(2020, 1, 6))
    assert isinstance(new["hire_date"], dt.date)


# --- request numbers --------------------------------------------------------------------------

def test_next_request_id_is_above_every_existing_id_and_increases(store):
    existing = ids(store.requests())
    first = store.next_request_id()
    second = store.next_request_id()
    assert all(first > i for i in existing)
    assert second > first
    assert isinstance(first, int) and isinstance(second, int)


def test_next_request_id_is_never_reused(store):
    store.add_employee(employee(100))
    seen = set()
    for _ in range(5):
        seen.add(leave_request(store, 100)["id"])
        seen.add(store.next_request_id())  # an id taken but not used is not handed out again
    assert len(seen) == 10


# --- employee numbers (spec 0022) -------------------------------------------------------------

def test_next_employee_id_is_above_every_existing_id_and_increases(store):
    existing = ids(store.employees())
    first = store.next_employee_id()
    second = store.next_employee_id()
    assert all(first > i for i in existing)
    assert second > first
    assert isinstance(first, int) and isinstance(second, int)


def test_next_employee_id_is_never_reused(store):
    seen = set()
    for n in range(5):
        emp_id = store.next_employee_id()
        store.add_employee(employee(emp_id, "Kisi %d" % n))
        seen.add(emp_id)
        seen.add(store.next_employee_id())  # an id taken but not used is not handed out again
    assert len(seen) == 10
    assert len(set(ids(store.employees()))) == len(store.employees())


def test_next_employee_id_starts_at_one_in_an_empty_store():
    store = SqliteStorage(":memory:")
    assert store.employees() == []
    assert store.next_employee_id() == 1


def test_next_employee_id_continues_after_reopen(tmp_path):
    path = tmp_path / "personel.db"
    store = SqliteStorage(path)
    for n in range(3):
        store.add_employee(employee(store.next_employee_id(), "Kisi %d" % n))
    store.close()
    reopened = SqliteStorage(path)
    assert reopened.next_employee_id() == 4
    reopened.close()


def test_concurrent_next_employee_id_calls_get_distinct_numbers(store, race_window):
    """G-5: two adds at the same time never get the same number. Spec 0026: the first read of the
    counter waits for a second thread, so without the lock a number repeats on every run."""
    race_window.counter(store, "_next_employee_id")
    start = threading.Barrier(8)
    seen = []

    def worker():
        start.wait()
        for _ in range(25):
            seen.append(store.next_employee_id())

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(seen) == 200
    assert len(set(seen)) == 200


# --- requests ---------------------------------------------------------------------------------

def test_added_request_is_listed_last_with_its_fields(store):
    store.add_employee(employee(100))
    before = ids(store.requests())
    first = leave_request(store, 100, reason="Ilk")
    second = leave_request(store, 100, reason="Ikinci")
    after = store.requests()
    assert ids(after) == before + [first["id"], second["id"]]
    got = after[-2]
    assert got == first
    assert isinstance(got["start"], dt.date) and isinstance(got["end"], dt.date)


def test_set_request_status_changes_only_that_request(store):
    store.add_employee(employee(100))
    a = leave_request(store, 100)["id"]
    b = leave_request(store, 100)["id"]
    others = {r["id"]: r["status"] for r in store.requests() if r["id"] != a}
    store.set_request_status(a, "Onaylandi")
    assert status_of(store, a) == "Onaylandi"
    assert {r["id"]: r["status"] for r in store.requests() if r["id"] != a} == others
    assert status_of(store, b) == "Beklemede"


def test_set_request_status_on_unknown_id_changes_nothing(store):
    """The transition decision lives in the domain (spec 0010); storage stays silent."""
    store.add_employee(employee(100))
    leave_request(store, 100)
    before = [dict(r) for r in store.requests()]
    unknown = max(ids(store.requests())) + 1000
    store.set_request_status(unknown, "Onaylandi")
    assert [dict(r) for r in store.requests()] == before


def test_status_change_is_visible_on_the_next_read(store):
    store.add_employee(employee(100))
    a = leave_request(store, 100)["id"]
    store.set_request_status(a, "Reddedildi")
    assert status_of(store, a) == "Reddedildi"
    assert status_of(store, a) == "Reddedildi"  # stable across reads


# --- accounts (spec 0018) ---------------------------------------------------------------------

def account(email, employee_id=None, locked_until=None, active=True, failed_attempts=0):
    return {"email": email, "password_hash": "scrypt:test$hash-" + email, "role": "IK",
            "employee_id": employee_id, "active": active, "failed_attempts": failed_attempts,
            "locked_until": locked_until}


def test_added_account_is_listed_last_with_its_fields(store):
    before = [a["email"] for a in store.accounts()]
    first = account("ali@firma.com")
    second = account("ayse@firma.com", employee_id=100, active=False, failed_attempts=3,
                     locked_until=dt.datetime(2026, 11, 5, 14, 30, 15))
    store.add_account(first)
    store.add_account(second)
    after = store.accounts()
    assert [a["email"] for a in after] == before + ["ali@firma.com", "ayse@firma.com"]
    assert after[-2] == first
    assert after[-1] == second
    assert after[-1]["active"] is False and after[-2]["active"] is True
    assert isinstance(after[-1]["locked_until"], dt.datetime)
    assert after[-2]["employee_id"] is None and after[-2]["locked_until"] is None


def test_accounts_do_not_touch_employees_or_requests(store):
    employees = [dict(e) for e in store.employees()]
    requests = [dict(r) for r in store.requests()]
    store.add_account(account("veli@firma.com"))
    assert [dict(e) for e in store.employees()] == employees
    assert [dict(r) for r in store.requests()] == requests


# --- login state (spec 0019) -------------------------------------------------------------------

def state(store, email):
    a = next(a for a in store.accounts() if a["email"] == email)
    return a["failed_attempts"], a["locked_until"], a["active"]


def test_login_failure_counts_up_and_returns_the_new_value(store):
    store.add_account(account("ali@firma.com"))
    store.add_account(account("veli@firma.com"))
    assert [store.record_login_failure("ali@firma.com") for _ in range(3)] == [1, 2, 3]
    assert state(store, "ali@firma.com") == (3, None, True)
    assert state(store, "veli@firma.com") == (0, None, True)


def test_lock_and_clear(store):
    until = dt.datetime(2026, 11, 6, 9, 15, 30)
    store.add_account(account("ali@firma.com"))
    store.record_login_failure("ali@firma.com")
    store.lock_account("ali@firma.com", until)
    assert state(store, "ali@firma.com") == (1, until, True)
    store.clear_login_failures("ali@firma.com")
    assert state(store, "ali@firma.com") == (0, None, True)


def test_set_account_active(store):
    store.add_account(account("ali@firma.com"))
    store.set_account_active("ali@firma.com", False)
    assert state(store, "ali@firma.com") == (0, None, False)
    store.set_account_active("ali@firma.com", True)
    assert state(store, "ali@firma.com") == (0, None, True)


def test_login_state_on_unknown_email_changes_nothing(store):
    store.add_account(account("ali@firma.com"))
    before = [dict(a) for a in store.accounts()]
    assert store.record_login_failure("yok@firma.com") == 0
    store.lock_account("yok@firma.com", dt.datetime(2026, 11, 6, 9, 0))
    store.clear_login_failures("yok@firma.com")
    store.set_account_active("yok@firma.com", False)
    assert [dict(a) for a in store.accounts()] == before


def test_concurrent_login_failures_are_all_counted(store):
    """G-4: increments that arrive at the same time are not lost."""
    store.add_account(account("ali@firma.com"))
    start = threading.Barrier(8)
    seen = []

    def worker():
        start.wait()
        for _ in range(25):
            seen.append(store.record_login_failure("ali@firma.com"))

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert state(store, "ali@firma.com")[0] == 200
    assert sorted(seen) == list(range(1, 201))


# --- the written contract ---------------------------------------------------------------------

def test_storage_implements_the_contract(store):
    from storage.contract import LeaveStorage
    assert isinstance(store, LeaveStorage)
