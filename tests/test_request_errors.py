"""Failed leave requests are reported, never shown as success — spec 0008.

Service tests pin the domain contract (typed exceptions, S-4 order); screen tests pin what the
user sees (message, status code, no redirect, no record).
"""
import datetime as dt

import pytest

import app as leave_app
from domain.errors import EmployeeNotFound, InsufficientBalance, InvalidDateRange


def by_name(name):
    return next(e for e in leave_app.storage.employees() if e["name"] == name)


# --- service (CB-1, CB-3, CB-6) -------------------------------------------------------------

def test_insufficient_balance_carries_remaining_and_requested(svc):
    """CB-1/CB-6 (S-2): Elif, kalan 0, 1 günlük talep."""
    elif_ = by_name("Elif Sahin")
    with pytest.raises(InsufficientBalance) as err:
        svc.create_request(elif_["id"], dt.date(2026, 11, 16), dt.date(2026, 11, 16), "x")
    assert (err.value.remaining, err.value.requested) == (0, 1)
    assert len(leave_app.storage.requests()) == 8


def test_end_before_start_raises_invalid_date_range(svc):
    """CB-3 (BR-9): bitiş başlangıçtan önceyse kayıt oluşmaz."""
    mehmet = by_name("Mehmet Demir")
    with pytest.raises(InvalidDateRange):
        svc.create_request(mehmet["id"], dt.date(2026, 11, 18), dt.date(2026, 11, 16), "x")
    assert len(leave_app.storage.requests()) == 8


def test_end_equal_to_start_is_one_day(svc):
    """CB-3: bitiş = başlangıç geçerlidir ve 1 gün sayılır."""
    mehmet = by_name("Mehmet Demir")
    assert svc.create_request(mehmet["id"], dt.date(2026, 11, 16), dt.date(2026, 11, 16), "x") is True
    saved = leave_app.storage.requests()[-1]
    assert svc.calc_days(saved["start"], saved["end"]) == 1


@pytest.mark.parametrize(
    "name, expected",
    [("Yok", EmployeeNotFound), ("Elif Sahin", InvalidDateRange)],
    ids=["unknown-employee-before-date-range", "date-range-before-balance"],
)
def test_violations_are_reported_in_order(svc, name, expected):
    """CB-6 (S-4): personel -> tarih aralığı -> bakiye; yalnızca ilk ihlal bildirilir.
    Elif'in kalanı 0, yani tarih aralığı ters olmasa bakiye ihlali olurdu."""
    emp_id = 99 if name == "Yok" else by_name(name)["id"]
    with pytest.raises(expected):
        svc.create_request(emp_id, dt.date(2026, 11, 18), dt.date(2026, 11, 16), "x")
