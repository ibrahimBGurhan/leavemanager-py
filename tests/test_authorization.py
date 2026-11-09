"""Role-based access on the screens — spec 0020 (plan 0020 steps 2–3).

Opening data (storage/demo.py): A = Ayse Yilmaz (id 1, IT), B = Mehmet Demir (id 2, Muhasebe).
A has requests 1 (Onaylandi) and 5 (Beklemede); B has 2 (Beklemede) and 8 (Reddedildi). The
`full_statuses` fixture gives both of them all three statuses (spec 0020 AC test data).
The logged-in account is chosen per test by `as_account` (the gate's session check is swapped,
as conftest does for the shared IK account; production code has no switch for it).
"""
import datetime as dt
import logging
import re

import pytest

import app as leave_app
from conftest import table_rows, visible_text
from domain.auth import LoginService

A, B = 1, 2
A_NAME, A_DEPT, B_NAME, B_DEPT = "Ayse Yilmaz", "IT", "Mehmet Demir", "Muhasebe"
B_REASONS = ("Aile ziyareti", "Ozel is", "B gizli neden")
MSG_FORBIDDEN = "Bu işlem için yetkiniz yok."
MSG_CSRF = "Form geçersiz ya da süresi dolmuş. Lütfen sayfayı yenileyip tekrar deneyin."
TOKEN = re.compile(r"""name=['"]csrf_token['"] value=['"]([^'"]+)['"]""")


def account(role, employee_id=A, email="ayse@firma.com"):
    return {"email": email, "password_hash": "", "role": role, "employee_id": employee_id,
            "active": True, "failed_attempts": 0, "locked_until": None}


STAFF = account("Personel")
HR = account("IK", None, "ik@firma.com")


@pytest.fixture
def as_account(monkeypatch):
    def use(acc):
        monkeypatch.setattr(LoginService, "session_account", lambda self, email, login_at: acc)
    return use


def add_request(emp_id, status, reason, day):
    rid = leave_app.storage.next_request_id()
    leave_app.storage.add_request({"id": rid, "employee_id": emp_id, "start": day, "end": day,
                                   "reason": reason, "status": status})
    return rid


@pytest.fixture
def full_statuses():
    """A gains a Reddedildi, B gains an Onaylandi: each has one request in every status."""
    a_rejected = add_request(A, "Reddedildi", "A red", dt.date(2026, 9, 7))
    b_approved = add_request(B, "Onaylandi", "B gizli neden", dt.date(2026, 9, 8))
    return a_rejected, b_approved


def text(resp):
    return visible_text(resp.get_data(as_text=True))


def assert_no_b_data(html_text):
    assert B_NAME not in html_text and B_DEPT not in html_text
    for reason in B_REASONS:
        assert reason not in html_text


def employee(emp_id):
    return next(e for e in leave_app.storage.employees() if e["id"] == emp_id)


def balance_row(emp_id):
    svc, emp = leave_app.svc, employee(emp_id)
    return [emp["name"], emp["department"], str(svc.get_entitlement(emp)),
            str(svc.get_used_days(emp_id)), str(svc.get_remaining(emp)),
            str(svc.get_pending_days(emp_id))]


def counts(page_text):
    return tuple(int(re.search(label + r": (\d+)", page_text).group(1))
                 for label in ("Bekleyen", "Onaylanan", "Reddedilen"))


# --- AC-1: IK unchanged -----------------------------------------------------------------------

@pytest.mark.parametrize("employee_id", [None, A])
def test_hr_sees_everything(client, as_account, full_statuses, employee_id):
    as_account(account("IK", employee_id, "ik@firma.com"))
    home = client.get("/").get_data(as_text=True)
    all_requests = leave_app.storage.requests()
    assert counts(visible_text(home)) == tuple(
        sum(r["status"] == s for r in all_requests) for s in ("Beklemede", "Onaylandi", "Reddedildi"))
    assert table_rows(home)[1:] == [balance_row(e["id"]) for e in leave_app.storage.employees()]
    page = client.get("/requests").get_data(as_text=True)
    assert len(table_rows(page)) - 1 == len(all_requests)
    pending = sum(r["status"] == "Beklemede" for r in all_requests)
    assert page.count("value='Onayla'") == pending and page.count("value='Reddet'") == pending
    form = client.get("/new").get_data(as_text=True)
    assert '<select name="employee_id">' in form and form.count("<option") == 5


# --- AC-2, AC-3: Personel reads only their own ------------------------------------------------

def test_staff_home_shows_only_own_counts_and_row(client, as_account, full_statuses):
    as_account(STAFF)
    home = client.get("/").get_data(as_text=True)
    assert counts(visible_text(home)) == (1, 1, 1)   # A: 5 Beklemede, 1 Onaylandi, 1 Reddedildi
    assert table_rows(home)[1:] == [balance_row(A)]
    assert_no_b_data(visible_text(home))


def test_staff_requests_lists_only_own_without_buttons(client, as_account, full_statuses):
    as_account(STAFF)
    page = client.get("/requests").get_data(as_text=True)
    rows = table_rows(page)[1:]
    assert sorted(r[4] for r in rows) == sorted(["Yaz tatili", "Yil sonu", "A red"])
    assert {r[0] for r in rows} == {A_NAME}
    assert {r[5] for r in rows} == {"Onaylandi", "Beklemede", "Reddedildi"}
    assert "value='Onayla'" not in page and "value='Reddet'" not in page
    assert "/approve" not in page and "/reject" not in page
    assert_no_b_data(visible_text(page))


# --- AC-8 (reading): no linked employee -------------------------------------------------------

@pytest.mark.parametrize("employee_id", [None, 99])
def test_unlinked_staff_sees_empty_screens(client, as_account, employee_id):
    as_account(account("Personel", employee_id))
    home = client.get("/").get_data(as_text=True)
    assert counts(visible_text(home)) == (0, 0, 0)
    assert table_rows(home) == [["Ad", "Birim", "Hak", "Kullanilan", "Kalan", "Bekleyen"]]
    assert len(table_rows(client.get("/requests").get_data(as_text=True))) == 1


# --- AC-9: error and message paths are scoped too ---------------------------------------------

@pytest.mark.parametrize("sonuc, rid", [("onaylandi", None), ("reddedildi", 8)])
def test_success_message_hides_other_requests(client, as_account, full_statuses, sonuc, rid):
    """B's decided requests: 8 (Reddedildi) and the fixture's Onaylandi one."""
    as_account(STAFF)
    rid = rid or full_statuses[1]
    page = text(client.get("/requests?sonuc=%s&talep=%d" % (sonuc, rid)))
    assert "Talep #%d" % rid not in page
    assert_no_b_data(page)


def test_csrf_error_page_is_scoped(as_account, full_statuses, monkeypatch):
    as_account(STAFF)
    monkeypatch.setitem(leave_app.app.config, "WTF_CSRF_ENABLED", True)
    leave_app.app.testing = True
    with leave_app.app.test_client() as c:
        for path in ("/requests/2/approve", "/new"):
            resp = c.post(path, data={"employee_id": str(B), "start": "2026-11-16",
                                      "end": "2026-11-16", "reason": "x"})
            assert resp.status_code == 400 and MSG_CSRF in text(resp)
            assert_no_b_data(text(resp))


# --- AC-1 (actions): IK decides any request, own included -------------------------------------

def test_hr_decides_any_request_including_own(client, as_account):
    as_account(account("IK", A, "ik@firma.com"))
    assert client.post("/requests/5/approve").status_code == 302      # A's own request (S-2)
    assert client.post("/requests/2/reject").status_code == 302
    st = {r["id"]: r["status"] for r in leave_app.storage.requests()}
    assert (st[5], st[2]) == ("Onaylandi", "Reddedildi")


# --- AC-4: Personel opens requests in their own name -----------------------------------------

MSG_NO_EMPLOYEE = "Hesabınız bir personel kaydına bağlı değil; talep açmak için İK ile görüşün."


def snapshot():
    return [dict(r) for r in leave_app.storage.requests()]


def test_staff_new_request_has_fixed_name(client, as_account):
    as_account(STAFF)
    html = client.get("/new").get_data(as_text=True)
    assert "<select" not in html and 'name="employee_id"' not in html
    assert "Personel: %s" % A_NAME in visible_text(html)
    for other in (B_NAME, "Zeynep Kaya", "Ahmet Celik", "Elif Sahin"):
        assert other not in html


def test_staff_creates_own_request(client, as_account):
    as_account(STAFF)
    before = snapshot()
    resp = client.post("/new", data={"start": "2026-11-16", "end": "2026-11-16", "reason": "Kendi"})
    assert resp.status_code == 302 and resp.headers["Location"] == "/requests"
    new = snapshot()[len(before):]
    assert [(r["employee_id"], r["status"], r["reason"]) for r in new] == [(A, "Beklemede", "Kendi")]
    assert ["Ayse Yilmaz", "2026-11-16", "2026-11-16", "1", "Kendi", "Beklemede"] in         table_rows(client.get("/requests").get_data(as_text=True))


@pytest.mark.parametrize("data, message", [
    ({"start": "2027-01-04", "end": "2027-03-26"}, "Kalan izin bakiyeniz yetersiz"),
    ({"start": "2026-11-20", "end": "2026-11-16"}, "Bitiş tarihi başlangıç tarihinden önce olamaz."),
    ({"start": "2026-11-21", "end": "2026-11-22"}, "Seçilen tarihler arasında iş günü yok."),
    ({"start": "bozuk", "end": "2026-11-16"},
     "Lütfen personeli ve geçerli başlangıç ve bitiş tarihlerini girin."),
], ids=["balance", "range", "no-workdays", "bad-input"])
def test_staff_rule_errors_keep_fixed_name(client, as_account, data, message):
    as_account(STAFF)
    before = snapshot()
    resp = client.post("/new", data=dict(data, reason="x"))
    assert resp.status_code == 400 and message in text(resp)
    assert "Personel: %s" % A_NAME in text(resp) and "<select" not in resp.get_data(as_text=True)
    assert snapshot() == before


# --- AC-5: not on behalf of anyone else -------------------------------------------------------

@pytest.mark.parametrize("employee_id", [str(B), "99", "abc", ""], ids=["B", "missing", "garbage", "empty"])
def test_staff_cannot_request_for_others(client, as_account, employee_id):
    as_account(STAFF)
    before = snapshot()
    resp = client.post("/new", data={"employee_id": employee_id, "start": "2026-11-16",
                                     "end": "2026-11-17", "reason": "Baskasi icin"})
    assert resp.status_code == 403 and MSG_FORBIDDEN in text(resp)
    assert snapshot() == before
    html = resp.get_data(as_text=True)
    assert "Personel: %s" % A_NAME in text(resp) and "<select" not in html      # G-2
    assert 'value="2026-11-16"' in html and 'value="2026-11-17"' in html and "Baskasi icin" in html
    assert_no_b_data(text(resp))


def test_staff_may_name_themselves(client, as_account):
    """The own number in the field is not an attempt on anyone else."""
    as_account(STAFF)
    resp = client.post("/new", data={"employee_id": str(A), "start": "2026-11-16",
                                     "end": "2026-11-16", "reason": "x"})
    assert resp.status_code == 302


# --- AC-6: Personel decides nothing -----------------------------------------------------------

@pytest.mark.parametrize("rid", ["5", "2", "1", "8", "999", "abc"],
                         ids=["own-pending", "other-pending", "own-decided", "other-decided",
                              "missing", "non-numeric"])
@pytest.mark.parametrize("action", ["approve", "reject"])
def test_staff_cannot_decide(client, as_account, caplog, action, rid):
    caplog.set_level(logging.INFO)
    as_account(STAFF)
    before = snapshot()
    resp = client.post("/requests/%s/%s" % (rid, action))
    assert resp.status_code == 403 and MSG_FORBIDDEN in text(resp)
    assert snapshot() == before
    assert_no_b_data(text(resp))
    assert "value='Onayla'" not in resp.get_data(as_text=True)
    # Every attempt is logged, whatever the request's existence or status (AC-6; review F-4)
    label = {"approve": "onay", "reject": "red"}[action]
    assert [(r.levelname, r.getMessage()) for r in caplog.records if r.name == "domain.access"] == [
        ("WARNING", "yetkisiz islem: ayse@firma.com, %s, hedef '%s'" % (label, rid))]


def test_forbidden_is_logged(client, as_account, caplog):
    caplog.set_level(logging.INFO)
    as_account(STAFF)
    client.post("/requests/2/approve")
    client.post("/requests/5/reject")
    client.post("/new", data={"employee_id": str(B), "start": "2026-11-16", "end": "2026-11-16",
                              "reason": "Gizli neden"})
    lines = [(r.levelname, r.getMessage()) for r in caplog.records if r.name == "domain.access"]
    assert lines == [
        ("WARNING", "yetkisiz islem: ayse@firma.com, onay, hedef '2'"),
        ("WARNING", "yetkisiz islem: ayse@firma.com, red, hedef '5'"),
        ("WARNING", "yetkisiz islem: ayse@firma.com, baskasi adina talep, hedef 2"),
    ]
    logged = " ".join(m for _, m in lines)
    assert "Aile ziyareti" not in logged and "Gizli neden" not in logged and "2026" not in logged


# --- AC-7: Yonetici behaves like Personel in this version (S-1, G-7) -------------------------

def test_manager_is_scoped_like_staff(client, as_account):
    as_account(account("Yonetici", A, "yonetici@firma.com"))
    assert table_rows(client.get("/").get_data(as_text=True))[1:] == [balance_row(A)]
    assert "value='Onayla'" not in client.get("/requests").get_data(as_text=True)
    before = snapshot()
    assert client.post("/requests/2/approve").status_code == 403
    assert client.post("/new", data={"employee_id": str(B), "start": "2026-11-16",
                                     "end": "2026-11-16", "reason": "x"}).status_code == 403
    assert snapshot() == before


# --- AC-8 (actions): no linked employee -------------------------------------------------------

@pytest.mark.parametrize("employee_id", [None, 99])
def test_unlinked_staff_cannot_request(client, as_account, employee_id):
    as_account(account("Personel", employee_id))
    page = client.get("/new")
    assert page.status_code == 200 and MSG_NO_EMPLOYEE in text(page)
    assert "<form method=\"post\">" not in page.get_data(as_text=True)
    before = snapshot()
    for data in ({"start": "2026-11-16", "end": "2026-11-16", "reason": "x"},
                 {"employee_id": str(A), "start": "2026-11-16", "end": "2026-11-16", "reason": "x"}):
        resp = client.post("/new", data=data)
        assert resp.status_code == 403 and MSG_FORBIDDEN in text(resp)
    assert snapshot() == before
