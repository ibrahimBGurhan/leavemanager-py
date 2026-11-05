"""Storage contract tests — spec 0016 (ADR-0001).

Every storage implementation must pass these. Today the list holds only MemoryStorage; spec 0017
adds SqliteStorage without changing the tests. The tests use their own storage instance (never
the app's `leave_app.storage`) and look at relative change (before/after), not at the opening
data, so a storage that starts empty passes them too (plan 0016 Risk 2). Only behavior the domain
relies on is pinned; MemoryStorage-only details (a live list object, the opening records) are not
(plan 0016 Risk 1).
"""
import datetime as dt

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


# --- the written contract ---------------------------------------------------------------------

def test_storage_implements_the_contract(store):
    from storage.contract import LeaveStorage
    assert isinstance(store, LeaveStorage)
