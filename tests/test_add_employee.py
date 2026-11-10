"""Add employee (Yeni Personel) — spec 0022 (plan 0022).

Opening data (storage/demo.py): employees 1..5 (units IT, Muhasebe, IK, IT, Satis), so the next
employee number is 6. Domain tests call LeaveService / AccountView directly; screen tests use the
in-process client. The logged-in account is chosen per test by `as_account` (the gate's session
check is swapped, as in tests/test_authorization.py).
"""
import datetime as dt
import logging
import threading

import pytest

import app as leave_app
from domain.accounts import AccountService
from domain.errors import InvalidEmployee, NotAuthorized
from domain.leave_service import LeaveService
from storage.memory import MemoryStorage
from storage.sqlite import SqliteStorage

D = dt.date
MSG_FORBIDDEN = "Bu işlem için yetkiniz yok."


def account(role, employee_id=None, email="ik@firma.com"):
    return {"email": email, "password_hash": "", "role": role, "employee_id": employee_id,
            "active": True, "failed_attempts": 0, "locked_until": None}


HR = account("IK")
HR_LINKED = account("IK", 3, "zeynep@firma.com")
STAFF = account("Personel", 1, "ayse@firma.com")
MANAGER = account("Yonetici", 4, "mudur@firma.com")
STAFF_UNLINKED = account("Personel", None, "bagsiz@firma.com")


def employee_ids():
    return [e["id"] for e in leave_app.storage.employees()]


# --- domain: rules (R-3, R-4, G-1) ---------------------------------------------------------------

@pytest.mark.parametrize("name, unit, hire, reason", [
    pytest.param("", "IT", D(2020, 1, 6), "name-missing", id="name-empty"),
    pytest.param("   ", "IT", D(2020, 1, 6), "name-missing", id="name-spaces"),
    pytest.param("Ali", "", D(2020, 1, 6), "unit-missing", id="unit-empty"),
    pytest.param("Ali", " \t ", D(2020, 1, 6), "unit-missing", id="unit-spaces"),
    pytest.param("A" * 101, "IT", D(2020, 1, 6), "name-too-long", id="name-101"),
    pytest.param("Ali", "U" * 51, D(2020, 1, 6), "unit-too-long", id="unit-51"),
    pytest.param("Ali", "IT", None, "date-invalid", id="date-missing"),
    pytest.param("Ali", "IT", D(1949, 12, 31), "date-too-early", id="date-1949-12-31"),
])
def test_add_employee_rules(svc, name, unit, hire, reason):
    before = list(employee_ids())
    with pytest.raises(InvalidEmployee) as exc:
        svc.add_employee(name, unit, hire)
    assert exc.value.reason == reason
    assert employee_ids() == before


@pytest.mark.parametrize("name, unit, hire, reason", [
    pytest.param("", "", None, "name-missing", id="all-bad"),
    pytest.param("A" * 101, "", None, "name-too-long", id="name-before-unit"),
    pytest.param("Ali", "", D(1900, 1, 1), "unit-missing", id="unit-before-date"),
    pytest.param("Ali", "U" * 51, None, "unit-too-long", id="unit-long-before-date"),
])
def test_domain_first_error_wins_in_order(svc, name, unit, hire, reason):
    with pytest.raises(InvalidEmployee) as exc:
        svc.add_employee(name, unit, hire)
    assert exc.value.reason == reason


@pytest.mark.parametrize("name, unit, hire", [
    pytest.param("A" * 100, "IT", D(2020, 1, 6), id="name-100"),
    pytest.param("Ali", "U" * 50, D(2020, 1, 6), id="unit-50"),
    pytest.param("Ali", "IT", D(1950, 1, 1), id="date-1950-01-01"),
])
def test_domain_boundaries_are_accepted(svc, name, unit, hire):
    record = svc.add_employee(name, unit, hire)
    assert (record["name"], record["department"], record["hire_date"]) == (name, unit, hire)
    assert employee_ids()[-1] == record["id"]


def test_domain_trims_and_keeps_unit_case(svc):
    record = svc.add_employee("  Ayşe Yılmaz ", " iT ", D(2020, 1, 6))
    stored = leave_app.storage.employees()[-1]
    assert (stored["name"], stored["department"]) == ("Ayşe Yılmaz", "iT")
    assert stored == record


def test_domain_numbers_are_next_after_the_largest(svc):
    first = svc.add_employee("Yeni Bir", "IT", D(2020, 1, 6))
    second = svc.add_employee("Yeni Iki", "IT", D(2020, 1, 6))
    assert (first["id"], second["id"]) == (6, 7)


def test_same_name_gets_a_new_number(svc):
    first = svc.add_employee("Ayse Yilmaz", "IT", D(2020, 1, 6))
    second = svc.add_employee("Ayse Yilmaz", "IT", D(2020, 1, 6))
    assert first["id"] != second["id"]
    assert [e["id"] for e in leave_app.storage.employees()
            if e["name"] == "Ayse Yilmaz"] == [1, first["id"], second["id"]]


@pytest.mark.parametrize("factory", [pytest.param(MemoryStorage, id="memory"),
                                     pytest.param(lambda: SqliteStorage(":memory:"),
                                                  id="sqlite")])
def test_concurrent_adds_get_distinct_numbers(factory):
    """G-5: two adds at the same time get different numbers; none is lost."""
    storage = factory()
    service = LeaveService(leave_app.clock, storage)
    before = len(storage.employees())
    start = threading.Barrier(8)
    numbers = []

    def worker(n):
        start.wait()
        for k in range(10):
            numbers.append(service.add_employee("Kisi %d-%d" % (n, k), "IT", D(2020, 1, 6))["id"])

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(set(numbers)) == 80
    ids = [e["id"] for e in storage.employees()]
    assert len(ids) == before + 80
    assert len(set(ids)) == len(ids)


# --- domain: authorization and log (R-7, R-8) -------------------------------------------------

@pytest.mark.parametrize("acc", [pytest.param(HR, id="IK-unlinked"),
                                 pytest.param(HR_LINKED, id="IK-linked")])
def test_hr_view_can_add(svc, acc):
    view = svc.for_account(acc)
    assert view.can_add_employees()
    record = view.add_employee("Yeni Kisi", "IT", D(2020, 1, 6))
    assert employee_ids()[-1] == record["id"]


@pytest.mark.parametrize("acc", [pytest.param(STAFF, id="Personel"),
                                 pytest.param(MANAGER, id="Yonetici"),
                                 pytest.param(STAFF_UNLINKED, id="unlinked-Personel"),
                                 pytest.param(account("Bilinmeyen", 1, "x@firma.com"),
                                              id="unknown-role")])
def test_other_views_cannot_add_even_with_bad_input(svc, caplog, acc):
    view = svc.for_account(acc)
    assert not view.can_add_employees()
    before = list(employee_ids())
    with caplog.at_level(logging.WARNING, logger="domain.access"):
        with pytest.raises(NotAuthorized):
            view.add_employee("", "", None)  # authorization before the input check (R-7)
    assert employee_ids() == before
    assert [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING] == [
        "yetkisiz islem: %s, personel ekleme, hedef None" % acc["email"]]


def test_add_is_logged_without_name_or_date(svc, caplog):
    with caplog.at_level(logging.INFO, logger="domain.leave_service"):
        record = svc.for_account(HR).add_employee("Gizli Ad", "Satis", D(2019, 4, 2))
    lines = [r.getMessage() for r in caplog.records if r.name == "domain.leave_service"]
    assert lines == ["personel eklendi: #%d (Satis), ekleyen: ik@firma.com (IK)" % record["id"]]
    assert all(r.levelno == logging.INFO for r in caplog.records
               if r.name == "domain.leave_service")
    assert "Gizli" not in caplog.text and "2019" not in caplog.text


# --- AC-8: empty database ------------------------------------------------------------------------

def test_first_employee_in_empty_database_gets_number_one_and_an_account(tmp_path):
    storage = SqliteStorage(tmp_path / "bos.db")  # no demo data
    try:
        assert storage.employees() == []
        service = LeaveService(leave_app.clock, storage)
        record = service.for_account(HR).add_employee("Ilk Personel", "IT", D(2026, 11, 2))
        assert record["id"] == 1
        accounts = AccountService(storage, leave_app.hasher)
        acc = accounts.create_account("ilk@firma.com", "Personel", 1, "uzun bir sifre 12",
                                      "uzun bir sifre 12")
        assert (acc["role"], acc["employee_id"]) == ("Personel", 1)
        assert [a["email"] for a in storage.accounts()] == ["ilk@firma.com"]
    finally:
        storage.close()
