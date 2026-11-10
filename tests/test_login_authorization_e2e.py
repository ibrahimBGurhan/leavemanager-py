"""Role rules through the real login — spec 0023 (issue #43, 0020 G-1).

The other authorization tests swap the session check (`as_account`). Here nothing is swapped:
`logged_out` (conftest) restores the real check, accounts are stored with the real hasher, the
login goes through the /giris form, CSRF is on and every form uses the token from its own page.
So the tests also prove that the account in the session is the one the screens are built for.

Opening data (storage/demo.py): A = Ayse Yilmaz (1, IT; requests 1 Onaylandi, 5 Beklemede),
B = Mehmet Demir (2, Muhasebe; requests 2 Beklemede, 8 Reddedildi).
"""
import logging
import re

import pytest

import app as leave_app
from conftest import table_rows, visible_text

pytestmark = pytest.mark.usefixtures("logged_out")

PASSWORD = "uctan uca sifre 12"
STAFF = "ayse@firma.com"            # Personel, linked to A
UNLINKED = "bagsiz@firma.com"       # Personel, no employee record
A_NAME, B_NAME, B_DEPT = "Ayse Yilmaz", "Mehmet Demir", "Muhasebe"
B_PENDING = 2
MSG_FORBIDDEN = "Bu işlem için yetkiniz yok."
MSG_NO_EMPLOYEE = "Hesabınız bir personel kaydına bağlı değil; talep açmak için İK ile görüşün."
TOKEN = re.compile(r"""name=['"]csrf_token['"] value=['"]([^'"]+)['"]""")
DAY = "2026-11-16"


@pytest.fixture
def browser(monkeypatch):
    """A client with CSRF on, like a real browser session."""
    monkeypatch.setitem(leave_app.app.config, "WTF_CSRF_ENABLED", True)
    leave_app.app.testing = True
    with leave_app.app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def accounts():
    for email, employee_id in ((STAFF, 1), (UNLINKED, None)):
        leave_app.storage.add_account({
            "email": email, "password_hash": leave_app.hasher.hash(PASSWORD),
            "role": "Personel", "employee_id": employee_id, "active": True,
            "failed_attempts": 0, "locked_until": None})


def html(resp):
    return resp.get_data(as_text=True)


def token(page):
    m = TOKEN.search(page)
    assert m, "no csrf_token on the page"
    return m.group(1)


def login(client, email):
    resp = client.post("/giris", data={"eposta": email, "sifre": PASSWORD,
                                       "csrf_token": token(html(client.get("/giris")))})
    assert resp.status_code == 302 and resp.headers["Location"] == "/", "login failed"


def post_form(client, page, path, data):
    """Submit like a browser: take the token from the page that holds the form."""
    return client.post(path, data={**data, "csrf_token": token(html(client.get(page)))})


def counts(text):
    return [int(n) for n in re.findall(r"(?:Bekleyen|Onaylanan|Reddedilen): (\d+)", text)]


def requests_of(employee_id):
    return [(r["id"], r["status"]) for r in leave_app.storage.requests()
            if r["employee_id"] == employee_id]


def test_linked_staff_sees_only_own_data_after_real_login(browser):
    login(browser, STAFF)
    home = html(browser.get("/"))
    text = visible_text(home)
    assert STAFF in text                                   # the session's account is shown
    assert counts(text) == [1, 1, 0]                       # A: 5 pending, 1 approved
    rows = table_rows(home)
    assert rows[1:] == [[A_NAME, "IT", "26", "9", "17", "3"]]
    assert B_NAME not in text and B_DEPT not in text

    listing = html(browser.get("/requests"))
    names = {row[0] for row in table_rows(listing)[1:]}
    assert names == {A_NAME}
    assert "/approve" not in listing and "/reject" not in listing   # no Onayla / Reddet forms
    assert "value='Onayla'" not in listing and "value='Reddet'" not in listing
    assert B_NAME not in visible_text(listing)


def test_linked_staff_creates_own_request_after_real_login(browser):
    login(browser, STAFF)
    form = html(browser.get("/new"))
    assert "<select" not in form and A_NAME in visible_text(form)
    before = requests_of(1)
    resp = post_form(browser, "/new", "/new", {"start": DAY, "end": DAY, "reason": "uctan uca"})
    assert resp.status_code == 302
    new = [r for r in leave_app.storage.requests() if r["reason"] == "uctan uca"]
    assert [(r["employee_id"], r["status"]) for r in new] == [(1, "Beklemede")]
    assert len(requests_of(1)) == len(before) + 1


def test_linked_staff_is_refused_for_others_after_real_login(browser, caplog):
    login(browser, STAFF)
    before = [dict(r) for r in leave_app.storage.requests()]
    with caplog.at_level(logging.WARNING, logger="domain.access"):
        approve = post_form(browser, "/requests", "/requests/%d/approve" % B_PENDING, {})
        for_b = post_form(browser, "/new", "/new",
                          {"employee_id": "2", "start": DAY, "end": DAY, "reason": "B adina"})
    for resp in (approve, for_b):
        assert resp.status_code == 403
        text = visible_text(html(resp))
        assert MSG_FORBIDDEN in text
        assert B_NAME not in text and "Aile ziyareti" not in text
    assert [dict(r) for r in leave_app.storage.requests()] == before
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 2
    assert all(w.startswith("yetkisiz islem: %s, " % STAFF) for w in warnings)
    assert ", onay, " in warnings[0] and ", baskasi adina talep, " in warnings[1]

    assert "Yeni Personel" not in html(browser.get("/"))
    assert browser.get("/personel/yeni").status_code == 403


def test_unlinked_staff_sees_nothing_and_cannot_request_after_real_login(browser):
    login(browser, UNLINKED)
    home = html(browser.get("/"))
    text = visible_text(home)
    assert UNLINKED in text
    assert counts(text) == [0, 0, 0]
    assert table_rows(home)[1:] == []                      # header only, no balance row
    listing = browser.get("/requests")              # review 0023 F-1: cannot pass vacuously
    assert listing.status_code == 200
    assert table_rows(html(listing)) == [["Personel", "Baslangic", "Bitis", "Gun", "Neden",
                                          "Durum"]]       # header only, no request row

    form = browser.get("/new")
    assert form.status_code == 200
    assert MSG_NO_EMPLOYEE in visible_text(html(form))
    assert "<form method=\"post\">" not in html(form)      # no request form

    before = [dict(r) for r in leave_app.storage.requests()]
    resp = browser.post("/new", data={"start": DAY, "end": DAY, "reason": "x",
                                      "csrf_token": token(html(form))})  # logout form's token
    assert resp.status_code == 403
    assert MSG_FORBIDDEN in visible_text(html(resp))
    assert [dict(r) for r in leave_app.storage.requests()] == before


def test_logout_then_other_account_does_not_carry_scope(browser):
    login(browser, STAFF)
    assert A_NAME in visible_text(html(browser.get("/")))
    out = post_form(browser, "/", "/cikis", {})
    assert out.status_code == 302 and out.headers["Location"] == "/giris?durum=cikis"
    gone = browser.get("/")
    assert gone.status_code == 302 and gone.headers["Location"] == "/giris"

    login(browser, UNLINKED)
    text = visible_text(html(browser.get("/")))
    assert UNLINKED in text and STAFF not in text
    assert A_NAME not in text and counts(text) == [0, 0, 0]
