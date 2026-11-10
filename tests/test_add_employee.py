"""Add employee (Yeni Personel) — spec 0022 (plan 0022).

Opening data (storage/demo.py): employees 1..5 (units IT, Muhasebe, IK, IT, Satis), so the next
employee number is 6. Domain tests call LeaveService / AccountView directly; screen tests use the
in-process client. The logged-in account is chosen per test by `as_account` (the gate's session
check is swapped, as in tests/test_authorization.py).
"""
import datetime as dt
import logging
import threading
from html.parser import HTMLParser

import pytest

import app as leave_app
from conftest import table_rows, visible_text
from domain.accounts import AccountService
from domain.auth import LoginService
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
def test_concurrent_adds_get_distinct_numbers(factory, race_window):
    """G-5: two adds at the same time get different numbers; none is lost. Spec 0026: the first
    read of the number counter waits for a second thread, so without the store's lock two adds
    get the same number on every run (tests/conftest.py, race_window)."""
    storage = factory()
    race_window.counter(storage, "_next_employee_id")
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


# --- screen (web) --------------------------------------------------------------------------------

PATH = "/personel/yeni"
MSG_CSRF = "Form geçersiz ya da süresi dolmuş. Lütfen sayfayı yenileyip tekrar deneyin."
FORM = {"name": "Deniz Ak", "department": "IT", "hire_date": "2023-03-01"}
LINK = '<a href="/personel/yeni">Yeni Personel</a>'


@pytest.fixture
def as_account(monkeypatch):
    def use(acc):
        monkeypatch.setattr(LoginService, "session_account", lambda self, email, login_at: acc)
    return use


class _Form(HTMLParser):
    """What a browser shows in the Yeni Personel form: input values, labels and suggestions."""

    def __init__(self):
        super().__init__()
        self.inputs, self.labels, self.options, self.forms = {}, {}, [], 0
        self._label = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "form" and a.get("action") != "/cikis":
            self.forms += 1
        elif tag == "input" and a.get("name"):
            self.inputs[a["name"]] = a
        elif tag == "option":
            self.options.append(a.get("value"))
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


def post(client, **changes):
    return client.post(PATH, data={**FORM, **changes})


def warnings(caplog):
    return [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]


def test_hr_sees_link_and_form(client):
    assert LINK in page(client.get("/"))
    html = page(client.get(PATH))
    f = form_of(html)
    assert f.forms == 1
    assert {"name", "department", "hire_date"} <= set(f.inputs)
    assert f.inputs["hire_date"]["type"] == "date"
    assert f.inputs["department"]["list"] == "birimler"
    # every field has a visible label bound to it (accessibility)
    assert f.labels == {"ad": "Ad", "birim": "Birim", "ise-giris": "İşe giriş tarihi"}
    assert [f.inputs[n]["id"] for n in ("name", "department", "hire_date")] == [
        "ad", "birim", "ise-giris"]
    assert '<input type="submit" value="Kaydet">' in html


def test_hr_adds_employee_with_next_number(client):
    resp = post(client)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/personel/yeni?eklendi=6")
    assert employee_ids()[-1] == 6
    stored = leave_app.storage.employees()[-1]
    assert (stored["name"], stored["department"], stored["hire_date"]) == (
        "Deniz Ak", "IT", D(2023, 3, 1))
    shown = client.get(resp.headers["Location"])
    assert shown.status_code == 200
    assert "Personel #6 eklendi: Deniz Ak (IT)." in visible_text(page(shown))


def test_new_employee_appears_on_home_and_new_request(client):
    post(client)
    rows = table_rows(page(client.get("/")))
    assert ["Deniz Ak", "IT", "14", "0", "14", "0"] in rows  # 3 years -> 14 days (BR-1)
    f = form_of(page(client.get("/new")))
    assert "6" in f.options


def test_values_are_trimmed_and_unit_reaches_manager(client, as_account):
    post(client, name=" Ayşe Yılmaz ", department=" IT ")
    stored = leave_app.storage.employees()[-1]
    assert (stored["name"], stored["department"]) == ("Ayşe Yılmaz", "IT")
    as_account(MANAGER)  # IT manager (spec 0021)
    names = [row[0] for row in table_rows(page(client.get("/")))[1:]]
    assert "Ayşe Yılmaz" in names


@pytest.mark.parametrize("changes, message", [
    pytest.param({"name": ""}, "Ad girin.", id="name-empty"),
    pytest.param({"name": "   "}, "Ad girin.", id="name-spaces"),
    pytest.param({"department": ""}, "Birim girin.", id="unit-empty"),
    pytest.param({"name": "A" * 101}, "Ad en fazla 100 karakter olabilir.", id="name-101"),
    pytest.param({"department": "U" * 51}, "Birim en fazla 50 karakter olabilir.", id="unit-51"),
    pytest.param({"hire_date": ""}, "Geçerli bir işe giriş tarihi girin.", id="date-missing"),
    pytest.param({"hire_date": "2023-02-30"}, "Geçerli bir işe giriş tarihi girin.",
                 id="date-bad"),
    pytest.param({"hire_date": "1949-12-31"}, "İşe giriş tarihi 1950-01-01'den önce olamaz.",
                 id="date-1949-12-31"),
])
def test_invalid_input_is_refused(client, changes, message):
    before = list(employee_ids())
    resp = post(client, **changes)
    assert resp.status_code == 400
    html = page(resp)
    assert message in visible_text(html)
    assert employee_ids() == before
    sent = {**FORM, **changes}
    f = form_of(html)
    assert f.inputs["name"]["value"] == sent["name"]
    assert f.inputs["department"]["value"] == sent["department"]
    expected_date = "" if sent["hire_date"] in ("", "2023-02-30") else sent["hire_date"]
    assert f.inputs["hire_date"]["value"] == expected_date


def test_hire_date_field_missing_from_the_post_is_refused(client):
    before = list(employee_ids())
    resp = client.post(PATH, data={"name": "Ali", "department": "IT"})
    assert resp.status_code == 400
    assert "Geçerli bir işe giriş tarihi girin." in visible_text(page(resp))
    assert employee_ids() == before


@pytest.mark.parametrize("changes, message", [
    pytest.param({"name": "", "department": "", "hire_date": "bozuk"}, "Ad girin.",
                 id="name-first"),
    pytest.param({"department": "", "hire_date": "bozuk"}, "Birim girin.", id="unit-before-date"),
    pytest.param({"name": "A" * 101, "department": "U" * 51},
                 "Ad en fazla 100 karakter olabilir.", id="long-name-before-long-unit"),
])
def test_first_error_wins_in_order(client, changes, message):
    text = visible_text(page(post(client, **changes)))
    shown = [m for m in ("Ad girin.", "Birim girin.", "Ad en fazla 100 karakter olabilir.",
                         "Birim en fazla 50 karakter olabilir.",
                         "Geçerli bir işe giriş tarihi girin.") if m in text]
    assert shown == [message]


@pytest.mark.parametrize("changes", [
    pytest.param({"name": "A" * 100}, id="name-100"),
    pytest.param({"department": "U" * 50}, id="unit-50"),
    pytest.param({"hire_date": "1950-01-01"}, id="date-1950-01-01"),
])
def test_boundaries_are_accepted(client, changes):
    resp = post(client, **changes)
    assert resp.status_code == 302
    stored = leave_app.storage.employees()[-1]
    sent = {**FORM, **changes}
    assert (stored["name"], stored["department"], stored["hire_date"].isoformat()) == (
        sent["name"], sent["department"], sent["hire_date"])


def test_html_in_name_is_shown_as_text(client):
    evil = "<script>alert(1)</script>"
    unit = "<b>IT</b>"
    resp = post(client, name=evil, department=unit)
    assert leave_app.storage.employees()[-1]["name"] == evil  # stored as written
    for html in (page(client.get(resp.headers["Location"])), page(client.get("/")),
                 page(client.get("/new")), page(client.get(PATH))):
        assert "<script>alert(1)" not in html and "<b>IT</b>" not in html
    assert evil in visible_text(page(client.get("/")))
    error = page(post(client, name=evil, department=""))  # echoed back escaped, too
    assert "<script>alert(1)" not in error


def test_future_hire_date_is_accepted_with_zero_entitlement(client):
    resp = post(client, hire_date="2027-02-01")
    assert resp.status_code == 302
    assert ["Deniz Ak", "IT", "0", "0", "0", "0"] in table_rows(page(client.get("/")))


def test_same_name_and_unit_twice_on_screen(client):
    post(client)
    post(client)
    assert [e["id"] for e in leave_app.storage.employees() if e["name"] == "Deniz Ak"] == [6, 7]


def test_success_redirects_to_empty_form_and_refresh_does_not_repeat(client):
    target = post(client).headers["Location"]
    for _ in range(2):  # a refresh is a GET of the same address
        f = form_of(page(client.get(target)))
        assert (f.inputs["name"]["value"], f.inputs["department"]["value"],
                f.inputs["hire_date"]["value"]) == ("", "", "")
    assert employee_ids() == [1, 2, 3, 4, 5, 6]


@pytest.mark.parametrize("param", ["eklendi=999", "eklendi=abc", "eklendi=%EF%BC%92",
                                   "eklendi=" + "9" * 5000, ""])
def test_success_message_needs_a_real_employee(client, param):
    resp = client.get(PATH + "?" + param)
    assert resp.status_code == 200
    assert "eklendi:" not in visible_text(page(resp))


def test_unit_suggestions_are_distinct_and_sorted(client):
    post(client, department="Arge")
    post(client, department="it")  # case is kept: a different unit (spec 0021 exact match)
    post(client, department="IT")
    f = form_of(page(client.get(PATH)))
    assert f.options == ["Arge", "IK", "IT", "Muhasebe", "Satis", "it"]


def test_unit_suggestions_are_empty_without_employees(client, monkeypatch):
    monkeypatch.setattr(leave_app.storage, "_employees", [])  # MemoryStorage detail
    assert form_of(page(client.get(PATH))).options == []


@pytest.mark.parametrize("acc", [pytest.param(STAFF, id="Personel"),
                                 pytest.param(MANAGER, id="Yonetici"),
                                 pytest.param(STAFF_UNLINKED, id="unlinked-Personel")])
def test_link_hidden_for_other_roles(client, as_account, acc):
    as_account(acc)
    for path in ("/", "/requests", "/new"):
        html = page(client.get(path))
        assert "Yeni Personel" not in html
        assert "Ana Sayfa | Talepler | Yeni Talep | " in visible_text(html)  # the rest stays


def test_unlinked_hr_can_add(client, as_account):
    as_account(HR)
    assert LINK in page(client.get("/"))
    assert post(client).status_code == 302
    assert employee_ids()[-1] == 6


@pytest.mark.parametrize("acc", [pytest.param(STAFF, id="Personel"),
                                 pytest.param(MANAGER, id="Yonetici"),
                                 pytest.param(STAFF_UNLINKED, id="unlinked-Personel")])
def test_others_cannot_open_or_post(client, as_account, caplog, acc):
    as_account(acc)
    before = list(employee_ids())
    with caplog.at_level(logging.WARNING):
        opened = client.get(PATH)
        sent = post(client)
    for resp in (opened, sent):
        assert resp.status_code == 403
        html = page(resp)
        assert MSG_FORBIDDEN in visible_text(html)
        assert form_of(html).forms == 0  # no form for them
    assert employee_ids() == before
    assert warnings(caplog) == ["yetkisiz islem: %s, personel ekleme, hedef None"
                                % acc["email"]] * 2


def test_unauthorized_invalid_post_is_403(client, as_account):
    as_account(MANAGER)
    resp = client.post(PATH, data={"name": "", "department": "", "hire_date": "bozuk"})
    assert resp.status_code == 403
    text = visible_text(page(resp))
    assert MSG_FORBIDDEN in text and "Ad girin." not in text


@pytest.fixture
def csrf_client(monkeypatch):
    monkeypatch.setitem(leave_app.app.config, "WTF_CSRF_ENABLED", True)
    leave_app.app.testing = True
    with leave_app.app.test_client() as c:
        yield c


@pytest.mark.parametrize("token", ["missing", "bad"])
def test_add_employee_needs_csrf_token(csrf_client, token):
    assert "csrf_token" in form_of(page(csrf_client.get(PATH))).inputs
    data = dict(FORM)
    if token == "bad":
        data["csrf_token"] = "bozuk-token"
    before = list(employee_ids())
    resp = csrf_client.post(PATH, data=data)
    assert resp.status_code == 400
    html = page(resp)
    assert MSG_CSRF in visible_text(html)
    assert html.index(MSG_CSRF) < html.index("<h3>Yeni Personel")
    assert form_of(html).inputs["name"]["value"] == ""  # values are not echoed (spec 0015 K-2)
    assert employee_ids() == before


def test_csrf_failure_shows_no_form_to_other_roles(csrf_client, as_account):
    as_account(STAFF)
    before = list(employee_ids())
    resp = csrf_client.post(PATH, data=FORM)
    assert resp.status_code == 400
    text = visible_text(page(resp))
    assert MSG_CSRF in text and MSG_FORBIDDEN in text
    assert form_of(page(resp)).forms == 0
    assert employee_ids() == before


@pytest.mark.parametrize("unit, logged", [
    pytest.param("IT\n2026-11-10 INFO sahte satir", r"IT\n2026-11-10 INFO sahte satir",
                 id="LF"),
    pytest.param("IT\r\nX", r"IT\r\nX", id="CRLF"),
    pytest.param("A\N{LINE SEPARATOR}B\tC", "A\\u" "2028B\\tC", id="line-separator-and-tab"),
    pytest.param("Arge Ğüşıöç", "Arge Ğüşıöç", id="printable-unchanged"),
])
def test_unit_cannot_forge_log_lines(svc, caplog, unit, logged):
    """Review 0022 F-1: the unit is user text; control characters are escaped in the log line."""
    with caplog.at_level(logging.INFO, logger="domain.leave_service"):
        record = svc.for_account(HR).add_employee("Ali", unit, D(2020, 1, 6))
    lines = [r.getMessage() for r in caplog.records if r.name == "domain.leave_service"]
    assert lines == ["personel eklendi: #%d (%s), ekleyen: ik@firma.com (IK)"
                     % (record["id"], logged)]
    assert all("\n" not in line and "\r" not in line for line in lines)
