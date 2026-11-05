"""Shared fixtures for the baseline (characterization) tests — spec 0001.

- Tests touch app.py only through its seams (spec 0005): app.clock, app.storage, app.svc and
  app.app. The layer refactor keeps these names at the composition root.
- "Today" is frozen at 2026-10-23 through app.clock (docs/conventions.md, Data rules).
- Every test starts from the app's opening data (docs/testing.md, Resource hygiene rule 5).
- HTML helpers return what the user sees, so tests assert values, not markup (spec 0001, R-5).
"""
import datetime as _dt
import os
from html.parser import HTMLParser

import pytest

# The app configures logging on import (spec 0009); LOG_LEVEL from the developer's shell must not
# reach the process under test, or caplog stops seeing records (0009 review F-1).
os.environ.pop("LOG_LEVEL", None)

import app as leave_app  # noqa: E402

TODAY = _dt.date(2026, 10, 23)


@pytest.fixture(autouse=True)
def frozen_today(monkeypatch):
    monkeypatch.setattr(leave_app.clock, "today", lambda: TODAY)


@pytest.fixture(autouse=True)
def opening_data():
    leave_app.storage.reset()


@pytest.fixture
def svc():
    return leave_app.svc


@pytest.fixture
def client():
    leave_app.app.testing = True
    leave_app.app.config["WTF_CSRF_ENABLED"] = False  # spec 0011 D3; CSRF: tests/test_csrf.py
    with leave_app.app.test_client() as c:
        yield c


def end_after_workdays(start, n):
    """End date of a range starting at `start` that holds n weekdays (Mon-Fri), spec 0014. Skips
    only Saturday/Sunday and does not call production code: pick dates without public holidays
    (e.g. Nov-Dec 2026). Holiday cases are written with explicit dates in test_workdays.py."""
    day, left = start, n
    while True:
        if day.weekday() < 5:
            left -= 1
            if left == 0:
                return day
        day += _dt.timedelta(days=1)


def pytest_collection_modifyitems(config, items):
    # ANEW_REVERSE_ORDER=1 runs the suite backwards: reproducible proof of order independence (AC-11).
    if os.environ.get("ANEW_REVERSE_ORDER") == "1":
        items.reverse()


def _normalize(text):
    return " ".join(text.split())


class _TextAndTables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.chunks = []
        self.rows = []
        self._row = None
        self._cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None:
            self._row.append(_normalize("".join(self._cell)))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None

    def handle_data(self, data):
        self.chunks.append(data)
        if self._cell is not None:
            self._cell.append(data)


def visible_text(html):
    """All text of the page with tags removed and whitespace collapsed."""
    p = _TextAndTables()
    p.feed(html)
    return _normalize(" ".join(p.chunks))


def table_rows(html):
    """Every <tr> as a list of its cell texts (header rows included)."""
    p = _TextAndTables()
    p.feed(html)
    return p.rows


def status_cell_html(html, marker):
    """Raw HTML of the last cell (Durum) in the one table row whose text contains marker."""
    rows = [row for row in html.split("<tr>") if marker in row]
    assert len(rows) == 1, f"expected one row with {marker!r}, got {len(rows)}"
    return rows[0].split("<td>")[-1].split("</td>")[0]
