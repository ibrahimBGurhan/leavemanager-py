"""Yeni Talep error screens keep the entered values — spec 0015 (#31).

On every domain/server error and on malformed input the form comes back with the employee
selected and the dates and reason filled in (K-1, K-3); only validated values are echoed, the
reason escaped (K-5). A CSRF failure echoes nothing (K-2). Today = 2026-10-23 (conftest).
"""
from html.parser import HTMLParser

import pytest

import app as leave_app
from conftest import visible_text

MSG_CSRF = "Form geçersiz ya da süresi dolmuş. Lütfen sayfayı yenileyip tekrar deneyin."


class FormState(HTMLParser):
    """What a browser would show in the Yeni Talep form: selected option and input values,
    plus every start tag with its attribute names (to detect injected elements/attributes)."""

    def __init__(self):
        super().__init__()
        self.options = []          # (value, selected)
        self.inputs = {}           # name -> value
        self.tags = []             # (tag, sorted attribute names)

    def handle_starttag(self, tag, attrs):
        names = sorted(a for a, _ in attrs)
        self.tags.append((tag, names))
        d = dict(attrs)
        if tag == "option":
            self.options.append((d.get("value"), "selected" in d))
        elif tag == "input" and d.get("name"):
            self.inputs[d["name"]] = d.get("value", "")


def form_state(resp):
    parser = FormState()
    parser.feed(resp.get_data(as_text=True))
    return parser


def selected(state):
    return [value for value, is_selected in state.options if is_selected]


def post(client, **fields):
    return client.post("/new", data=fields)


def assert_kept(state, employee, start, end, reason):
    assert selected(state) == ([employee] if employee else [])
    assert state.inputs["start"] == start
    assert state.inputs["end"] == end
    assert state.inputs["reason"] == reason


# --- CB-1 -----------------------------------------------------------------------------------

def test_balance_error_keeps_values(client):
    resp = post(client, employee_id="3", start="2026-12-01", end="2026-12-18", reason="Aile")
    assert resp.status_code == 400
    html = resp.get_data(as_text=True)
    message = "Kalan izin bakiyeniz yetersiz (kalan 14 gün, bekleyen 1 gün, talep 14 gün)."
    assert message in visible_text(html)
    assert html.index(message) < html.index("<form")
    assert_kept(form_state(resp), "3", "2026-12-01", "2026-12-18", "Aile")
    assert len(leave_app.storage.requests()) == 8


# --- CB-2 -----------------------------------------------------------------------------------

@pytest.mark.parametrize("start, end, status", [
    ("2026-11-18", "2026-11-16", 400),   # ters tarih
    ("2026-11-14", "2026-11-15", 400),   # iş günü yok
], ids=["reversed", "no-working-days"])
def test_other_errors_keep_values(client, start, end, status):
    resp = post(client, employee_id="2", start=start, end=end, reason="Tatil")
    assert resp.status_code == status
    assert_kept(form_state(resp), "2", start, end, "Tatil")


def test_unexpected_error_keeps_values(client, monkeypatch):
    def broken(record):
        raise RuntimeError("gizli ayrinti")
    monkeypatch.setattr(leave_app.storage, "add_request", broken)
    resp = post(client, employee_id="2", start="2026-11-16", end="2026-11-16", reason="Tatil")
    assert resp.status_code == 500
    assert "gizli ayrinti" not in resp.get_data(as_text=True)
    assert_kept(form_state(resp), "2", "2026-11-16", "2026-11-16", "Tatil")


# --- CB-3 -----------------------------------------------------------------------------------

@pytest.mark.parametrize("fields, expected", [
    ({"employee_id": "2", "start": "2026-13-01", "end": "2026-11-18", "reason": "x"},
     ("2", "", "2026-11-18", "x")),
    ({"employee_id": "abc", "start": "2026-11-16", "end": "2026-11-18", "reason": "x"},
     (None, "2026-11-16", "2026-11-18", "x")),
    ({"start": "2026-11-16", "end": "2026-11-18", "reason": "x"},
     (None, "2026-11-16", "2026-11-18", "x")),
    ({"employee_id": "2", "start": "16.11.2026", "end": "<b>", "reason": "x"},
     ("2", "", "", "x")),
    ({"employee_id": "2", "start": "2026-13-01", "end": "2026-11-18", "reason": "  Aile  "},
     ("2", "", "2026-11-18", "  Aile  ")),  # S-2: reason echoed as typed, spaces kept (F-1)
], ids=["bad-start", "bad-employee", "missing-employee", "raw-text-dates", "reason-spaces"])
def test_malformed_input_keeps_valid_fields(client, fields, expected):
    resp = client.post("/new", data=fields)
    assert resp.status_code == 400
    assert "Lütfen personeli ve geçerli başlangıç ve bitiş tarihlerini girin." in visible_text(
        resp.get_data(as_text=True))
    assert_kept(form_state(resp), *expected)


# --- CB-4 -----------------------------------------------------------------------------------

def test_unknown_employee_selects_nothing(client):
    resp = post(client, employee_id="99", start="2026-11-16", end="2026-11-18", reason="x")
    assert resp.status_code == 400
    assert "Seçilen personel bulunamadı." in visible_text(resp.get_data(as_text=True))
    assert_kept(form_state(resp), None, "2026-11-16", "2026-11-18", "x")


# --- CB-5 -----------------------------------------------------------------------------------

@pytest.mark.parametrize("reason", ['"><script>x</script>', "' onfocus='x"],
                         ids=["double-quote", "single-quote"])
def test_reason_is_escaped(client, reason):
    """The reason comes back as the text the user typed; no new element or attribute appears."""
    baseline = form_state(post(client, employee_id="5", start="2026-11-16", end="2026-11-16",
                               reason="duz"))
    resp = post(client, employee_id="5", start="2026-11-16", end="2026-11-16", reason=reason)
    assert resp.status_code == 400  # Elif: kalan 0
    state = form_state(resp)
    assert state.inputs["reason"] == reason
    assert state.tags == baseline.tags
    assert "<script>" not in resp.get_data(as_text=True)


# --- PB-1, PB-3, PB-4 -----------------------------------------------------------------------

def test_empty_form_on_get(client):
    state = form_state(client.get("/new"))
    assert [value for value, _ in state.options] == ["1", "2", "3", "4", "5"]
    assert selected(state) == []
    assert (state.inputs["start"], state.inputs["end"], state.inputs["reason"]) == ("", "", "")


def test_csrf_error_keeps_nothing(monkeypatch):
    """K-2: a token failure echoes none of the submitted values."""
    monkeypatch.setitem(leave_app.app.config, "WTF_CSRF_ENABLED", True)
    leave_app.app.testing = True
    with leave_app.app.test_client() as c:
        resp = c.post("/new", data={"employee_id": "3", "start": "2026-12-01",
                                    "end": "2026-12-18", "reason": "sahte-form"})
    assert resp.status_code == 400
    assert MSG_CSRF in visible_text(resp.get_data(as_text=True))
    state = form_state(resp)
    assert selected(state) == []
    assert (state.inputs["start"], state.inputs["end"], state.inputs["reason"]) == ("", "", "")
    assert "sahte-form" not in resp.get_data(as_text=True)
    assert len(leave_app.storage.requests()) == 8


def test_success_redirects_and_next_form_is_empty(client):
    resp = post(client, employee_id="2", start="2026-11-16", end="2026-11-18", reason="Tatil")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/requests")
    assert len(leave_app.storage.requests()) == 9
    state = form_state(client.get("/new"))
    assert selected(state) == []
    assert (state.inputs["start"], state.inputs["end"], state.inputs["reason"]) == ("", "", "")
