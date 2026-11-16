"""Bootstrap shell and login screen — spec 0034 (ADR-0003, plan 0034).

Bootstrap is vendored under web/static/vendor/ and served by the app itself; its files are pinned
by SHA-256 (plan 0034 "Sabitlenen özetler"). Static files need no login; screens still do (G-3).
"""
import hashlib
import pathlib
import re

import pytest

import app as leave_app
from conftest import BOOTSTRAP_JS, current_links, page_links, scripts, visible_text
from domain.auth import LoginService

ROOT = pathlib.Path(__file__).resolve().parent.parent
VENDOR = ROOT / "web" / "static" / "vendor" / "bootstrap-5.3.8"
PINNED = {  # plan 0034, Sabitlenen özetler — doğrulandı: release zip SHA-256 + config.yml SRI
    "bootstrap.min.css": "d85327d99c7a3ee1f9b5d0500d1370acea3ad2db39c163c2f51f232baedbdede",
    "bootstrap.bundle.min.js": "e4fd49181388c48ec5040bd3fe66f57c29c8e67fcd8502b3354b96ec7ab47cc7",
}
STATIC = ["/static/vendor/bootstrap-5.3.8/bootstrap.min.css",
          "/static/vendor/bootstrap-5.3.8/bootstrap.bundle.min.js"]


@pytest.mark.parametrize("name", sorted(PINNED))
def test_vendored_bootstrap_matches_pinned_sha256(name):
    """AC-2: a single changed byte (or a line-ending conversion, plan Risk 9) turns this red."""
    assert hashlib.sha256((VENDOR / name).read_bytes()).hexdigest() == PINNED[name]


@pytest.mark.usefixtures("logged_out")
def test_static_needs_no_login_screens_do(client):
    """G-3: the login screen's CSS loads before login; screens still go to the login page."""
    for path in STATIC:
        resp = client.get(path)
        assert resp.status_code == 200, path
        assert resp.data == (VENDOR / path.rsplit("/", 1)[1]).read_bytes()
    for path in ("/", "/requests", "/new", "/personel/yeni"):
        resp = client.get(path)
        assert resp.status_code == 302 and resp.headers["Location"] == "/giris", path


@pytest.mark.usefixtures("logged_out")
def test_static_serves_only_files_under_static(client):
    """G-3: the open endpoint does not reach outside web/static/."""
    for path in ("/static/../app.py", "/static/..%2fapp.py", "/static/vendor/../../templates/base.html"):
        assert client.get(path).status_code == 404, path


# --- step 3: the shell -------------------------------------------------------------------------
CSS = ["/static/vendor/bootstrap-5.3.8/bootstrap.min.css", "/static/app.css"]
NOSCRIPT = "/static/noscript.css"
EXTERNAL = re.compile(r"""(?:src|href)\s*=\s*["']\s*(?:[a-z][a-z0-9+.-]*:|//)""", re.IGNORECASE)


def account(role, employee_id, email):
    return {"email": email, "password_hash": "", "role": role, "employee_id": employee_id,
            "active": True, "failed_attempts": 0, "locked_until": None}


HR = account("IK", None, "ik@firma.com")
MANAGER = account("Yonetici", 4, "mudur@firma.com")
STAFF = account("Personel", 1, "ayse@firma.com")
ROLES = [pytest.param(HR, id="IK"), pytest.param(MANAGER, id="Yonetici"),
         pytest.param(STAFF, id="Personel")]
SCREENS = ["/", "/requests", "/new", "/personel/yeni"]
MENU = [("Ana Sayfa", "/"), ("Talepler", "/requests"), ("Yeni Talep", "/new")]


@pytest.fixture
def as_account(monkeypatch):
    def use(acc):
        monkeypatch.setattr(LoginService, "session_account", lambda self, email, login_at: acc)
    return use


def html_of(resp):
    return resp.get_data(as_text=True)


@pytest.mark.parametrize("acc", ROLES)
def test_assets_load_from_own_server(client, as_account, acc):
    """AC-1: every screen links Bootstrap's CSS, its JS bundle and app.css from the app itself;
    nothing points to another server (no scheme, no protocol-relative URL)."""
    as_account(acc)
    for path in SCREENS:
        html = html_of(client.get(path))
        for href in CSS:
            assert f'href="{href}"' in html, (path, href)
        assert scripts(html) == [(BOOTSTRAP_JS, "")], path
        assert not EXTERNAL.search(html), (path, EXTERNAL.search(html))
    for asset in CSS + [BOOTSTRAP_JS, NOSCRIPT]:
        assert client.get(asset).status_code == 200, asset


@pytest.mark.parametrize("acc, links", [
    pytest.param(HR, MENU + [("Yeni Personel", "/personel/yeni")], id="IK"),
    pytest.param(MANAGER, MENU, id="Yonetici"),
    pytest.param(STAFF, MENU, id="Personel"),
])
def test_menu_links_per_role(client, as_account, acc, links):
    """AC-3: same targets, same order; Yeni Personel only for an account that can add employees;
    e-mail and Çıkış in the bar."""
    as_account(acc)
    for path in ("/", "/requests", "/new"):
        html = html_of(client.get(path))
        assert page_links(html) == links, path
        text = visible_text(html)
        assert acc["email"] in text and "Çıkış" in text, path


@pytest.mark.parametrize("method, path, current", [
    ("get", "/", ("Ana Sayfa", "/")),
    ("get", "/requests", ("Talepler", "/requests")),
    ("get", "/requests?sonuc=onaylandi&talep=1", ("Talepler", "/requests")),
    ("post", "/requests/999/approve", ("Talepler", "/requests")),      # 404 screen
    ("post", "/requests/1/approve", ("Talepler", "/requests")),        # 400 screen
    ("get", "/new", ("Yeni Talep", "/new")),
    ("post", "/new", ("Yeni Talep", "/new")),                          # 400 screen
    ("get", "/personel/yeni", ("Yeni Personel", "/personel/yeni")),
    ("post", "/personel/yeni", ("Yeni Personel", "/personel/yeni")),   # 400 screen
])
def test_current_page_is_marked(client, as_account, method, path, current):
    """AC-3, G-4: the screen that is drawn marks its own menu item, error screens included —
    exactly one link, also for screen readers (aria-current)."""
    as_account(HR)
    html = html_of(getattr(client, method)(path))
    assert current_links(html) == [current]


def test_csrf_error_screen_marks_requests(as_account, monkeypatch):
    """G-4: a refused /cikis (no token) draws the Talepler screen, so Talepler is marked."""
    as_account(HR)
    monkeypatch.setitem(leave_app.app.config, "WTF_CSRF_ENABLED", True)
    leave_app.app.testing = True
    with leave_app.app.test_client() as c:
        resp = c.post("/cikis")
    assert resp.status_code == 400
    assert current_links(html_of(resp)) == [("Talepler", "/requests")]


def test_staff_on_employee_screen_marks_nothing(client, as_account):
    """G-4: the Yeni Personel screen of an account without the link marks no item."""
    as_account(STAFF)
    resp = client.get("/personel/yeni")
    assert resp.status_code == 403 and current_links(html_of(resp)) == []


def test_mobile_menu_toggle(client):
    """AC-5 (markup part; the 360 px view is VERIFY's screenshot): viewport meta, and a toggle
    button with an accessible name that controls the menu and reports open/closed."""
    html = html_of(client.get("/"))
    assert '<meta name="viewport" content="width=device-width, initial-scale=1">' in html
    toggles = re.findall(r"<button[^>]*navbar-toggler[^>]*>", html)
    assert len(toggles) == 1
    toggle = toggles[0]
    assert 'aria-label="Menüyü aç/kapat"' in toggle and 'aria-expanded="false"' in toggle
    menu_id = re.search(r'aria-controls="([^"]+)"', toggle).group(1)
    assert f'id="{menu_id}"' in html and f'data-bs-target="#{menu_id}"' in toggle


def test_menu_without_javascript(client):
    """AC-6 (markup part; the JS-off view is VERIFY's screenshot): a stylesheet that only loads
    when JavaScript is off opens the narrow menu and hides the useless toggle."""
    html = html_of(client.get("/"))
    assert f'<noscript><link rel="stylesheet" href="{NOSCRIPT}"></noscript>' in html
    css = client.get(NOSCRIPT).get_data(as_text=True)
    rule = re.search(r"@media \(max-width: 767\.98px\) \{(.*)\}", css, re.S).group(1)
    assert re.search(r"\.navbar-collapse\.collapse \{ display: block !important; \}", rule)
    assert re.search(r"\.navbar-toggler \{ display: none; \}", rule)


# --- step 4: the login screen ------------------------------------------------------------------
MSG_FAILED = "E-posta ya da şifre hatalı."
MSG_CSRF = "Form geçersiz ya da süresi dolmuş. Lütfen sayfayı yenileyip tekrar deneyin."
MSG_EXPIRED = "Oturumunuzun süresi doldu. Lütfen tekrar giriş yapın."
MSG_LOGGED_OUT = "Çıkış yapıldı."
ALERT = re.compile(r"<div class=\"alert alert-(\w+)\"( role=\"alert\")?>([^<]*)</div>")


def alerts(html):
    """Message boxes on the page as (kind, announced, text)."""
    return [(kind, bool(role), text) for kind, role, text in ALERT.findall(html)]


@pytest.fixture
def anonymous(logged_out, monkeypatch):
    monkeypatch.setitem(leave_app.app.config, "WTF_CSRF_ENABLED", True)
    leave_app.app.testing = True
    with leave_app.app.test_client() as c:
        yield c


@pytest.mark.parametrize("path", ["/giris", "/giris?durum=sure", "/giris?durum=cikis",
                                  "/giris?durum=bilinmez"])
def test_login_has_no_menu(anonymous, path):
    """AC-7: the login screen carries no navigation and no logout; its assets still load."""
    html = html_of(anonymous.get(path))
    assert "<nav" not in html and page_links(html) == [] and "cikis" not in html
    assert scripts(html) == [(BOOTSTRAP_JS, "")]
    for href in CSS:
        assert f'href="{href}"' in html
    assert not EXTERNAL.search(html)


@pytest.mark.parametrize("path", ["/giris", "/giris?durum=sure", "/giris?durum=cikis"])
def test_login_shows_app_name(anonymous, path):
    """AC-7 (review 0034 F-1): the login screen still names the application, without the menu."""
    assert "LeaveManager" in visible_text(html_of(anonymous.get(path)))


def test_error_messages_announce_info_messages_do_not(anonymous):
    """AC-8 (and AC-7 states): failed login and CSRF error are announced error boxes; expired
    and logged-out are quiet info boxes; an unknown ?durum= and the empty form show no box. The
    distinction does not rest on colour alone (role=alert)."""
    failed = anonymous.post("/giris", data={"eposta": "x@firma.com", "sifre": "yanlis parola 1"})
    assert failed.status_code == 400                               # no token yet: CSRF first
    assert alerts(html_of(failed)) == [("danger", True, MSG_CSRF)]
    token = re.search(r"name='csrf_token' value='([^']+)'", html_of(anonymous.get("/giris"))).group(1)
    failed = anonymous.post("/giris", data={"eposta": "x@firma.com", "sifre": "yanlis parola 1",
                                            "csrf_token": token})
    assert failed.status_code == 401
    assert alerts(html_of(failed)) == [("danger", True, MSG_FAILED)]
    assert alerts(html_of(anonymous.get("/giris?durum=sure"))) == [("info", False, MSG_EXPIRED)]
    assert alerts(html_of(anonymous.get("/giris?durum=cikis"))) == [("info", False, MSG_LOGGED_OUT)]
    assert alerts(html_of(anonymous.get("/giris?durum=bilinmez"))) == []
    assert alerts(html_of(anonymous.get("/giris"))) == []
