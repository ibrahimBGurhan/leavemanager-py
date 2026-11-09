"""Role-based access on the screens — spec 0020 (plan 0020 steps 2–3).

Opening data (storage/demo.py): A = Ayse Yilmaz (id 1, IT), B = Mehmet Demir (id 2, Muhasebe).
A has requests 1 (Onaylandi) and 5 (Beklemede); B has 2 (Beklemede) and 8 (Reddedildi). The
`full_statuses` fixture gives both of them all three statuses (spec 0020 AC test data).
The logged-in account is chosen per test by `as_account` (the gate's session check is swapped,
as conftest does for the shared IK account; production code has no switch for it).
"""
import datetime as dt
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
        for path in ("/requests/2/approve",):
            resp = c.post(path, data={"employee_id": str(B), "start": "2026-11-16",
                                      "end": "2026-11-16", "reason": "x"})
            assert resp.status_code == 400 and MSG_CSRF in text(resp)
            assert_no_b_data(text(resp))
