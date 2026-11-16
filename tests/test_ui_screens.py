"""Screen bodies on Bootstrap — spec 0035 (ADR-0003, plan 0035).

What the four screens show and offer, read from the page the way a browser offers it: boxes,
headings, tables, labelled fields, badges and message boxes. Class names matter only where they
carry meaning the user sees (badge kind, message kind, the scrollable table box).
"""
import ast
import datetime as dt
import pathlib
import re

import pytest

import app as leave_app
import web.routes as routes
from conftest import (BOOTSTRAP_JS, badge_kind, controls, form_bs_attrs, headings, message_boxes,
                      scripts, status_cell_html, table_rows, table_wrapped, visible_text)
from domain.auth import LoginService

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCREENS = ["/", "/requests", "/new", "/personel/yeni"]


def account(role, employee_id, email):
    return {"email": email, "password_hash": "", "role": role, "employee_id": employee_id,
            "active": True, "failed_attempts": 0, "locked_until": None}


HR = account("IK", None, "ik@firma.com")
MANAGER = account("Yonetici", 4, "mudur@firma.com")
STAFF = account("Personel", 1, "ayse@firma.com")
UNLINKED = account("Personel", None, "kayitsiz@firma.com")


@pytest.fixture
def as_account(monkeypatch):
    def use(acc):
        monkeypatch.setattr(LoginService, "session_account", lambda self, email, login_at: acc)
    return use


@pytest.fixture
def csrf_client(monkeypatch):
    monkeypatch.setitem(leave_app.app.config, "WTF_CSRF_ENABLED", True)
    leave_app.app.testing = True
    with leave_app.app.test_client() as c:
        yield c


def html_of(resp):
    return resp.get_data(as_text=True)


# --- AC-1 ---------------------------------------------------------------------------------------
def test_dashboard_counters_in_boxes(client):
    """AC-1: three counters, each in its own box, side by side on wide screens and stacked on
    narrow ones; the balance table follows under its heading."""
    html = html_of(client.get("/"))
    boxes = re.findall(r'<div class="card-body">(.*?)</div>', html)
    assert [visible_text(b) for b in boxes] == ["Bekleyen: 4", "Onaylanan: 1", "Reddedilen: 3"]
    assert '<div class="row row-cols-1 row-cols-sm-3 g-3 mb-4">' in html
    assert headings(html) == ["Personel Bakiyeleri"]
    assert table_rows(html)[0] == ["Ad", "Birim", "Hak", "Kullanılan", "Kalan", "Bekleyen"]


# --- AC-2 ---------------------------------------------------------------------------------------
def test_requests_title_and_columns(client):
    """AC-2: one heading, the six columns, one row per request."""
    html = html_of(client.get("/requests"))
    assert headings(html) == ["İzin Talepleri"]
    rows = table_rows(html)
    assert rows[0] == ["Personel", "Başlangıç", "Bitiş", "Gün", "Neden", "Durum"]
    assert len(rows) - 1 == len(leave_app.storage.requests())


# --- AC-3 ---------------------------------------------------------------------------------------
KINDS = {"success", "warning", "danger", "secondary"}
CSS_COLORS = {"green", "orange", "red", "gray", "grey", "#999"}


def test_status_kind_names_no_color(client):
    """AC-3: every badge on the screen has a kind and the status text; the code that picks the
    kind names no CSS color, and no template sets a color."""
    html = html_of(client.get("/requests"))
    for r in leave_app.storage.requests():
        cell = status_cell_html(html, r["reason"])
        assert badge_kind(cell) == routes.status_kind(r["status"]) and r["status"] in cell
    assert {routes.status_kind(s) for s in ("Onaylandi", "Beklemede", "Reddedildi", "x")} == KINDS
    source = (ROOT / "web" / "routes.py").read_text(encoding="utf-8")
    literals = {n.value.lower() for n in ast.walk(ast.parse(source))
                if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    assert not literals & CSS_COLORS
    for t in (ROOT / "web" / "templates").glob("*.html"):
        assert "color" not in t.read_text(encoding="utf-8").lower(), t.name


# --- AC-4 ---------------------------------------------------------------------------------------
FORM = re.compile(r"<form method='post' action='/requests/(\d+)/(approve|reject)'[^>]*>(.*?)</form>",
                  re.S)


def test_decision_buttons_name_the_request(csrf_client):
    """AC-4: each pending request has two separate POST forms with a token; the visible label is
    Onayla / Reddet and the name a screen reader reads holds the person and both dates."""
    html = html_of(csrf_client.get("/requests"))
    names = {e["id"]: e["name"] for e in leave_app.storage.employees()}
    pending = {r["id"]: r for r in leave_app.storage.requests() if r["status"] == "Beklemede"}
    forms = FORM.findall(html)
    assert sorted((int(i), a) for i, a, _ in forms) == sorted(
        (i, a) for i in pending for a in ("approve", "reject"))
    for rid, action, body in forms:
        r = pending[int(rid)]
        assert re.search(r"name='csrf_token' value='[^']+'", body)
        verb, label = ("onayla", "Onayla") if action == "approve" else ("reddet", "Reddet")
        [button] = [c for c in controls(body) if c.get("type") == "submit"]
        assert button["value"] == label
        assert button["aria-label"] == (
            f"{names[r['employee_id']]}, {r['start']} – {r['end']} talebini {verb}")


def test_decision_still_works(client):
    """AC-4: pressing the button does what it did: approved, redirected with the success box."""
    resp = client.post("/requests/2/approve")
    assert resp.status_code == 302 and "sonuc=onaylandi" in resp.headers["Location"]
    assert [r["status"] for r in leave_app.storage.requests() if r["id"] == 2] == ["Onaylandi"]


# --- AC-5 ---------------------------------------------------------------------------------------
DANGER, SUCCESS = ("danger", "alert"), ("success", "status")


def boom(*_args, **_kwargs):
    raise RuntimeError("bozuk")


@pytest.mark.parametrize("acc, method, path, data, patch, expected", [
    (HR, "get", "/requests?sonuc=onaylandi&talep=1", None, None, [(*SUCCESS, "Talep #1 onaylandı.")]),
    (HR, "get", "/requests?sonuc=reddedildi&talep=8", None, None, [(*SUCCESS, "Talep #8 reddedildi.")]),
    (HR, "get", "/requests?sonuc=onaylandi&talep=2", None, None, []),
    (HR, "post", "/requests/999/approve", {}, None, [(*DANGER, routes.MSG_REQUEST_NOT_FOUND)]),
    (HR, "post", "/requests/1/approve", {}, None, [(*DANGER, routes.MSG_ALREADY_DECIDED)]),
    (HR, "post", "/requests/2/approve", {}, "set_request_status", [(*DANGER, routes.MSG_ACTION_UNEXPECTED)]),
    (STAFF, "post", "/requests/2/approve", {}, None, [(*DANGER, routes.MSG_FORBIDDEN)]),
    (HR, "post", "/new", {}, None, [(*DANGER, routes.MSG_INVALID_INPUT)]),
    (HR, "post", "/new", {"employee_id": "2", "start": "2026-11-20", "end": "2026-11-16", "reason": "x"},
     None, [(*DANGER, routes.MSG_INVALID_DATE_RANGE)]),
    (HR, "post", "/new", {"employee_id": "999", "start": "2026-11-16", "end": "2026-11-16", "reason": "x"},
     None, [(*DANGER, routes.MSG_EMPLOYEE_NOT_FOUND)]),
    (HR, "post", "/new", {"employee_id": "2", "start": "2026-11-21", "end": "2026-11-22", "reason": "x"},
     None, [(*DANGER, routes.MSG_NO_WORKING_DAYS)]),
    (HR, "post", "/new", {"employee_id": "2", "start": "2026-11-16", "end": "2026-11-16", "reason": "x"},
     "add_request", [(*DANGER, routes.MSG_UNEXPECTED)]),
    (HR, "post", "/new", {"employee_id": "5", "start": "2026-11-16", "end": "2026-11-16", "reason": "x"},
     None, [(*DANGER, routes.MSG_INSUFFICIENT_BALANCE % (0, 0, 1))]),    # review 0035 F-1
    (STAFF, "post", "/new", {"employee_id": "2", "start": "2026-11-16", "end": "2026-11-16", "reason": "x"},
     None, [(*DANGER, routes.MSG_FORBIDDEN)]),
    (UNLINKED, "get", "/new", None, None, [("info", "", routes.MSG_NO_EMPLOYEE)]),
    (HR, "get", "/personel/yeni?eklendi=1", None, None, [(*SUCCESS, "Personel #1 eklendi: Ayse Yilmaz (IT).")]),
    (HR, "get", "/personel/yeni?eklendi=777", None, None, []),
    (HR, "post", "/personel/yeni", {"name": "", "department": "IT", "hire_date": "2020-01-01"}, None, "danger"),
    (HR, "post", "/personel/yeni", {"name": "X", "department": "", "hire_date": "2020-01-01"}, None, "danger"),
    (HR, "post", "/personel/yeni", {"name": "X", "department": "IT", "hire_date": "2020-13-45"}, None, "danger"),
    (HR, "post", "/personel/yeni", {"name": "X", "department": "IT", "hire_date": ""}, None, "danger"),
    (HR, "post", "/personel/yeni", {"name": "X", "department": "IT", "hire_date": "1949-12-31"}, None, "danger"),
    (HR, "post", "/personel/yeni", {"name": "X", "department": "IT", "hire_date": "2020-01-01"},
     "add_employee", [(*DANGER, routes.MSG_EMPLOYEE_UNEXPECTED)]),
    (STAFF, "get", "/personel/yeni", None, None, [(*DANGER, routes.MSG_FORBIDDEN)]),
    (HR, "get", "/requests", None, None, []),
    (HR, "get", "/new", None, None, []),
])
def test_message_boxes(client, as_account, monkeypatch, acc, method, path, data, patch, expected):
    """AC-5: success in a green box announced quietly, every error in a red box announced at
    once, the unlinked-account notice in an info box; no box where there is no message. The
    texts are today's."""
    as_account(acc)
    if patch:
        monkeypatch.setattr(leave_app.storage, patch, boom)
    resp = client.post(path, data=data) if method == "post" else client.get(path)
    boxes = message_boxes(html_of(resp))
    if expected == "danger":    # a validation message whose text other tests own
        assert len(boxes) == 1 and boxes[0][:2] == DANGER
    else:
        assert boxes == expected


def test_approve_insufficient_message_box(client):
    """AC-5 (review 0035 F-1): approving a request the balance no longer covers shows the
    refusal in a red, announced box."""
    request_id = leave_app.storage.next_request_id()
    leave_app.storage.add_request({    # Elif: Kalan 0; straight into storage (seam)
        "id": request_id, "employee_id": 5, "start": dt.date(2026, 11, 16),
        "end": dt.date(2026, 11, 16), "reason": "x", "status": "Beklemede"})
    resp = client.post(f"/requests/{request_id}/approve")
    assert resp.status_code == 400
    assert message_boxes(html_of(resp)) == [(*DANGER, routes.MSG_APPROVE_INSUFFICIENT % (0, 1))]


@pytest.mark.parametrize("path, data", [
    ("/new", {"employee_id": "2", "start": "2026-11-16", "end": "2026-11-16", "reason": "x"}),
    ("/requests/2/approve", {}),
    ("/personel/yeni", {"name": "X", "department": "IT", "hire_date": "2020-01-01"}),
])
def test_csrf_message_box(csrf_client, path, data):
    """AC-5: a refused form (no token) shows the CSRF message in a red, announced box."""
    resp = csrf_client.post(path, data=data)
    assert resp.status_code == 400
    assert message_boxes(html_of(resp)) == [(*DANGER, routes.MSG_CSRF)]


# --- AC-6 ---------------------------------------------------------------------------------------
def test_new_request_fields_are_labelled(client, as_account):
    """AC-6: every field has a visible label bound to it; HR picks from a list, an employee sees
    their own name as plain text (no field to change it)."""
    as_account(HR)
    fields = {c["name"]: c.get("label") for c in controls(html_of(client.get("/new")))
              if c.get("name") and c.get("type") not in ("hidden", "submit")}
    assert fields == {"employee_id": "Personel", "start": "Başlangıç", "end": "Bitiş",
                      "reason": "Neden"}
    as_account(STAFF)
    html = html_of(client.get("/new"))
    fields = {c["name"]: c.get("label") for c in controls(html)
              if c.get("name") and c.get("type") not in ("hidden", "submit")}
    assert fields == {"start": "Başlangıç", "end": "Bitiş", "reason": "Neden"}
    assert "Personel Ayse Yilmaz" in visible_text(html)


def test_unlinked_account_gets_no_form(client, as_account):
    """AC-6: an account with no employee record sees the notice, not a form."""
    as_account(UNLINKED)
    html = html_of(client.get("/new"))
    assert "<form method=\"post\">" not in html and [c for c in controls(html)
                                                    if c.get("name") == "start"] == []


# --- AC-7 ---------------------------------------------------------------------------------------
def test_new_employee_submit_is_primary(client):
    """AC-7: the form's Kaydet is the primary button (and on Yeni Talep too, AC-6)."""
    for path in ("/new", "/personel/yeni"):
        kaydet = [c for c in controls(html_of(client.get(path)))
                  if c.get("type") == "submit" and c.get("value") == "Kaydet"]
        assert len(kaydet) == 1 and "btn-primary" in kaydet[0]["class"].split(), path


# --- AC-8 / AC-9 --------------------------------------------------------------------------------
def test_tables_scroll_in_their_own_box(client):
    """AC-8 (markup part; the 360 px measurement is VERIFY's): every table sits in a box that
    scrolls sideways, so the page itself does not."""
    for path in ("/", "/requests"):
        assert table_wrapped(html_of(client.get(path))) == [True], path


@pytest.mark.parametrize("acc", [HR, MANAGER, STAFF])
def test_screens_need_no_script(client, as_account, acc):
    """AC-9 (markup part; JS-off screenshots are VERIFY's): the only script is Bootstrap's bundle
    and no form control is bound to it — forms and decisions work without JavaScript."""
    as_account(acc)
    for path in SCREENS:
        html = html_of(client.get(path))
        assert scripts(html) == [(BOOTSTRAP_JS, "")], path
        assert form_bs_attrs(html) == [], path


# --- AC-10 / AC-11 ------------------------------------------------------------------------------
OLD = re.compile(r"\b(?:Izin|Baslangic|Bitis|Gun|Kullanilan)\b")


def test_turkish_texts(client):
    """AC-10: the corrected headings show, the old spellings are gone from all four screens."""
    texts = {p: visible_text(html_of(client.get(p))) for p in SCREENS}
    assert "Kullanılan" in texts["/"]
    assert all(w in texts["/requests"] for w in ("İzin Talepleri", "Başlangıç", "Bitiş", "Gün"))
    assert all(w in texts["/new"] for w in ("Başlangıç", "Bitiş"))
    for path, text in texts.items():
        assert not OLD.search(text), (path, OLD.search(text))


def test_app_css_has_no_interim_rules():
    """AC-11: the spec 0034 stop-gap rules (old table borders, .kutu) are gone."""
    css = (ROOT / "web" / "static" / "app.css").read_text(encoding="utf-8")
    assert ".kutu" not in css and "main table" not in css and "main td" not in css


def test_dates_render_as_in_table(client):
    """G-2: the screen reader name uses the dates exactly as the table shows them."""
    html = html_of(client.get("/requests"))
    row = [r for r in table_rows(html) if r[0] == "Mehmet Demir" and r[4] == "Aile ziyareti"][0]
    assert row[1] == str(dt.date(2026, 11, 2)) and f"{row[1]} – {row[2]}" in html
