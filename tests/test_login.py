"""Login screen, the default-deny gate, session and logout — spec 0019 (ADR-0002 D-4…D-6).

Every test here uses `logged_out` (conftest): the real session check runs. Accounts are added to
the app's in-memory storage with the real hasher; "now" is frozen through the clock seam and moved
forward by the tests (G-6). CSRF is off in the shared `client` and on in `csrf_client`.
"""
import datetime as dt
import logging
import os
import re
from email.utils import parsedate_to_datetime

import pytest

import app as leave_app
from conftest import visible_text

pytestmark = pytest.mark.usefixtures("logged_out")

T0 = dt.datetime(2026, 11, 6, 9, 0, 0)
EMAIL = "ali@firma.com"
PASSWORD = "dogru parola 12"
WRONG = "yanlis parola 1"
MSG_FAILED = "E-posta ya da şifre hatalı."
MSG_EXPIRED = "Oturumunuzun süresi doldu. Lütfen tekrar giriş yapın."
MSG_LOGGED_OUT = "Çıkış yapıldı."
MSG_LOCK_NOTE = "Çok sayıda hatalı denemeden sonra hesap geçici olarak kilitlenir."
MSG_CSRF = "Form geçersiz ya da süresi dolmuş. Lütfen sayfayı yenileyip tekrar deneyin."
TOKEN = re.compile(r"""name=['"]csrf_token['"] value=['"]([^'"]+)['"]""")
NEW_REQUEST = {"employee_id": "2", "start": "2026-11-16", "end": "2026-11-16", "reason": "x"}


class Now:
    def __init__(self):
        self.current = T0

    def __call__(self):
        return self.current


@pytest.fixture
def csrf_client(monkeypatch):
    monkeypatch.setitem(leave_app.app.config, "WTF_CSRF_ENABLED", True)
    leave_app.app.testing = True
    with leave_app.app.test_client() as c:
        yield c


@pytest.fixture
def now(monkeypatch):
    clock = Now()
    monkeypatch.setattr(leave_app.clock, "now", clock)
    return clock


def add_account(email=EMAIL, password=PASSWORD, active=True):
    leave_app.storage.add_account({
        "email": email, "password_hash": leave_app.hasher.hash(password), "role": "IK",
        "employee_id": None, "active": active, "failed_attempts": 0, "locked_until": None})


@pytest.fixture
def account(now):
    add_account()
    return EMAIL


def login(client, email=EMAIL, password=PASSWORD):
    return client.post("/giris", data={"eposta": email, "sifre": password})


def snapshot():
    return ([dict(r) for r in leave_app.storage.requests()],
            [dict(a) for a in leave_app.storage.accounts()])


def goes_to(resp, where):
    return resp.status_code == 302 and resp.headers["Location"] == where


def logged_in_as(client, email=EMAIL):
    resp = client.get("/")
    return resp.status_code == 200 and email in visible_text(resp.get_data(as_text=True))


# --- AC-1: default deny ------------------------------------------------------------------------

CLOSED = [("get", "/", None), ("get", "/requests", None), ("get", "/new", None),
          ("post", "/new", NEW_REQUEST), ("post", "/requests/2/approve", {}),
          ("post", "/requests/2/reject", {}), ("get", "/yok-boyle-bir-sayfa", None),
          ("post", "/cikis", {})]


@pytest.mark.parametrize("method, path, data", CLOSED, ids=[f"{m}{p}" for m, p, _ in CLOSED])
def test_logged_out_requests_go_to_login(client, method, path, data):
    before = snapshot()
    resp = getattr(client, method)(path, data=data)
    assert goes_to(resp, "/giris")
    assert snapshot() == before
    html = resp.get_data(as_text=True)
    assert "Ayse" not in html and "Beklemede" not in html


def test_every_route_is_closed(client):
    """A route added later is closed unless it is listed as open on purpose."""
    open_rules = []
    for rule in leave_app.app.url_map.iter_rules():
        path = re.sub(r"<[^>]+>", "1", rule.rule)
        if rule.endpoint == "static":
            continue
        for method in sorted(rule.methods - {"HEAD", "OPTIONS"}):
            resp = client.open(path, method=method)
            if not goes_to(resp, "/giris"):
                open_rules.append((method, rule.rule))
    assert open_rules == [("GET", "/giris"), ("POST", "/giris")]


def test_logged_out_post_without_csrf_token_shows_no_data(csrf_client):
    """Plan 0019 Risk 3: the gate runs before CSRF, whose error page shows the request list."""
    before = snapshot()
    for path, data in [("/requests/2/approve", {}), ("/new", NEW_REQUEST), ("/cikis", {})]:
        resp = csrf_client.post(path, data=data)
        assert goes_to(resp, "/giris"), path
        assert "Ayse" not in resp.get_data(as_text=True)
    assert snapshot() == before


# --- AC-2: login -------------------------------------------------------------------------------

@pytest.mark.parametrize("typed", [EMAIL, "  ALI@Firma.COM "])
def test_login_lands_on_home(client, account, typed):
    assert goes_to(login(client, typed), "/")
    assert logged_in_as(client)


def test_login_always_goes_home(client, account):
    assert goes_to(client.get("/new"), "/giris")
    assert goes_to(client.post("/giris?next=/new", data={"eposta": EMAIL, "sifre": PASSWORD}), "/")


def test_logged_in_pages_show_email_and_logout(client, account):
    login(client)
    for path in ("/", "/requests", "/new"):
        html = client.get(path).get_data(as_text=True)
        assert EMAIL in visible_text(html), path
        assert '<button type="submit" form="cikis-formu">Çıkış</button>' in html
        assert '<form id="cikis-formu" method="post" action="/cikis">' in html
    assert "Bekleyen:" in visible_text(client.get("/").get_data(as_text=True))
    assert "Izin Talepleri" in visible_text(client.get("/requests").get_data(as_text=True))
    assert "Kaydet" in client.get("/new").get_data(as_text=True)


def test_menu_email_is_escaped(client, now):
    odd = "<b>x</b>@firma.com"
    add_account(odd)
    login(client, odd)
    html = client.get("/").get_data(as_text=True)
    assert "&lt;b&gt;x&lt;/b&gt;@firma.com" in html and "<b>x</b>" not in html


# --- AC-3: one refusal for every reason --------------------------------------------------------

def lock(client):
    for _ in range(5):
        login(client, EMAIL, WRONG)


REFUSALS = {
    "unknown": ("yok@firma.com", PASSWORD), "wrong": (EMAIL, WRONG),
    "inactive": ("pasif@firma.com", PASSWORD), "locked": (EMAIL, PASSWORD),
    "empty-email": ("", PASSWORD), "empty-password": (EMAIL, ""),
}


@pytest.mark.parametrize("case", REFUSALS)
def test_refusals_look_the_same(client, account, case):
    add_account("pasif@firma.com", active=False)
    if case == "locked":
        lock(client)
    email, password = REFUSALS[case]
    resp = login(client, email, password)
    html = resp.get_data(as_text=True)
    assert resp.status_code == 401
    assert MSG_FAILED in visible_text(html)
    assert f'value="{email}"' in html
    assert password not in html or not password
    assert 'name="sifre" autocomplete="current-password">' in html     # empty password field
    assert goes_to(client.get("/"), "/giris")


def test_refusal_page_is_the_same_text_for_every_reason(client, account):
    add_account("pasif@firma.com", active=False)
    pages = set()
    for email, password in [("yok@firma.com", PASSWORD), (EMAIL, WRONG),
                            ("pasif@firma.com", PASSWORD)]:
        html = login(client, email, password).get_data(as_text=True)
        pages.add(visible_text(html.replace(email, "E")))
    assert len(pages) == 1


def test_email_echo_is_escaped(client, account):
    html = login(client, '"><script>x</script>', PASSWORD).get_data(as_text=True)
    assert "<script>x</script>" not in html
    assert "&#34;&gt;&lt;script&gt;" in html


# --- AC-4: lock through the screen, and across a restart is in test_auth.py ---------------------

def test_lock_through_the_screen(client, account, now):
    lock(client)
    assert login(client).status_code == 401                     # right password, still locked
    now.current = T0 + dt.timedelta(minutes=15)
    assert goes_to(login(client), "/")


# --- AC-6: log through the screen --------------------------------------------------------------

def test_screen_logs_without_secrets(client, account, caplog):
    caplog.set_level(logging.INFO)
    login(client, "parola-yanlis-alana", PASSWORD)
    login(client, EMAIL, WRONG)
    login(client)
    client.post("/cikis")
    messages = [(r.levelname, r.getMessage()) for r in caplog.records if r.name == "domain.auth"]
    assert messages == [("WARNING", "başarısız giriş: bilinmeyen hesap"),
                        ("WARNING", "başarısız giriş: ali@firma.com (art arda 1)"),
                        ("INFO", "giriş: ali@firma.com"), ("INFO", "çıkış: ali@firma.com")]
    for secret in ("parola-yanlis-alana", PASSWORD, WRONG, "scrypt:"):
        assert secret not in caplog.text


# --- AC-7: eight hours -------------------------------------------------------------------------

@pytest.mark.parametrize("after, valid", [(dt.timedelta(hours=8, seconds=-1), True),
                                          (dt.timedelta(hours=8), False)],
                         ids=["7:59:59", "8:00:00"])
def test_session_lasts_eight_hours(client, account, now, after, valid):
    login(client)
    now.current = T0 + after
    resp = client.get("/requests")
    if valid:
        assert resp.status_code == 200
    else:
        assert goes_to(resp, "/giris?durum=sure")
        assert MSG_EXPIRED in visible_text(client.get("/giris?durum=sure").get_data(as_text=True))
        assert goes_to(client.get("/"), "/giris")               # the session is gone


def test_activity_does_not_extend_session(client, account, now):
    login(client)
    for hour in range(1, 8):
        now.current = T0 + dt.timedelta(hours=hour)
        assert client.get("/").status_code == 200
    now.current = T0 + dt.timedelta(hours=8)
    assert goes_to(client.get("/"), "/giris?durum=sure")


def test_expired_post_changes_nothing(client, account, now):
    login(client)
    now.current = T0 + dt.timedelta(hours=9)
    before = snapshot()
    assert goes_to(client.post("/requests/2/approve"), "/giris?durum=sure")
    assert snapshot() == before


def test_relogin_starts_new_session(client, account, now):
    login(client)
    now.current = T0 + dt.timedelta(hours=7)
    login(client)
    now.current = T0 + dt.timedelta(hours=14, minutes=59)
    assert client.get("/").status_code == 200


# --- AC-8: account changes during the session ---------------------------------------------------

@pytest.mark.parametrize("change", ["inactive", "deleted"])
def test_inactive_or_deleted_account_ends_session(client, account, change):
    login(client)
    if change == "inactive":
        leave_app.storage.set_account_active(EMAIL, False)
    else:
        leave_app.storage._accounts.clear()           # no delete in the contract yet (G-2)
    before = snapshot()
    assert goes_to(client.post("/requests/2/approve"), "/giris")
    assert snapshot() == before
    if change == "inactive":
        leave_app.storage.set_account_active(EMAIL, True)
        assert goes_to(client.get("/"), "/giris")      # the session was ended, not just refused


# --- AC-9: fixation and logout -----------------------------------------------------------------

def test_login_drops_earlier_session_data(client, account):
    with client.session_transaction() as s:
        s["planted"] = "x"
        s["hesap"] = "baskasi@firma.com"
    login(client)
    with client.session_transaction() as s:
        assert "planted" not in s and s["hesap"] == EMAIL


def test_logout_ends_session(client, account):
    login(client)
    resp = client.post("/cikis")
    assert goes_to(resp, "/giris?durum=cikis")
    with client.session_transaction() as s:
        assert dict(s) == {}
    assert MSG_LOGGED_OUT in visible_text(client.get("/giris?durum=cikis").get_data(as_text=True))
    assert goes_to(client.get("/"), "/giris")


def csrf_login(c):
    token = TOKEN.search(c.get("/giris").get_data(as_text=True)).group(1)
    return c.post("/giris", data={"eposta": EMAIL, "sifre": PASSWORD, "csrf_token": token})


@pytest.mark.parametrize("token", [None, "bozuk"])
def test_logout_needs_csrf_token(csrf_client, account, token):
    assert goes_to(csrf_login(csrf_client), "/")
    data = {} if token is None else {"csrf_token": token}
    resp = csrf_client.post("/cikis", data=data)
    assert resp.status_code == 400 and MSG_CSRF in visible_text(resp.get_data(as_text=True))
    assert logged_in_as(csrf_client)


def test_logout_with_token_works(csrf_client, account):
    csrf_login(csrf_client)
    html = csrf_client.get("/").get_data(as_text=True)
    form = html.split('<form id="cikis-formu"')[1].split("</form>")[0]
    resp = csrf_client.post("/cikis", data={"csrf_token": TOKEN.search(form).group(1)})
    assert goes_to(resp, "/giris?durum=cikis")


def test_logout_by_get_is_not_allowed(client, account):
    login(client)
    assert client.get("/cikis").status_code == 405
    assert logged_in_as(client)


# --- AC-10: login screen -----------------------------------------------------------------------

def test_login_page_shape(csrf_client):
    html = csrf_client.get("/giris").get_data(as_text=True)
    assert "<title>Giriş</title>" in html and "<h3>Giriş</h3>" in html
    assert '<input type="submit" value="Giriş Yap">' in html
    assert 'href="/requests"' not in html and "cikis" not in html          # no menu
    assert '<label for="eposta">' in html and 'id="eposta"' in html
    assert '<label for="sifre">' in html and 'id="sifre"' in html and 'type="password"' in html
    assert 'autocomplete="username"' in html and 'autocomplete="current-password"' in html
    assert MSG_LOCK_NOTE in visible_text(html)
    assert TOKEN.search(html)


@pytest.mark.parametrize("durum, shown", [("sure", MSG_EXPIRED), ("cikis", MSG_LOGGED_OUT),
                                          ("<script>", None), ("", None)])
def test_login_page_status_messages(client, durum, shown):
    text = visible_text(client.get("/giris?durum=" + durum).get_data(as_text=True))
    for message in (MSG_EXPIRED, MSG_LOGGED_OUT):
        assert (message in text) == (message == shown)
    assert "<script>" not in client.get("/giris?durum=" + durum).get_data(as_text=True)


@pytest.mark.parametrize("token", [None, "bozuk"])
def test_login_without_csrf_token_is_refused(csrf_client, account, token):
    data = {"eposta": EMAIL, "sifre": PASSWORD}
    if token:
        data["csrf_token"] = token
    resp = csrf_client.post("/giris", data=data)
    assert resp.status_code == 400
    text = visible_text(resp.get_data(as_text=True))
    assert MSG_CSRF in text and "Giriş" in text
    assert goes_to(csrf_client.get("/"), "/giris")


@pytest.mark.parametrize("between", ["/favicon.ico", "/yok-boyle-bir-sayfa", "/requests"])
def test_request_between_login_page_and_submit_keeps_the_form_valid(csrf_client, account, between):
    """Review 0019 F-1: the browser asks for /favicon.ico (or a second tab opens a page) after the
    login page; the gate must not drop the login form's CSRF token on the way."""
    token = TOKEN.search(csrf_client.get("/giris").get_data(as_text=True)).group(1)
    assert goes_to(csrf_client.get(between), "/giris")
    resp = csrf_client.post("/giris", data={"eposta": EMAIL, "sifre": PASSWORD,
                                            "csrf_token": token})
    assert goes_to(resp, "/")


def test_expired_session_keeps_the_form_valid(csrf_client, account, now):
    """Review 0019 F-1: an expired session sends the user to login; that login must still work."""
    assert goes_to(csrf_login(csrf_client), "/")
    now.current = T0 + dt.timedelta(hours=8)
    token = TOKEN.search(csrf_client.get("/giris").get_data(as_text=True)).group(1)
    assert goes_to(csrf_client.get("/requests"), "/giris?durum=sure")
    resp = csrf_client.post("/giris", data={"eposta": EMAIL, "sifre": PASSWORD,
                                            "csrf_token": token})
    assert goes_to(resp, "/")
    assert logged_in_as(csrf_client)


@pytest.mark.parametrize("change", ["expired", "inactive"])
def test_ended_session_sends_no_more_cookies(client, account, now, change):
    """Review 0019 round 2 F-1: once the gate ends a session, nothing of the login is left, and
    later logged-out requests get no fresh 8-hour cookie."""
    login(client)
    if change == "expired":
        now.current = T0 + dt.timedelta(hours=8)
    else:
        leave_app.storage.set_account_active(EMAIL, False)
    assert client.get("/requests").status_code == 302
    with client.session_transaction() as s:
        assert dict(s) == {}
    resp = client.get("/favicon.ico")
    assert goes_to(resp, "/giris") and "Set-Cookie" not in resp.headers


def test_logged_in_user_skips_login_page(client, account):
    login(client)
    assert goes_to(client.get("/giris"), "/")


def test_keyboard_path(client):
    """Fields and the submit button sit in one form, in order: Tab moves e-posta -> şifre ->
    Giriş Yap and Enter submits (no script needed)."""
    html = client.get("/giris").get_data(as_text=True)
    form = html.split("<form")[1].split("</form>")[0]
    assert form.index('id="eposta"') < form.index('id="sifre"') < form.index('type="submit"')
    assert "tabindex" not in html and "<script" not in html


# --- AC-11: cookie ----------------------------------------------------------------------------

@pytest.mark.parametrize("value, secure", [("1", True), (None, False), ("0", False),
                                           ("true", False), ("", False)])
def test_cookie_secure_from_environment(value, secure):
    environ = {} if value is None else {"SESSION_COOKIE_SECURE": value}
    assert leave_app.cookie_secure(environ) is secure


@pytest.mark.parametrize("secure", [True, False])
def test_session_cookie_flags(client, account, monkeypatch, secure):
    monkeypatch.setitem(leave_app.app.config, "SESSION_COOKIE_SECURE", secure)
    cookie = login(client).headers["Set-Cookie"]
    assert cookie.startswith("session=")
    assert "HttpOnly" in cookie and "SameSite=Lax" in cookie
    assert ("Secure" in cookie.split("; ")) is secure


def test_session_cookie_expires_after_eight_hours(client, account):
    """Review 0019 N-2: the browser drops the cookie after 8 hours (R-7). The server-side limit
    is proven by test_session_lasts_eight_hours; this pins session.permanent and the lifetime."""
    sent = dt.datetime.now(dt.timezone.utc)
    cookie = login(client).headers["Set-Cookie"]
    expires = [part for part in cookie.split("; ") if part.startswith("Expires=")]
    assert len(expires) == 1
    at = parsedate_to_datetime(expires[0].removeprefix("Expires="))
    assert abs(at - sent - dt.timedelta(hours=8)) < dt.timedelta(minutes=1)


def test_app_reads_cookie_setting_from_environment():
    assert leave_app.app.config["SESSION_COOKIE_SECURE"] is leave_app.cookie_secure(os.environ)
