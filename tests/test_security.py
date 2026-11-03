"""Security regression guards (docs/security.md). Each test is the permanent reproduction of a
reported bug (workflows/bug-fix.md) and must never be weakened or removed.
"""
import datetime as dt
import inspect
import pathlib
import runpy

import flask
import pytest

import app as leave_app
from conftest import table_rows, visible_text

APP_PY = pathlib.Path(__file__).resolve().parent.parent / "app.py"
PAYLOAD = "<script>alert(1)</script>"
NAME = "<b>Ad</b>"
DEPARTMENT = "<i>Birim</i>"


def test_request_reason_is_shown_as_text_not_html(client):
    """Issue #2 (B-1, stored XSS): a reason containing HTML is displayed as the literal text the
    user typed and never reaches the page as markup."""
    resp = client.post("/new", data={
        "employee_id": "2", "start": "2026-11-16", "end": "2026-11-16", "reason": PAYLOAD,
    })
    assert resp.status_code == 302

    html = client.get("/requests").get_data(as_text=True)
    assert PAYLOAD not in html
    assert table_rows(html)[-1] == [
        "Mehmet Demir", "2026-11-16", "2026-11-16", "1", PAYLOAD, "Beklemede",
    ]


@pytest.mark.parametrize("path", ["/", "/requests", "/new"])
def test_employee_text_is_shown_as_text_not_html_on_every_screen(client, path):
    """Issue #2 (B-1), root cause: every text value placed into page HTML is escaped — employee
    name and department too, on every screen that shows them."""
    leave_app.storage.add_employee(
        {"id": 6, "name": NAME, "department": DEPARTMENT, "hire_date": dt.date(2020, 1, 6)})
    leave_app.storage.add_request(
        {"id": 9, "employee_id": 6, "start": dt.date(2026, 11, 16), "end": dt.date(2026, 11, 16),
         "reason": "x", "status": "Beklemede"})

    html = client.get(path).get_data(as_text=True)
    assert NAME not in html
    assert NAME in visible_text(html)
    if path == "/":
        assert DEPARTMENT not in html
        assert [NAME, DEPARTMENT, "20", "0", "20"] in table_rows(html)


def test_running_app_py_does_not_force_debug_mode(monkeypatch):
    """Issue #3 (B-2): `python app.py` must not switch the Werkzeug debugger on by itself;
    debug is only ever enabled locally through the environment (docs/security.md)."""
    run_signature = inspect.signature(flask.Flask.run)
    calls = []

    def fake_run(self, *args, **kwargs):
        # bind to the real signature so positional and keyword arguments are judged alike
        calls.append((self, run_signature.bind(self, *args, **kwargs).arguments))

    monkeypatch.setattr(flask.Flask, "run", fake_run)
    monkeypatch.delenv("FLASK_DEBUG", raising=False)

    runpy.run_path(str(APP_PY), run_name="__main__")

    assert len(calls) == 1
    flask_app, arguments = calls[0]
    assert not arguments.get("debug")
    assert not arguments.get("options", {}).get("use_debugger")
    assert not flask_app.debug
