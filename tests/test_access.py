"""Role-based access, domain side — spec 0020 R-1, R-5, R-6, R-7 (plan 0020 step 1).

AccountView is exercised without Flask, on the app's opening data (storage/demo.py):
A = Ayse Yilmaz (id 1; requests 1 Onaylandi, 5 Beklemede), B = Mehmet Demir (id 2; requests 2
Beklemede, 8 Reddedildi).
"""
import datetime as dt
import logging

import pytest

import app as leave_app
from domain.access import AccountView
from domain.errors import (LeaveRequestError, NotAuthorized, RequestNotFound)
from domain.leave_service import APPROVED, PENDING

A, B = 1, 2
DAY = dt.date(2026, 11, 16)   # a Monday, no public holiday


def account(role, employee_id=A, email="a@firma.com"):
    return {"email": email, "role": role, "employee_id": employee_id, "active": True}


def view(acc):
    return leave_app.svc.for_account(acc)


def statuses():
    return {r["id"]: r["status"] for r in leave_app.storage.requests()}


def test_for_account_returns_an_account_view():
    assert isinstance(view(account("IK")), AccountView)


@pytest.mark.parametrize("employee_id", [None, A])
def test_hr_sees_and_decides_everything(employee_id):
    v = view(account("IK", employee_id))
    assert v.employees() == leave_app.storage.employees()
    assert v.requests() == leave_app.storage.requests()
    assert v.can_decide()


@pytest.mark.parametrize("role", ["Personel", "Yonetici", "Admin", "ik", None])
def test_other_roles_see_only_their_own_employee(role):
    """R-1; an unknown or mis-written role gains nothing (plan 0020 Risk 2)."""
    v = view(account(role))
    assert [e["id"] for e in v.employees()] == [A]
    assert sorted(r["id"] for r in v.requests()) == [1, 5]
    assert v.own_employee()["id"] == A
    assert not v.can_decide()


@pytest.mark.parametrize("employee_id", [None, 99])
def test_unlinked_or_missing_employee_sees_nothing(employee_id):
    """R-7: no link, or the linked employee record no longer exists."""
    v = view(account("Personel", employee_id))
    assert v.own_employee() is None
    assert v.employees() == [] and v.requests() == []


def employee(emp_id):
    return next(e for e in leave_app.storage.employees() if e["id"] == emp_id)


def test_balance_is_the_service_calculation():
    svc, emp = leave_app.svc, employee(A)
    expected = (svc.get_entitlement(emp), svc.get_used_days(A), svc.get_remaining(emp),
                svc.get_pending_days(A))
    assert view(account("Personel")).balance(emp) == expected
    assert view(account("IK")).balance(employee(B))[0] == svc.get_entitlement(employee(B))


@pytest.mark.parametrize("employee_id", [A, None])
def test_staff_cannot_read_another_balance(employee_id):
    with pytest.raises(NotAuthorized):
        view(account("Personel", employee_id)).balance(employee(B))


def test_calc_days_is_the_workday_count():
    assert view(account("Personel")).calc_days(DAY, DAY + dt.timedelta(days=6)) == 5


def test_staff_creates_own_request():
    before = len(leave_app.storage.requests())
    view(account("Personel")).create_request(A, DAY, DAY, "x")
    new = leave_app.storage.requests()[before:]
    assert [(r["employee_id"], r["status"]) for r in new] == [(A, PENDING)]


@pytest.mark.parametrize("employee_id, target", [(A, B), (A, 99), (A, "abc"), (None, A), (99, 99)])
def test_staff_cannot_create_for_anyone_else(employee_id, target):
    before = leave_app.storage.requests()[:]
    with pytest.raises(NotAuthorized):
        view(account("Personel", employee_id)).create_request(target, DAY, DAY, "x")
    assert leave_app.storage.requests() == before


@pytest.mark.parametrize("request_id", [5, 2, 1, 8, 999, "abc"])
@pytest.mark.parametrize("decide", ["approve_request", "reject_request"])
def test_staff_cannot_decide_any_request(decide, request_id):
    """R-6: authorization comes before existence and status — own pending (5), other's pending
    (2), decided (1, 8), missing (999) and a malformed id all get the same refusal."""
    before = statuses()
    with pytest.raises(NotAuthorized):
        getattr(view(account("Personel")), decide)(request_id)
    assert statuses() == before


def test_hr_still_gets_the_domain_errors():
    with pytest.raises(RequestNotFound):
        view(account("IK")).approve_request(999)


def test_hr_approves_own_request():
    """R-5, S-2: no separation of duties in this version."""
    view(account("IK", A)).approve_request(5)
    assert statuses()[5] == APPROVED


def test_refusal_is_logged_without_request_content(caplog):
    caplog.set_level(logging.INFO)
    v = view(account("Personel", email="ayse@firma.com"))
    for call in (lambda: v.approve_request(2), lambda: v.reject_request(5),
                 lambda: v.create_request(B, DAY, DAY, "Gizli neden")):
        with pytest.raises(NotAuthorized):
            call()
    lines = [(r.levelname, r.getMessage()) for r in caplog.records if r.name == "domain.access"]
    assert lines == [
        ("WARNING", "yetkisiz islem: ayse@firma.com, onay, hedef 2"),
        ("WARNING", "yetkisiz islem: ayse@firma.com, red, hedef 5"),
        ("WARNING", "yetkisiz islem: ayse@firma.com, baskasi adina talep, hedef 2"),
    ]
    text = " ".join(m for _, m in lines)
    assert "Aile ziyareti" not in text and "Gizli neden" not in text and "2026" not in text


def test_not_authorized_is_not_a_leave_request_error():
    """Existing `except LeaveRequestError` paths must not swallow it (plan 0020)."""
    assert not issubclass(NotAuthorized, LeaveRequestError)
