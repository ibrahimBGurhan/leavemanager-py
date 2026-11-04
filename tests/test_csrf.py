"""Every state-changing form carries a CSRF token; SECRET_KEY comes from the environment — spec 0011.

Reproduction for #25 (written before the fix): with protection on, a POST without a valid token
must change nothing and answer 400 with a Turkish message. These tests turn CSRF on themselves
(csrf_client); the shared `client` fixture runs with it off (spec 0011, D3).
"""
import logging
import pathlib
import re
import time

import pytest

import app as leave_app
from conftest import visible_text

ROOT = pathlib.Path(__file__).resolve().parent.parent
MSG_CSRF = "Form geçersiz ya da süresi dolmuş. Lütfen sayfayı yenileyip tekrar deneyin."
TOKEN = re.compile(r"""name=['"]csrf_token['"] value=['"]([^'"]+)['"]""")
NEW_FORM = {"employee_id": "2", "start": "2026-11-16", "end": "2026-11-16", "reason": "x"}

# (name, page that holds the form, POST path, form data, marker the message must precede)
ACTIONS = [
    ("new", "/new", "/new", NEW_FORM, "<form"),
    ("approve", "/requests", "/requests/2/approve", {}, "<table"),
    ("reject", "/requests", "/requests/4/reject", {}, "<table"),
]
ACTION_IDS = [a[0] for a in ACTIONS]


@pytest.fixture
def csrf_client(monkeypatch):
    monkeypatch.setitem(leave_app.app.config, "WTF_CSRF_ENABLED", True)
    leave_app.app.testing = True
    with leave_app.app.test_client() as c:
        yield c


def records():
    return [(r["id"], r["status"]) for r in leave_app.storage.requests()]


def token_from(html):
    m = TOKEN.search(html)
    assert m, "no csrf_token field on the page"
    return m.group(1)


def assert_rejected(resp, marker, before):
    assert resp.status_code == 400
    html = resp.get_data(as_text=True)
    text = visible_text(html)
    assert MSG_CSRF in text
    assert html.index(MSG_CSRF) < html.index(marker)
    for leak in ("Bad Request", "CSRF", "csrf_token", "Traceback"):
        assert leak not in text
    assert records() == before


# --- reproduction (#25) + CB-2 --------------------------------------------------------------

@pytest.mark.parametrize("name, page, path, data, marker", ACTIONS, ids=ACTION_IDS)
def test_post_without_token_is_rejected(csrf_client, caplog, name, page, path, data, marker):
    before = records()
    with caplog.at_level(logging.INFO):
        resp = csrf_client.post(path, data=data)
    assert_rejected(resp, marker, before)
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1 and warnings[0].exc_info is None


@pytest.mark.parametrize("kind", ["bozuk", "baska-oturum"])
@pytest.mark.parametrize("name, page, path, data, marker", ACTIONS, ids=ACTION_IDS)  # F-2: all 3
def test_bad_or_foreign_token_is_rejected(csrf_client, kind, name, page, path, data, marker):
    if kind == "bozuk":
        csrf_client.get(page)
        token = "x" + token_from(csrf_client.get(page).get_data(as_text=True))[1:]
    else:
        with leave_app.app.test_client() as other:
            token = token_from(other.get(page).get_data(as_text=True))
        csrf_client.get(page)
    before = records()
    resp = csrf_client.post(path, data={**data, "csrf_token": token})
    assert_rejected(resp, marker, before)


def test_csrf_check_comes_before_request_lookup(csrf_client):
    """Plan 0011 Risk 3: a token-less POST to an unknown number is a CSRF failure, not a 404."""
    before = records()
    assert_rejected(csrf_client.post("/requests/abc/approve"), "<table", before)


# --- CB-1 -----------------------------------------------------------------------------------

def test_forms_carry_a_token(csrf_client):
    assert token_from(csrf_client.get("/new").get_data(as_text=True))
    html = csrf_client.get("/requests").get_data(as_text=True)
    pending = [r for r in leave_app.storage.requests() if r["status"] == "Beklemede"]
    forms = html.split("<form")[1:]
    assert len(forms) == 2 * len(pending) == 8
    assert all(TOKEN.search(f.split("</form>")[0]) for f in forms)


def test_every_post_form_on_every_page_carries_a_token(csrf_client):
    """Review F-1: a POST form added later without csrf_field() goes red here, not in production.
    Visits every GET page the app routes (no URL arguments) and checks each POST form."""
    pages = sorted(r.rule for r in leave_app.app.url_map.iter_rules()
                   if "GET" in r.methods and not r.arguments and r.endpoint != "static")
    assert {"/", "/requests", "/new"} <= set(pages)
    post_forms = []
    for page in pages:
        html = csrf_client.get(page).get_data(as_text=True)
        for block in html.split("<form")[1:]:
            opening, body = block.split(">", 1)
            if re.search(r"""method\s*=\s*['"]?post""", opening, re.IGNORECASE):  # F-6
                post_forms.append((page, body.split("</form>")[0]))
    assert len(post_forms) >= 1 + 8  # en az: Yeni Talep + 4 bekleyen talep x (Onayla, Reddet)
    missing = [page for page, body in post_forms if not TOKEN.search(body)]
    assert missing == []


@pytest.mark.parametrize("name, page, path, data, marker", ACTIONS, ids=ACTION_IDS)
def test_valid_token_flow_works(csrf_client, name, page, path, data, marker):
    token = token_from(csrf_client.get(page).get_data(as_text=True))
    resp = csrf_client.post(path, data={**data, "csrf_token": token})
    assert resp.status_code == 302
    if name == "new":
        assert records()[-1] == (9, "Beklemede")
    elif name == "approve":
        assert dict(records())[2] == "Onaylandi"
    else:
        assert dict(records())[4] == "Reddedildi"


# --- CB-3 -----------------------------------------------------------------------------------

def secret_warnings(caplog):
    return [r for r in caplog.records if r.name == "app.secrets" and r.levelno == logging.WARNING]


def test_secret_key_from_environment(caplog):
    with caplog.at_level(logging.INFO):
        assert leave_app.load_secret_key({"SECRET_KEY": "ortamdan-gelen"}) == "ortamdan-gelen"
    assert secret_warnings(caplog) == []


@pytest.mark.parametrize("environ", [{}, {"SECRET_KEY": ""}, {"SECRET_KEY": "   "}],
                         ids=["unset", "empty", "blank"])
def test_missing_secret_key_warns_once_without_value(caplog, environ):
    with caplog.at_level(logging.INFO):
        key = leave_app.load_secret_key(environ)
    assert re.fullmatch(r"[0-9a-f]{64}", key)
    warnings = secret_warnings(caplog)
    assert len(warnings) == 1
    assert key not in warnings[0].getMessage()
    assert "SECRET_KEY" in warnings[0].getMessage()


def test_token_has_no_time_limit(csrf_client, monkeypatch):
    token = token_from(csrf_client.get("/new").get_data(as_text=True))
    now = time.time()
    monkeypatch.setattr(time, "time", lambda: now + 2 * 3600)
    assert csrf_client.post("/new", data={**NEW_FORM, "csrf_token": token}).status_code == 302


def test_env_example_has_placeholder():
    lines = (ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
    values = [line.split("=", 1)[1] for line in lines if line.startswith("SECRET_KEY=")]
    assert len(values) == 1
    assert not re.fullmatch(r"[0-9a-fA-F]{32,}", values[0].strip())


# --- PB-1, PB-4 -----------------------------------------------------------------------------

@pytest.mark.parametrize("path", ["/", "/requests", "/new"])
def test_get_needs_no_token(csrf_client, path):
    assert csrf_client.get(path).status_code == 200


def test_session_cookie_flags(csrf_client):
    cookie = csrf_client.get("/new").headers.get("Set-Cookie", "")
    assert cookie.startswith("session=")
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie
    assert "Secure" not in cookie


def test_secret_never_in_logs(csrf_client, caplog, monkeypatch):
    """The signing key and the form token appear in no log record: neither while the key is read
    from the environment nor on a failed and a successful POST of the running app. Review F-3:
    the running app gets a known key; review F-5: the start-up path is checked with the same value
    (load_secret_key logs nothing today — the assert guards against it starting to)."""
    monkeypatch.setitem(leave_app.app.config, "SECRET_KEY", "s3cr3t-deger-0011")
    with caplog.at_level(logging.DEBUG):
        assert leave_app.load_secret_key({"SECRET_KEY": "s3cr3t-deger-0011"}) == "s3cr3t-deger-0011"
        token = token_from(csrf_client.get("/new").get_data(as_text=True))
        csrf_client.post("/new", data=NEW_FORM)
        csrf_client.post("/new", data={**NEW_FORM, "csrf_token": token})
    assert any(r.name == "web.routes" for r in caplog.records)  # the failed POST was logged
    assert "s3cr3t-deger-0011" not in caplog.text
    assert token not in caplog.text
