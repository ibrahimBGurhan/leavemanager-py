"""Shared fixtures for the baseline (characterization) tests — spec 0001.

- "Today" is frozen at 2026-10-23 without touching app.py (docs/conventions.md, Data rules).
- Every test starts from the app's opening data (docs/testing.md, Resource hygiene rule 5).
- HTML helpers return what the user sees, so tests assert values, not markup (spec 0001, R-5).
"""
import datetime as _dt
import os
from html.parser import HTMLParser

import pytest

import app as leave_app

TODAY = _dt.date(2026, 10, 23)


class FrozenDatetime(_dt.datetime):
    """datetime whose now() is TODAY; strptime and the rest behave as usual."""

    @classmethod
    def now(cls, tz=None):
        return cls(TODAY.year, TODAY.month, TODAY.day, 12, 0, tzinfo=tz)


@pytest.fixture(autouse=True)
def frozen_today(monkeypatch):
    monkeypatch.setattr(leave_app, "datetime", FrozenDatetime)


@pytest.fixture(autouse=True)
def opening_data():
    leave_app.seed()


@pytest.fixture
def svc():
    return leave_app.LeaveService()


@pytest.fixture
def client():
    leave_app.app.testing = True
    with leave_app.app.test_client() as c:
        yield c


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
