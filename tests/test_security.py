"""Security regression guards (docs/security.md). Each test is the permanent reproduction of a
reported bug (workflows/bug-fix.md) and must never be weakened or removed.
"""
import pathlib
import runpy

import flask

from conftest import table_rows

APP_PY = pathlib.Path(__file__).resolve().parent.parent / "app.py"
PAYLOAD = "<script>alert(1)</script>"


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


def test_running_app_py_does_not_force_debug_mode(monkeypatch):
    """Issue #3 (B-2): `python app.py` must not switch the Werkzeug debugger on by itself;
    debug is only ever enabled locally through the environment (docs/security.md)."""
    calls = []
    monkeypatch.setattr(flask.Flask, "run", lambda self, *a, **kw: calls.append(kw))
    monkeypatch.delenv("FLASK_DEBUG", raising=False)

    runpy.run_path(str(APP_PY), run_name="__main__")

    assert len(calls) == 1
    assert calls[0].get("debug") is not True
