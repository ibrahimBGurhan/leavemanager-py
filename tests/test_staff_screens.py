"""Staff screens that were only observed so far — spec 0024 (issue #43, 0020 G-4).

Yeni Talep for a Personel account has the date fields, the reason field and "Kaydet" in one form,
in keyboard order (0020 Accessibility: tarih -> neden -> Kaydet), and a Personel linked to an
employee without requests sees an empty Talepler. The logged-in account is chosen per test by
`as_account` (the gate's session check is swapped, as in tests/test_authorization.py; the real
login path is pinned in tests/test_login_authorization_e2e.py).

Opening data (storage/demo.py): A = Ayse Yilmaz (1, IT). Every demo employee has requests, so the
tests add C, an employee without any.
"""
import datetime as dt
import re
from html.parser import HTMLParser

import pytest

import app as leave_app
from conftest import table_rows, visible_text
from domain.auth import LoginService

A, A_NAME = 1, "Ayse Yilmaz"
C_NAME, C_DEPT = "Talepsiz Kisi", "Satis"
OTHERS = ("Mehmet Demir", "Zeynep Kaya", "Ahmet Celik", "Elif Sahin", A_NAME)
HEADER = ["Personel", "Baslangic", "Bitis", "Gun", "Neden", "Durum"]


def account(role, employee_id, email):
    return {"email": email, "password_hash": "", "role": role, "employee_id": employee_id,
            "active": True, "failed_attempts": 0, "locked_until": None}


STAFF = account("Personel", A, "ayse@firma.com")
HR = account("IK", None, "ik@firma.com")


@pytest.fixture
def as_account(monkeypatch):
    def use(acc):
        monkeypatch.setattr(LoginService, "session_account", lambda self, email, login_at: acc)
    return use


class _Forms(HTMLParser):
    """The page's forms as a browser sees them: per form, its focusable controls in DOM order.
    The logout form (/cikis, button in the menu via form=) is not a page form."""

    def __init__(self):
        super().__init__()
        self.forms, self._current = [], None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "form":
            self._current = None if a.get("action") == "/cikis" else []
            if self._current is not None:
                self.forms.append(self._current)
        elif tag in ("input", "select", "textarea", "button") and self._current is not None:
            if a.get("type") != "hidden":
                self._current.append({"tag": tag, **a})

    def handle_endtag(self, tag):
        if tag == "form":
            self._current = None


def forms_of(html):
    p = _Forms()
    p.feed(html)
    return p.forms


def page(client, path):
    resp = client.get(path)
    assert resp.status_code == 200
    return resp.get_data(as_text=True)


def control_names(form):
    return [c.get("name") or c.get("type") for c in form]


# --- PB-1: Yeni Talep fields ---------------------------------------------------------------------

def test_staff_new_request_form_has_dates_reason_and_save(client, as_account):
    as_account(STAFF)
    html = page(client, "/new")
    forms = forms_of(html)
    assert len(forms) == 1
    fields = {c.get("name"): c for c in forms[0] if c.get("name")}
    assert set(fields) == {"start", "end", "reason"}            # no employee_id selection
    assert (fields["start"]["type"], fields["end"]["type"]) == ("date", "date")
    assert fields["reason"]["type"] == "text"
    assert [c.get("value") for c in forms[0] if c.get("type") == "submit"] == ["Kaydet"]
    assert "<select" not in html
    assert "Personel: %s" % A_NAME in visible_text(html)      # own name as plain text


def test_hr_new_request_form_keeps_its_fields(client, as_account):
    as_account(HR)
    forms = forms_of(page(client, "/new"))
    assert len(forms) == 1
    by_name = {c.get("name"): c for c in forms[0] if c.get("name")}
    assert set(by_name) == {"employee_id", "start", "end", "reason"}
    assert by_name["employee_id"]["tag"] == "select"
    assert (by_name["start"]["type"], by_name["end"]["type"]) == ("date", "date")
    assert [c.get("value") for c in forms[0] if c.get("type") == "submit"] == ["Kaydet"]


# --- PB-2: keyboard order ------------------------------------------------------------------------

@pytest.mark.parametrize("acc, order", [
    pytest.param(STAFF, ["start", "end", "reason", "submit"], id="Personel"),
    pytest.param(HR, ["employee_id", "start", "end", "reason", "submit"], id="IK"),
])
def test_new_request_keyboard_order(client, as_account, acc, order):
    """Tab follows the DOM order of the one form (no tabindex), the submit button is the form's
    last control and Enter submits it — no script involved."""
    as_account(acc)
    html = page(client, "/new")
    forms = forms_of(html)
    assert len(forms) == 1
    assert control_names(forms[0]) == order
    assert "tabindex" not in html.lower() and "<script" not in html.lower()


# --- PB-3: linked staff without requests --------------------------------------------------------

def test_linked_staff_without_requests_sees_empty_talepler(client, as_account):
    storage = leave_app.storage
    c_id = storage.next_employee_id()
    storage.add_employee({"id": c_id, "name": C_NAME, "department": C_DEPT,
                          "hire_date": dt.date(2020, 1, 6)})
    assert not [r for r in storage.requests() if r["employee_id"] == c_id]
    as_account(account("Personel", c_id, "talepsiz@firma.com"))

    listing = page(client, "/requests")
    assert table_rows(listing) == [HEADER]                     # header only, no request row
    assert "/approve" not in listing and "/reject" not in listing
    for name in OTHERS:
        assert name not in listing

    home = page(client, "/")
    text = visible_text(home)
    counts = [int(n) for n in re.findall(r"(?:Bekleyen|Onaylanan|Reddedilen): (\d+)", text)]
    assert counts == [0, 0, 0]
    assert table_rows(home)[1:] == [[C_NAME, C_DEPT, "20", "0", "20", "0"]]  # 6 years -> 20
    for name in OTHERS:
        assert name not in text
