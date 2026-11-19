"""Opening balance entry for HR — spec 0041 (plan 0041).

HR enters, per employee, the leave days left as of a date (K-1, K-3); the leave-year calculation
of spec 0040 then starts there (0040 K-9). A pending request that starts before the opening date
is approved without the balance check (K-5); a new request starting before it is refused (K-6).
Opening data (storage/demo.py), today = 2026-10-23 (conftest); the default account is IK
(test@firma.com). Mehmet Demir is #2, hired 2019-06-01, pending #2 starts 2026-11-02.
"""
import datetime as dt
import logging
from html.parser import HTMLParser

import pytest

import app as leave_app
from conftest import (TEST_ACCOUNT, current_links, headings, page_links, table_rows,
                      visible_text)
from domain.auth import LoginService

D = dt.date
PATH = "/acilis-bakiyesi"
LINK = ("Açılış Bakiyesi", PATH)
MSG_FORBIDDEN = "Bu işlem için yetkiniz yok."
MSG_SAVED = "Personel #%d açılış bakiyesi kaydedildi: %s, %d gün."
MSG_WARNING = ("Açılış tarihinden önce başlayan bekleyen talepler: %s. Bunlar onaylanırsa "
               "bakiyeden düşmez.")
MSG_EMPLOYEE_MISSING = "Personel seçin."
MSG_EMPLOYEE_NOT_FOUND = "Personel bulunamadı."
MSG_DATE_INVALID = "Geçerli bir açılış tarihi girin."
MSG_DATE_BEFORE_HIRE = "Açılış tarihi işe giriş tarihinden (%s) önce olamaz."
MSG_DATE_FUTURE = "Açılış tarihi bugünden sonra olamaz."
MSG_DAYS = "Gün 0 ile 365 arasında bir tam sayı olmalı."
MSG_BEFORE_OPENING = ("Bu personelin açılış bakiyesi %s tarihli; daha önce başlayan izin açılış "
                      "bakiyesine dahildir.")
MSG_CSRF = "Form geçersiz ya da süresi dolmuş. Lütfen sayfayı yenileyip tekrar deneyin."
LIST_HEADER = ["Ad", "Birim", "İşe giriş", "Açılış tarihi", "Gün"]


def account(role, employee_id, email):
    return {"email": email, "password_hash": "", "role": role, "employee_id": employee_id,
            "active": True, "failed_attempts": 0, "locked_until": None}


MANAGER = account("Yonetici", 4, "mudur@firma.com")
STAFF = account("Personel", 1, "ayse@firma.com")


@pytest.fixture
def as_account(monkeypatch):
    def use(acc):
        monkeypatch.setattr(LoginService, "session_account", lambda self, email, login_at: acc)
    return use


class _Form(HTMLParser):
    """The form as a browser shows it: input values, select options and the selected one."""

    def __init__(self):
        super().__init__()
        self.forms, self.inputs, self.options, self.selected, self.labels = 0, {}, [], None, {}
        self._label = None

    def handle_starttag(self, tag, attrs):
        a = {k: (v if v is not None else "") for k, v in attrs}
        if tag == "form" and a.get("action") != "/cikis":
            self.forms += 1
        elif tag == "input" and a.get("name"):
            self.inputs[a["name"]] = a
        elif tag == "option":
            self.options.append(a.get("value"))
            if "selected" in a:
                self.selected = a.get("value")
        elif tag == "label":
            self._label = a.get("for")

    def handle_data(self, data):
        if self._label is not None:
            self.labels[self._label] = data.strip()
            self._label = None


def form_of(html):
    p = _Form()
    p.feed(html)
    return p


def page(resp):
    return resp.get_data(as_text=True)


def post(client, employee_id="2", on="2026-01-01", days="10"):
    return client.post(PATH, data={"employee_id": employee_id, "date": on, "days": days})


def opening_of(emp_id):
    return next((o for o in leave_app.storage.opening_balances() if o["employee_id"] == emp_id),
                None)


def home_row(client, name):
    return next(r for r in table_rows(page(client.get("/"))) if r[0] == name)


def add_request(emp_id, start, end, status="Beklemede"):
    rid = leave_app.storage.next_request_id()
    leave_app.storage.add_request({"id": rid, "employee_id": emp_id, "start": start, "end": end,
                                   "reason": "x", "status": status})
    return rid


def status_of(rid):
    return next(r for r in leave_app.storage.requests() if r["id"] == rid)["status"]


def assert_refused(resp, message):
    assert resp.status_code == 400
    html = page(resp)
    assert message in visible_text(html)
    assert html.index(message) < html.index("<form")
    assert leave_app.storage.opening_balances() == []


# --- AC-1: only HR ------------------------------------------------------------------------------

def test_menu_shows_link_only_to_hr(client, as_account):
    assert LINK in page_links(page(client.get("/")))
    html = page(client.get(PATH))
    assert "Açılış Bakiyesi" in headings(html)
    assert current_links(html) == [LINK]
    for acc in (MANAGER, STAFF):
        as_account(acc)
        assert LINK not in page_links(page(client.get("/")))


@pytest.mark.parametrize("acc", [pytest.param(MANAGER, id="Yonetici"),
                                 pytest.param(STAFF, id="Personel")])
@pytest.mark.parametrize("method", ["get", "post"])
def test_non_hr_is_refused(client, as_account, caplog, acc, method):
    as_account(acc)
    with caplog.at_level(logging.WARNING):
        resp = post(client) if method == "post" else client.get(PATH)
    assert resp.status_code == 403
    html = page(resp)
    assert MSG_FORBIDDEN in visible_text(html)
    assert form_of(html).forms == 0 and table_rows(html) == []
    assert leave_app.storage.opening_balances() == []
    assert [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING] == [
        "yetkisiz islem: %s, acilis bakiyesi, hedef None" % acc["email"]]


# --- AC-2: the list ------------------------------------------------------------------------------

def test_list_shows_every_employee(client):
    rows = table_rows(page(client.get(PATH)))
    assert rows == [LIST_HEADER,
                    ["Ayse Yilmaz", "IT", "2008-03-15", "", ""],
                    ["Mehmet Demir", "Muhasebe", "2019-06-01", "", ""],
                    ["Zeynep Kaya", "IK", "2024-11-10", "", ""],
                    ["Ahmet Celik", "IT", "2020-02-29", "", ""],
                    ["Elif Sahin", "Satis", "2026-06-01", "", ""]]
    post(client)
    assert table_rows(page(client.get(PATH)))[2] == [
        "Mehmet Demir", "Muhasebe", "2019-06-01", "2026-01-01", "10"]


def test_form_fields_and_labels(client):
    """K-3, G-2, G-4: labelled fields; employees in insertion order; the date starts empty."""
    f = form_of(page(client.get(PATH)))
    assert f.forms == 1
    assert f.options == ["", "1", "2", "3", "4", "5"]
    assert f.inputs["date"]["type"] == "date" and f.inputs["date"].get("value", "") == ""
    assert f.inputs["days"].get("value", "") == ""
    assert sorted(f.labels.values()) == ["Açılış tarihi", "Gün", "Personel"]


# --- AC-3, AC-4: save and correct ----------------------------------------------------------------

def test_save_redirects_with_message_and_updates_home(client, caplog):
    resp = post(client)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith(PATH + "?kaydedildi=2")
    assert opening_of(2) == {"employee_id": 2, "date": D(2026, 1, 1), "days": 10}
    with caplog.at_level(logging.INFO, logger="domain"):
        for _ in range(2):  # a refresh repeats nothing
            html = page(client.get(resp.headers["Location"]))
            assert MSG_SAVED % (2, "2026-01-01", 10) in visible_text(html)
            assert html.index(MSG_SAVED % (2, "2026-01-01", 10)) < html.index("<form")
            f = form_of(html)
            assert f.selected in (None, "") and f.inputs["date"].get("value", "") == ""
    assert not [r for r in caplog.records if "acilis bakiyesi" in r.getMessage()]
    assert len(leave_app.storage.opening_balances()) == 1
    assert home_row(client, "Mehmet Demir") == [
        "Mehmet Demir", "Muhasebe", "10", "20", "0", "3", "30", "2027-06-01"]


def test_correction_replaces_the_record(client):
    post(client)
    assert post(client, on="2026-07-01", days="5").status_code == 302
    assert leave_app.storage.opening_balances() == [
        {"employee_id": 2, "date": D(2026, 7, 1), "days": 5}]
    assert table_rows(page(client.get(PATH)))[2][3:] == ["2026-07-01", "5"]
    assert home_row(client, "Mehmet Demir") == [
        "Mehmet Demir", "Muhasebe", "5", "0", "0", "3", "5", "2027-06-01"]


@pytest.mark.parametrize("message", ["kaydedildi=99", "kaydedildi=abc", "kaydedildi=" + "9" * 5000,
                                     "kaydedildi=3"],
                         ids=["unknown", "not-a-number", "5000-digits", "no-opening-balance"])
def test_message_comes_from_the_record(client, message):
    """Plan Risk 6: no message for an unknown number or an employee without an opening balance."""
    post(client)
    assert "açılış bakiyesi kaydedildi" not in visible_text(page(client.get(PATH + "?" + message)))


# --- AC-5, AC-6, AC-7: input rules ---------------------------------------------------------------

@pytest.mark.parametrize("days, saved", [("0", True), ("365", True), (" 7 ", True), ("05", True),
                                         ("-1", False), ("366", False), ("2.5", False),
                                         ("abc", False), ("", False), ("٥", False),
                                         ("1_0", False), ("+5", False)])
def test_days_boundaries(client, days, saved):
    resp = post(client, days=days)
    if saved:
        assert resp.status_code == 302
        assert opening_of(2)["days"] == int(days)
    else:
        assert_refused(resp, MSG_DAYS)
        f = form_of(page(resp))
        assert f.selected == "2" and f.inputs["date"]["value"] == "2026-01-01"


@pytest.mark.parametrize("on, message", [
    ("2019-06-01", None), ("2026-10-23", None),
    ("2019-05-31", MSG_DATE_BEFORE_HIRE % "2019-06-01"),
    ("2026-10-24", MSG_DATE_FUTURE),
    ("", MSG_DATE_INVALID), ("2026-02-30", MSG_DATE_INVALID), ("bozuk", MSG_DATE_INVALID),
])
def test_date_boundaries(client, on, message):
    resp = post(client, on=on)
    if message is None:
        assert resp.status_code == 302
        assert opening_of(2)["date"] == D.fromisoformat(on)
    else:
        assert_refused(resp, message)
        f = form_of(page(resp))
        assert f.selected == "2" and f.inputs["days"]["value"] == "10"
        if on == "bozuk":
            assert "bozuk" not in page(resp)  # a broken date is not echoed (spec 0015 K-3)


@pytest.mark.parametrize("employee_id, on, days, message", [
    ("", "2026-01-01", "10", MSG_EMPLOYEE_MISSING),
    ("99", "2026-01-01", "10", MSG_EMPLOYEE_NOT_FOUND),
    ("abc", "2026-01-01", "10", MSG_EMPLOYEE_NOT_FOUND),
    ("٢", "2026-01-01", "10", MSG_EMPLOYEE_NOT_FOUND),
    ("", "bozuk", "abc", MSG_EMPLOYEE_MISSING),         # personel önce
    ("2", "bozuk", "abc", MSG_DATE_INVALID),            # tarih günden önce
])
def test_employee_errors_and_order(client, employee_id, on, days, message):
    assert_refused(post(client, employee_id=employee_id, on=on, days=days), message)


def test_future_hire_gets_the_date_message(client, svc):
    emp = svc.add_employee("Gelecek Kisi", "IT", D(2027, 2, 1))
    assert_refused(post(client, employee_id=str(emp["id"]), on="2026-10-23"),
                   MSG_DATE_BEFORE_HIRE % "2027-02-01")


def test_csrf_error_saves_nothing(monkeypatch):
    """G-5: a form without a token saves nothing and shows the CSRF message."""
    monkeypatch.setitem(leave_app.app.config, "WTF_CSRF_ENABLED", True)
    leave_app.app.testing = True
    with leave_app.app.test_client() as c:
        resp = c.post(PATH, data={"employee_id": "2", "date": "2026-01-01", "days": "10"})
    assert resp.status_code == 400
    assert MSG_CSRF in visible_text(page(resp))
    assert leave_app.storage.opening_balances() == []


# --- AC-8: warning about pending requests before the opening date ------------------------------

def test_warning_lists_pending_before_opening(client):
    rid = add_request(2, D(2026, 9, 7), D(2026, 9, 7))
    assert rid == 9
    resp = post(client, on="2026-10-01", days="0")
    text = visible_text(page(client.get(resp.headers["Location"])))
    assert MSG_SAVED % (2, "2026-10-01", 0) in text
    assert MSG_WARNING % "#9" in text
    assert "#2" not in text.split("bekleyen talepler:")[1].split(".")[0]


def test_no_warning_without_such_pending(client):
    resp = post(client, on="2026-10-01")
    assert "bekleyen talepler" not in visible_text(page(client.get(resp.headers["Location"])))


def test_warning_disappears_once_decided(client, svc):
    """G-3: the warning is computed on every page load."""
    rid = add_request(2, D(2026, 9, 7), D(2026, 9, 7))
    location = post(client, on="2026-10-01", days="0").headers["Location"]
    svc.reject_request(rid)
    assert "bekleyen talepler" not in visible_text(page(client.get(location)))


# --- AC-9: approval exemption ---------------------------------------------------------------------

def test_pending_before_opening_is_approved_without_balance_check(client, svc):
    rid = add_request(2, D(2026, 9, 7), D(2026, 9, 11))   # 5 working days, Kalan 0
    post(client, on="2026-10-01", days="0")
    assert svc.get_remaining(leave_app.storage.employees()[1]) == 0
    resp = client.post(f"/requests/{rid}/approve")
    assert resp.status_code == 302
    assert "Talep #%d onaylandı." % rid in visible_text(page(client.get(resp.headers["Location"])))
    assert status_of(rid) == "Onaylandi"
    assert svc.get_remaining(leave_app.storage.employees()[1]) == 0


def test_pending_after_opening_keeps_br10(client):
    """#2 (2026-11-02, 3 days) starts after the opening date: Kalan 0 < 3, it stays pending."""
    post(client, on="2026-10-01", days="0")
    resp = client.post("/requests/2/approve")
    assert resp.status_code == 400
    assert ("Personelin kalan izin bakiyesi yetersiz (kalan 0 gün, talep 3 gün)."
            in visible_text(page(resp)))
    assert status_of(2) == "Beklemede"


# --- AC-10: new request before the opening date -----------------------------------------------

def test_new_request_before_opening_is_refused(client, svc):
    from domain.errors import BeforeOpeningBalance  # new in spec 0041
    post(client, on="2026-10-01", days="20")
    before = len(leave_app.storage.requests())
    resp = client.post("/new", data={"employee_id": "2", "start": "2026-09-28",
                                     "end": "2026-10-02", "reason": "x"})
    assert resp.status_code == 400
    assert MSG_BEFORE_OPENING % "2026-10-01" in visible_text(page(resp))
    with pytest.raises(BeforeOpeningBalance) as exc:
        svc.create_request(2, D(2026, 9, 28), D(2026, 10, 2), "x")
    assert exc.value.opening_date == D(2026, 10, 1)
    assert len(leave_app.storage.requests()) == before
    ok = client.post("/new", data={"employee_id": "2", "start": "2026-10-01",
                                   "end": "2026-10-02", "reason": "x"})
    assert ok.status_code == 302
    assert len(leave_app.storage.requests()) == before + 1


@pytest.mark.parametrize("start, end, message", [
    ("2026-09-30", "2026-09-28", "Bitiş tarihi başlangıç tarihinden önce olamaz."),
    ("2026-09-26", "2026-09-27", MSG_BEFORE_OPENING % "2026-10-01"),   # yalnız hafta sonu
], ids=["range-first", "before-workdays"])
def test_order_range_then_opening_then_workdays(client, start, end, message):
    post(client, on="2026-10-01", days="20")
    resp = client.post("/new", data={"employee_id": "2", "start": start, "end": end,
                                     "reason": "x"})
    assert resp.status_code == 400
    assert message in visible_text(page(resp))


def test_without_opening_past_request_still_accepted(client):
    """BR-8 unchanged for an employee without an opening balance."""
    resp = client.post("/new", data={"employee_id": "2", "start": "2026-09-28",
                                     "end": "2026-10-02", "reason": "x"})
    assert resp.status_code == 302


# --- AC-11: log --------------------------------------------------------------------------------

def test_log_line_has_no_personal_data(client, caplog):
    with caplog.at_level(logging.INFO, logger="domain"):
        post(client)
    lines = [r.getMessage() for r in caplog.records
             if r.levelno == logging.INFO and "acilis bakiyesi" in r.getMessage()]
    assert lines == ["acilis bakiyesi: #2, giren: %s (IK)" % TEST_ACCOUNT["email"]]
    for secret in ("Mehmet", "2026-01-01", " 10"):
        assert secret not in lines[0]


def test_failed_save_logs_no_info(client, caplog):
    with caplog.at_level(logging.INFO, logger="domain"):
        post(client, days="abc")
    assert not [r for r in caplog.records if r.levelno == logging.INFO]
