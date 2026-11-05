"""Pending requests count against new requests; the balance table shows them — spec 0013 (OD-3).

Kalan stays Hak − Kullanilan. A new request is saved only if Kalan − Bekleyen >= its days
(K-2); approval keeps checking Kalan alone (K-4). Opening data, today = 2026-10-23 (conftest):
Bekleyen is Ayse 3 (#5), Mehmet 3 (#2), Zeynep 1 (#3), Ahmet 5 (#4), Elif 0.
"""
import datetime as dt

import pytest

import app as leave_app
from conftest import table_rows, visible_text
from domain.errors import InsufficientBalance

START = dt.date(2026, 12, 1)
BALANCE_HEADER = ["Ad", "Birim", "Hak", "Kullanilan", "Kalan", "Bekleyen"]


def by_name(name):
    return next(e for e in leave_app.storage.employees() if e["name"] == name)


def add_pending(emp_id, start, days):
    """A pending request straight into storage (seam): its size is not limited by the rule."""
    request_id = leave_app.storage.next_request_id()
    leave_app.storage.add_request({
        "id": request_id, "employee_id": emp_id, "start": start,
        "end": start + dt.timedelta(days=days - 1), "reason": "x", "status": "Beklemede",
    })
    return request_id


def form(emp_id, days, start=START):
    end = start + dt.timedelta(days=days - 1)
    return {"employee_id": str(emp_id), "start": start.isoformat(), "end": end.isoformat(),
            "reason": "x"}


def service_saves(svc, emp_id, days):
    leave_app.storage.reset()
    try:
        return svc.create_request(emp_id, START, START + dt.timedelta(days=days - 1), "x") is True
    except InsufficientBalance:
        return False


def balance_row(client, name):
    rows = table_rows(client.get("/").get_data(as_text=True))
    assert rows[0] == BALANCE_HEADER
    return next(row for row in rows[1:] if row[0] == name)


def assert_refused(resp, message):
    assert resp.status_code == 400
    html = resp.get_data(as_text=True)
    text = visible_text(html)
    assert message in text
    assert html.index(message) < html.index("<form")
    for leak in ("ERR-", "InsufficientBalance", "Traceback"):
        assert leak not in text
    assert len(leave_app.storage.requests()) == 8


# --- CB-1 -----------------------------------------------------------------------------------

@pytest.mark.parametrize("days, saved", [(12, True), (13, True), (14, False)],
                         ids=["available-1", "available", "available+1"])
def test_new_request_counts_pending(client, svc, days, saved):
    """Zeynep: Kalan 14, Bekleyen 1 (#3) → 13 days available. Screen and service agree."""
    resp = client.post("/new", data=form(3, days))
    assert (resp.status_code == 302) is saved
    assert (len(leave_app.storage.requests()) == 9) is saved
    assert service_saves(svc, 3, days) is saved


@pytest.mark.parametrize("days, saved", [(20, True), (21, False)])
def test_no_pending_boundary_unchanged(client, svc, days, saved):
    """Mehmet, after #2 is rejected: Kalan 20, Bekleyen 0 → the boundary is Kalan, as before."""
    svc.reject_request(2)
    resp = client.post("/new", data=form(2, days))
    assert (resp.status_code == 302) is saved
    assert (len(leave_app.storage.requests()) == 9) is saved


def test_past_dated_pending_counts(svc):
    """K-1: a pending request in the past counts too (BR-8)."""
    add_pending(3, dt.date(2026, 9, 1), 2)  # Zeynep: Bekleyen 1 + 2 = 3 → 11 available
    with pytest.raises(InsufficientBalance) as exc:
        svc.create_request(3, START, START + dt.timedelta(days=11), "x")
    assert (exc.value.remaining, exc.value.pending, exc.value.requested) == (14, 3, 12)
    assert svc.create_request(3, START, START + dt.timedelta(days=10), "x") is True


# --- CB-2 -----------------------------------------------------------------------------------

def test_balance_message_names_pending(client, svc):
    resp = client.post("/new", data=form(3, 14))
    assert_refused(resp, "Kalan izin bakiyeniz yetersiz (kalan 14 gün, bekleyen 1 gün, talep 14 gün).")
    with pytest.raises(InsufficientBalance) as exc:
        svc.create_request(3, START, START + dt.timedelta(days=13), "x")
    assert (exc.value.remaining, exc.value.pending, exc.value.requested) == (14, 1, 14)


def test_negative_available_has_no_special_case(client):
    """S-1: pre-0013 data where Bekleyen exceeds Kalan — every request is refused, the message
    gives the numbers as they are and no negative 'available' number."""
    add_pending(3, dt.date(2026, 11, 16), 14)  # Zeynep: Kalan 14, Bekleyen 15
    resp = client.post("/new", data=form(3, 1))
    assert resp.status_code == 400
    text = visible_text(resp.get_data(as_text=True))
    assert "Kalan izin bakiyeniz yetersiz (kalan 14 gün, bekleyen 15 gün, talep 1 gün)." in text
    assert "-1" not in text
    assert len(leave_app.storage.requests()) == 9  # opening 8 + the one added above


# --- CB-3 -----------------------------------------------------------------------------------

def test_balance_table_shows_pending(client):
    rows = table_rows(client.get("/").get_data(as_text=True))
    assert rows[0] == BALANCE_HEADER
    assert [(r[0], r[2], r[3], r[4], r[5]) for r in rows[1:]] == [
        ("Ayse Yilmaz", "26", "12", "14", "3"),
        ("Mehmet Demir", "20", "0", "20", "3"),
        ("Zeynep Kaya", "14", "0", "14", "1"),
        ("Ahmet Celik", "20", "0", "20", "5"),
        ("Elif Sahin", "0", "0", "0", "0"),
    ]


# --- CB-4 -----------------------------------------------------------------------------------

@pytest.mark.parametrize("action, name, expected", [
    ("approve #2", "Mehmet Demir", ["Mehmet Demir", "Muhasebe", "20", "3", "17", "0"]),
    ("reject #4", "Ahmet Celik", ["Ahmet Celik", "IT", "20", "0", "20", "0"]),
    ("new 2 days", "Zeynep Kaya", ["Zeynep Kaya", "IK", "14", "0", "14", "3"]),
], ids=["approve", "reject", "new"])
def test_transitions_move_days(client, svc, action, name, expected):
    if action == "approve #2":
        svc.approve_request(2)
    elif action == "reject #4":
        svc.reject_request(4)
    else:
        assert client.post("/new", data=form(3, 2)).status_code == 302
    assert balance_row(client, name) == expected


# --- PB-1 -----------------------------------------------------------------------------------

def test_other_pending_do_not_block_approval(svc):
    """K-4: approval checks Kalan alone. Ayse: Kalan 14, #5 (3 days) pending; a 14-day pending
    request is approved anyway, and #5 then hits the approval check as in 0010."""
    ayse = by_name("Ayse Yilmaz")
    request_id = add_pending(ayse["id"], dt.date(2026, 11, 16), 14)
    svc.approve_request(request_id)
    assert svc.get_remaining(ayse) == 0
    with pytest.raises(InsufficientBalance) as exc:
        svc.approve_request(5)
    assert (exc.value.remaining, exc.value.requested) == (0, 3)
