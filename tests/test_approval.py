"""IK approves or rejects pending leave requests — spec 0010.

Service tests pin the domain contract (R-1..R-5: transitions, balance check on approval, typed
exceptions); screen tests pin what the user sees (buttons, message, status code, redirect).
Examples use today = 2026-10-23 and the opening data (conftest).
"""
import datetime as dt
import logging
from html.parser import HTMLParser

import pytest

import app as leave_app
from conftest import table_rows, visible_text
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


# --- screen --------------------------------------------------------------------------------

MSG_APPROVE_INSUFFICIENT = "Personelin kalan izin bakiyesi yetersiz (kalan %d gün, talep %d gün)."
MSG_ALREADY_DECIDED = "Bu talep zaten sonuçlandırılmış."
MSG_REQUEST_NOT_FOUND = "Talep bulunamadı."
MSG_ACTION_UNEXPECTED = "İşlem tamamlanamadı. Lütfen daha sonra tekrar deneyin."


def statuses():
    return [r["status"] for r in leave_app.storage.requests()]


def dashboard(client):
    html = client.get("/").get_data(as_text=True)
    text = visible_text(html)
    counts = tuple(int(text.split(label + ": ")[1].split()[0])
                   for label in ("Bekleyen", "Onaylanan", "Reddedilen"))
    return counts, {row[0]: row[1:] for row in table_rows(html)[1:]}


def assert_message_above_list(resp, status, message):
    """Failure: no redirect, message shown above the requests table."""
    assert resp.status_code == status
    html = resp.get_data(as_text=True)
    assert message in visible_text(html)
    assert html.index(message) < html.index("<table")


def test_screen_approve_redirects_with_message_and_updates_dashboard(client):
    resp = client.post("/requests/2/approve")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/requests?sonuc=onaylandi&talep=2")
    html = client.get(resp.headers["Location"]).get_data(as_text=True)
    assert "Talep #2 onaylandı." in visible_text(html)
    assert html.index("Talep #2 onaylandı.") < html.index("<table")
    counts, balances = dashboard(client)
    assert counts == (3, 2, 3)
    assert balances["Mehmet Demir"] == ["Muhasebe", "20", "3", "17"]


def test_screen_reload_after_success_does_not_repeat(client):
    location = client.post("/requests/2/approve").headers["Location"]
    for _ in range(2):
        assert "Talep #2 onaylandı." in visible_text(client.get(location).get_data(as_text=True))
    assert dashboard(client)[1]["Mehmet Demir"] == ["Muhasebe", "20", "3", "17"]
    assert statuses().count("Onaylandi") == 2


def test_screen_reject_shows_message_and_counts(client):
    _, before = dashboard(client)
    resp = client.post("/requests/4/reject")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/requests?sonuc=reddedildi&talep=4")
    assert "Talep #4 reddedildi." in visible_text(
        client.get(resp.headers["Location"]).get_data(as_text=True))
    counts, balances = dashboard(client)
    assert counts == (3, 1, 4)
    assert balances["Ahmet Celik"] == before["Ahmet Celik"]


def test_screen_approve_insufficient_shows_message(client, svc):
    intervening_approval(svc)
    before = statuses()
    resp = client.post("/requests/5/approve")
    assert_message_above_list(resp, 400, MSG_APPROVE_INSUFFICIENT % (2, 3))
    html = resp.get_data(as_text=True)
    assert "ERR-" not in html and "InsufficientBalance" not in html
    assert statuses() == before


@pytest.mark.parametrize("days, approved", [(13, True), (14, True), (15, False)],
                         ids=["K-1", "K", "K+1"])
def test_screen_and_service_agree_on_approval(client, days, approved):
    request_id = add_pending(1, dt.date(2026, 11, 2), days)
    resp = client.post(f"/requests/{request_id}/approve")
    assert resp.status_code == (302 if approved else 400)
    assert status_of(request_id) == ("Onaylandi" if approved else "Beklemede")


def test_screen_reject_ignores_balance(client, svc):
    intervening_approval(svc)
    assert client.post("/requests/5/reject").status_code == 302
    assert status_of(5) == "Reddedildi"


@pytest.mark.parametrize("path", ["/requests/1/approve", "/requests/1/reject",
                                  "/requests/6/approve", "/requests/6/reject"])
def test_screen_decided_request_shows_message(client, path):
    before = statuses()
    assert_message_above_list(client.post(path), 400, MSG_ALREADY_DECIDED)
    assert statuses() == before


@pytest.mark.parametrize("path", ["/requests/99/approve", "/requests/99/reject",
                                  "/requests/abc/approve", "/requests/abc/reject",
                                  # fix-1 (review F-1): only ASCII digits name a request
                                  "/requests/%202/approve", "/requests/%D9%A2/reject",
                                  "/requests/0_2/approve"])
def test_screen_unknown_or_non_numeric_request(client, path):
    before = statuses()
    assert_message_above_list(client.post(path), 404, MSG_REQUEST_NOT_FOUND)
    assert statuses() == before


def test_screen_unexpected_error_is_logged_not_shown(client, monkeypatch, caplog):
    def broken(request_id, status):
        raise RuntimeError("gizli ayrinti")
    monkeypatch.setattr(leave_app.storage, "set_request_status", broken)
    resp = client.post("/requests/2/approve")
    assert_message_above_list(resp, 500, MSG_ACTION_UNEXPECTED)
    html = resp.get_data(as_text=True)
    assert "gizli ayrinti" not in html and "Traceback" not in html
    assert "onaylandı" not in visible_text(html)
    errors = [r for r in caplog.records if r.levelname == "ERROR"]
    assert len(errors) == 1
    assert errors[0].exc_info[0] is RuntimeError


class _RowForms(HTMLParser):
    """Per table row: the POST forms it holds as (action, [submit values])."""
    def __init__(self):
        super().__init__()
        self.rows = []
        self._form = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "tr":
            self.rows.append([])
        elif tag == "form" and self.rows:
            self._form = (attrs.get("method", "").lower(), attrs.get("action"), [])
            self.rows[-1].append(self._form)
        elif tag == "input" and self._form is not None and attrs.get("type") == "submit":
            self._form[2].append(attrs.get("value"))

    def handle_endtag(self, tag):
        if tag == "form":
            self._form = None


def test_buttons_only_on_pending_rows(client):
    p = _RowForms()
    p.feed(client.get("/requests").get_data(as_text=True))
    data_rows = p.rows[1:]
    assert len(data_rows) == 8
    for r, forms in zip(leave_app.storage.requests(), data_rows):
        if r["status"] == "Beklemede":
            assert forms == [("post", f"/requests/{r['id']}/approve", ["Onayla"]),
                             ("post", f"/requests/{r['id']}/reject", ["Reddet"])]
        else:
            assert forms == []


def test_get_never_changes_status(client):
    before = statuses()
    for path in ("/", "/requests", "/requests?sonuc=onaylandi&talep=2"):
        assert client.get(path).status_code == 200
    for path in ("/requests/2/approve", "/requests/2/reject"):
        assert client.get(path).status_code == 405
    assert statuses() == before
    assert dashboard(client)[0] == (4, 1, 3)


@pytest.mark.parametrize("query", [
    "sonuc=onaylandi&talep=3", "sonuc=reddedildi&talep=2", "sonuc=onaylandi&talep=99",
    "sonuc=onaylandi&talep=abc", "sonuc=xyz&talep=1", "talep=1",
    "sonuc=onaylandi&talep=%201", "sonuc=onaylandi&talep=%D9%A1",  # fix-1 (review F-1)
])
def test_success_message_requires_matching_state(client, query):
    resp = client.get("/requests?" + query)
    assert resp.status_code == 200
    text = visible_text(resp.get_data(as_text=True))
    assert "onaylandı." not in text and "reddedildi." not in text
