"""IK approves or rejects pending leave requests — spec 0010.

Service tests pin the domain contract (R-1..R-5: transitions, balance check on approval, typed
exceptions); screen tests pin what the user sees (buttons, message, status code, redirect).
Examples use today = 2026-10-23 and the opening data (conftest).
"""
import datetime as dt
import logging

import pytest

import app as leave_app
from domain.errors import InsufficientBalance, RequestAlreadyDecided, RequestNotFound


def by_name(name):
    return next(e for e in leave_app.storage.employees() if e["name"] == name)


def status_of(request_id):
    return next(r for r in leave_app.storage.requests() if r["id"] == request_id)["status"]


def add_pending(emp_id, start, days, reason="x"):
    """A pending request straight into storage (seam), so its size is not limited by BR-6."""
    request_id = leave_app.storage.next_request_id()
    leave_app.storage.add_request({
        "id": request_id, "employee_id": emp_id, "start": start,
        "end": start + dt.timedelta(days=days - 1), "reason": reason, "status": "Beklemede",
    })
    return request_id


def intervening_approval(svc):
    """AC-3 setup: Ayse (Kalan 14) gets a 12-day request approved → Kalan 2; #5 (3 days) pending."""
    svc.create_request(1, dt.date(2026, 11, 16), dt.date(2026, 11, 27), "Uzun izin")
    svc.approve_request(9)
    assert svc.get_remaining(by_name("Ayse Yilmaz")) == 2


# --- service: happy paths (AC-1, AC-2) ------------------------------------------------------

def test_approve_pending_request_updates_status_and_balance(svc):
    mehmet = by_name("Mehmet Demir")
    assert svc.approve_request(2) is None
    assert status_of(2) == "Onaylandi"
    assert svc.get_used_days(mehmet["id"]) == 3
    assert svc.get_remaining(mehmet) == 17


def test_reject_pending_request_keeps_balance(svc):
    ahmet = by_name("Ahmet Celik")
    before = (svc.get_used_days(ahmet["id"]), svc.get_remaining(ahmet))
    assert svc.reject_request(4) is None
    assert status_of(4) == "Reddedildi"
    assert (svc.get_used_days(ahmet["id"]), svc.get_remaining(ahmet)) == before


# --- service: balance on approval (AC-3, AC-4, AC-5) ----------------------------------------

def test_approve_after_intervening_approval_is_refused(svc):
    intervening_approval(svc)
    with pytest.raises(InsufficientBalance) as exc:
        svc.approve_request(5)
    assert (exc.value.remaining, exc.value.requested) == (2, 3)
    assert status_of(5) == "Beklemede"
    assert svc.get_remaining(by_name("Ayse Yilmaz")) == 2


@pytest.mark.parametrize("days, approved", [(13, True), (14, True), (15, False)],
                         ids=["K-1", "K", "K+1"])
def test_approve_balance_boundary(svc, days, approved):
    ayse = by_name("Ayse Yilmaz")
    assert svc.get_remaining(ayse) == 14
    request_id = add_pending(ayse["id"], dt.date(2026, 11, 2), days)
    if approved:
        svc.approve_request(request_id)
        assert status_of(request_id) == "Onaylandi"
        assert svc.get_remaining(ayse) == 14 - days
    else:
        with pytest.raises(InsufficientBalance) as exc:
            svc.approve_request(request_id)
        assert (exc.value.remaining, exc.value.requested) == (14, 15)
        assert status_of(request_id) == "Beklemede"


def test_reject_ignores_balance(svc):
    intervening_approval(svc)
    svc.reject_request(5)
    assert status_of(5) == "Reddedildi"


# --- service: final states, unknown request (AC-6, AC-7) ------------------------------------

@pytest.mark.parametrize("request_id, action", [
    (1, "approve_request"), (1, "reject_request"), (6, "approve_request"), (6, "reject_request"),
], ids=["#1-approve", "#1-reject", "#6-approve", "#6-reject"])
def test_decided_request_cannot_change(svc, request_id, action):
    before = status_of(request_id)
    with pytest.raises(RequestAlreadyDecided) as exc:
        getattr(svc, action)(request_id)
    assert exc.value.request_id == request_id
    assert exc.value.status == before
    assert status_of(request_id) == before


def test_double_approve_counts_once(svc):
    mehmet = by_name("Mehmet Demir")
    svc.approve_request(2)
    with pytest.raises(RequestAlreadyDecided):
        svc.approve_request(2)
    assert svc.get_used_days(mehmet["id"]) == 3


@pytest.mark.parametrize("action", ["approve_request", "reject_request"])
def test_unknown_request_raises_not_found(svc, action):
    with pytest.raises(RequestNotFound) as exc:
        getattr(svc, action)(99)
    assert exc.value.request_id == 99
    assert [r["status"] for r in leave_app.storage.requests()].count("Beklemede") == 4


# --- service: past date, log line (AC-10, AC-1 K-6) -----------------------------------------

def test_approve_past_dated_pending_request(svc):
    request_id = add_pending(2, dt.date(2026, 10, 1), 2)
    svc.approve_request(request_id)
    assert status_of(request_id) == "Onaylandi"


@pytest.mark.parametrize("action, request_id, result, name, reason", [
    ("approve_request", 2, "Onaylandi", "Mehmet Demir", "Aile ziyareti"),
    ("reject_request", 4, "Reddedildi", "Ahmet Celik", "Yilbasi oncesi"),
], ids=["approve", "reject"])
def test_decision_logs_info_without_personal_data(svc, caplog, action, request_id, result,
                                                  name, reason):
    with caplog.at_level(logging.INFO, logger="domain"):
        getattr(svc, action)(request_id)
    infos = [r for r in caplog.records if r.levelno == logging.INFO]
    assert len(infos) == 1
    line = infos[0].getMessage()
    assert f"#{request_id}" in line and result in line
    assert name not in line and reason not in line
