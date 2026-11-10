"""Manager (Yonetici) role — spec 0021 (plan 0021).

Opening data (storage/demo.py): IT = A Ayse Yilmaz (id 1; requests 1 Onaylandi, 5 Beklemede) and
M Ahmet Celik (id 4; request 4 Beklemede); Muhasebe = B Mehmet Demir (id 2; requests 2 Beklemede,
8 Reddedildi). The manager account is linked to M. Extra employees and requests are added to the
in-memory storage inside the tests. The logged-in account is chosen per test by `as_account`
(the gate's session check is swapped, as in tests/test_authorization.py).
"""
import datetime as dt
import logging
import re

import pytest

import app as leave_app
from conftest import table_rows, visible_text
from domain.auth import LoginService

A, M, B = 1, 4, 2
B_NAME, B_DEPT = "Mehmet Demir", "Muhasebe"
B_REASONS = ("Aile ziyareti", "Ozel is")
MSG_FORBIDDEN = "Bu işlem için yetkiniz yok."
MSG_NO_EMPLOYEE = "Hesabınız bir personel kaydına bağlı değil; talep açmak için İK ile görüşün."
MSG_APPROVE_INSUFFICIENT = "Personelin kalan izin bakiyesi yetersiz"
DAY = "2026-11-16"


def account(role, employee_id=M, email="mudur@firma.com"):
    return {"email": email, "password_hash": "", "role": role, "employee_id": employee_id,
            "active": True, "failed_attempts": 0, "locked_until": None}


MANAGER = account("Yonetici")
HR = account("IK", None, "ik@firma.com")


@pytest.fixture
def as_account(monkeypatch):
    def use(acc):
        monkeypatch.setattr(LoginService, "session_account", lambda self, email, login_at: acc)
    return use


def add_employee(emp_id, name, department):
    leave_app.storage.add_employee({"id": emp_id, "name": name, "department": department,
                                    "hire_date": dt.date(2015, 1, 5)})


def add_request(emp_id, status, reason, start, end=None):
    rid = leave_app.storage.next_request_id()
    leave_app.storage.add_request({"id": rid, "employee_id": emp_id, "start": start,
                                   "end": end or start, "reason": reason, "status": status})
    return rid


def statuses():
    return {r["id"]: r["status"] for r in leave_app.storage.requests()}


def text(resp):
    return visible_text(resp.get_data(as_text=True))


def assert_no_b_data(page_text):
    assert B_NAME not in page_text and B_DEPT not in page_text
    for reason in B_REASONS:
        assert reason not in page_text


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


# --- AC-1: IK decides the manager's own request; Personel and IK otherwise unchanged ----------

def test_hr_decides_manager_request(client, as_account):
    as_account(HR)
    assert client.post("/requests/%d/approve" % M).status_code == 302
    assert statuses()[M] == "Onaylandi"


# --- AC-2: home page shows the unit -----------------------------------------------------------

def test_manager_home_shows_unit_counts_and_rows(client, as_account):
    add_request(A, "Reddedildi", "A red", dt.date(2026, 9, 7))
    as_account(MANAGER)
    home = client.get("/").get_data(as_text=True)
    assert counts(visible_text(home)) == (2, 1, 1)    # IT: 5 and 4 pending, 1 approved, new reject
    assert table_rows(home)[1:] == [balance_row(A), balance_row(M)]
    assert_no_b_data(visible_text(home))


# --- AC-3: requests list — buttons only on others' pending requests in the unit ----------------

def test_manager_requests_show_unit_with_buttons_on_others_pending(client, as_account):
    as_account(MANAGER)
    page = client.get("/requests").get_data(as_text=True)
    rows = table_rows(page)[1:]
    assert sorted(r[4] for r in rows) == sorted(["Yaz tatili", "Yilbasi oncesi", "Yil sonu"])
    assert "/requests/5/approve" in page and "/requests/5/reject" in page     # A, pending
    assert "/requests/4/approve" not in page                                   # own
    assert "/requests/1/approve" not in page                                   # decided
    assert_no_b_data(visible_text(page))


# --- AC-4: deciding a unit request ------------------------------------------------------------

def test_manager_approves_and_rejects_unit_request(client, as_account):
    other = add_request(A, "Beklemede", "A ikinci", dt.date(2026, 11, 23))
    as_account(MANAGER)
    resp = client.post("/requests/5/approve")
    assert resp.status_code == 302 and "Talep #5 onaylandı." in text(client.get(resp.headers["Location"]))
    resp = client.post("/requests/%d/reject" % other)
    assert resp.status_code == 302 and ("Talep #%d reddedildi." % other) in text(client.get(resp.headers["Location"]))
    assert (statuses()[5], statuses()[other]) == ("Onaylandi", "Reddedildi")


def test_manager_approve_insufficient_balance_keeps_pending(client, as_account):
    big = add_request(A, "Beklemede", "Uzun", dt.date(2027, 1, 4), dt.date(2027, 3, 26))
    as_account(MANAGER)
    resp = client.post("/requests/%d/approve" % big)
    assert resp.status_code == 400 and MSG_APPROVE_INSUFFICIENT in text(resp)
    assert statuses()[big] == "Beklemede"


# --- AC-5: everything else is refused ---------------------------------------------------------

@pytest.mark.parametrize("rid", [str(M), str(B), "1", "999", "abc"],
                         ids=["own-pending", "other-unit-pending", "unit-decided", "missing",
                              "non-numeric"])
@pytest.mark.parametrize("action", ["approve", "reject"])
def test_manager_cannot_decide(client, as_account, caplog, action, rid):
    caplog.set_level(logging.INFO)
    as_account(MANAGER)
    before = statuses()
    resp = client.post("/requests/%s/%s" % (rid, action))
    assert resp.status_code == 403 and MSG_FORBIDDEN in text(resp)
    assert statuses() == before
    assert_no_b_data(text(resp))
    label = {"approve": "onay", "reject": "red"}[action]
    assert [(r.levelname, r.getMessage()) for r in caplog.records if r.name == "domain.access"] == [
        ("WARNING", "yetkisiz islem: mudur@firma.com, %s, hedef '%s'" % (label, rid))]
    # Spec 0027 (issue #43, 0021 G-B): the 403 screen shows the manager's unit, not just "no B".
    rows = table_rows(resp.get_data(as_text=True))
    assert {row[0] for row in rows[1:]} == {"Ayse Yilmaz", "Ahmet Celik"}
    assert rows == table_rows(client.get("/requests").get_data(as_text=True))


def test_manager_success_message_hides_other_unit(client, as_account):
    as_account(MANAGER)
    page = text(client.get("/requests?sonuc=reddedildi&talep=8"))
    assert "Talep #8" not in page
    assert_no_b_data(page)


# --- AC-6: requests only in the manager's own name --------------------------------------------

def test_manager_new_request_own_name_only(client, as_account):
    as_account(MANAGER)
    html = client.get("/new").get_data(as_text=True)
    assert "<select" not in html and "Personel: Ahmet Celik" in visible_text(html)
    before = len(leave_app.storage.requests())
    assert client.post("/new", data={"start": DAY, "end": DAY, "reason": "Kendi"}).status_code == 302
    assert [r["employee_id"] for r in leave_app.storage.requests()[before:]] == [M]


@pytest.mark.parametrize("target", [str(A), str(B)], ids=["A", "B"])
def test_manager_cannot_request_for(client, as_account, target):
    as_account(MANAGER)
    before = statuses()
    resp = client.post("/new", data={"employee_id": target, "start": DAY, "end": DAY,
                                     "reason": "x"})
    assert resp.status_code == 403 and MSG_FORBIDDEN in text(resp)
    assert statuses() == before


# --- AC-7: the unit rule ----------------------------------------------------------------------

def test_second_manager_decides_unit_requests(client, as_account):
    """G-1: another manager's request is 'someone else's request' for a co-manager."""
    add_employee(6, "Yeni Mudur", "IT")
    as_account(account("Yonetici", 6, "mudur2@firma.com"))
    assert client.post("/requests/5/approve").status_code == 302     # A
    assert client.post("/requests/%d/reject" % M).status_code == 302  # the first manager
    assert (statuses()[5], statuses()[M]) == ("Onaylandi", "Reddedildi")


@pytest.mark.parametrize("department", ["It", " IT", "IT "])
def test_unit_match_is_exact(client, as_account, department):
    """G-3: a differently written unit is another unit; nothing is guessed."""
    add_employee(7, "Farkli Yazim", department)
    rid = add_request(7, "Beklemede", "Farkli birim", dt.date(2026, 11, 24))
    as_account(MANAGER)
    assert "Farkli Yazim" not in text(client.get("/")) + text(client.get("/requests"))
    assert client.post("/requests/%d/approve" % rid).status_code == 403
    assert statuses()[rid] == "Beklemede"


@pytest.mark.parametrize("department", ["", "   "], ids=["empty", "spaces"])
def test_manager_with_blank_unit_is_scoped_to_self(client, as_account, department):
    """G-2: a blank unit is missing data, not a unit — the manager sees only their own record."""
    add_employee(9, "Birimsiz Mudur", department)
    add_employee(10, "Birimsiz Personel", department)
    as_account(account("Yonetici", 9))
    assert [r[0] for r in table_rows(client.get("/").get_data(as_text=True))[1:]] == ["Birimsiz Mudur"]
    assert "value='Onayla'" not in client.get("/requests").get_data(as_text=True)
    before = statuses()
    assert client.post("/requests/5/approve").status_code == 403
    assert statuses() == before


# --- AC-8: no linked employee -----------------------------------------------------------------

@pytest.mark.parametrize("employee_id", [None, 99])
def test_unlinked_manager_sees_nothing(client, as_account, employee_id):
    as_account(account("Yonetici", employee_id))
    home = client.get("/").get_data(as_text=True)
    assert counts(visible_text(home)) == (0, 0, 0) and len(table_rows(home)) == 1
    assert len(table_rows(client.get("/requests").get_data(as_text=True))) == 1
    page = client.get("/new")
    assert page.status_code == 200 and MSG_NO_EMPLOYEE in text(page)
    before = statuses()
    assert client.post("/requests/5/approve").status_code == 403
    assert statuses() == before


# --- AC-9: the decision log names who decided -------------------------------------------------

@pytest.mark.parametrize("who, action, rid, status", [
    ("manager", "approve", 5, "Onaylandi"), ("manager", "reject", 5, "Reddedildi"),
    ("hr", "approve", 2, "Onaylandi"), ("hr", "reject", 2, "Reddedildi"),
], ids=["manager-approve", "manager-reject", "hr-approve", "hr-reject"])
def test_decision_log_names_who_decided(client, as_account, caplog, who, action, rid, status):
    caplog.set_level(logging.INFO)
    acc, decider = (MANAGER, "mudur@firma.com (Yonetici)") if who == "manager" \
        else (HR, "ik@firma.com (IK)")
    as_account(acc)
    assert client.post("/requests/%d/%s" % (rid, action)).status_code == 302
    lines = [r.getMessage() for r in caplog.records
             if r.name == "domain.leave_service" and r.levelname == "INFO"]
    assert lines == ["izin talebi #%d: %s, karar: %s" % (rid, status, decider)]
    for leak in ("Yil sonu", "Aile ziyareti", "Ayse", "Mehmet", "2026"):
        assert leak not in lines[0]


# --- Review 0021 F-1: an over-long numeric id is refused, not a server error -----------------

LONG_ID = "9" * 4301   # past int()'s digit limit (4300)


@pytest.mark.parametrize("acc", [account("Yonetici"), account("Personel", A, "ayse@firma.com")],
                         ids=["manager", "staff"])
@pytest.mark.parametrize("action", ["approve", "reject"])
def test_over_long_request_id_is_refused(client, as_account, caplog, acc, action):
    caplog.set_level(logging.INFO)
    as_account(acc)
    before = statuses()
    resp = client.post("/requests/%s/%s" % (LONG_ID, action))
    assert resp.status_code == 403 and MSG_FORBIDDEN in text(resp)
    assert statuses() == before
    lines = [(r.levelname, r.getMessage()) for r in caplog.records
             if r.name == "domain.access" or r.levelno >= logging.ERROR]
    label = {"approve": "onay", "reject": "red"}[action]
    assert len(lines) == 1 and lines[0][0] == "WARNING"
    assert lines[0][1].startswith("yetkisiz islem: %s, %s, hedef '999" % (acc["email"], label))


# --- Review 0021 F-3: the CSRF error screen is scoped to the unit ----------------------------

MSG_CSRF = "Form geçersiz ya da süresi dolmuş. Lütfen sayfayı yenileyip tekrar deneyin."


def test_manager_csrf_error_page_is_scoped(as_account, monkeypatch):
    as_account(MANAGER)
    monkeypatch.setitem(leave_app.app.config, "WTF_CSRF_ENABLED", True)
    leave_app.app.testing = True
    with leave_app.app.test_client() as c:
        before = statuses()
        resp = c.post("/requests/5/approve")
        assert resp.status_code == 400 and MSG_CSRF in text(resp)
        names = {row[0] for row in table_rows(resp.get_data(as_text=True))[1:]}
        assert names == {"Ayse Yilmaz", "Ahmet Celik"}
        assert_no_b_data(text(resp))
        assert statuses() == before
