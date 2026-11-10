"""Shared fixtures for the baseline (characterization) tests — spec 0001.

- Tests touch app.py only through its seams (spec 0005): app.clock, app.storage, app.svc and
  app.app. The layer refactor keeps these names at the composition root.
- "Today" is frozen at 2026-10-23 through app.clock (docs/conventions.md, Data rules).
- Every test starts from the app's opening data (docs/testing.md, Resource hygiene rule 5).
- HTML helpers return what the user sees, so tests assert values, not markup (spec 0001, R-5).
"""
import datetime as _dt
import os
import threading
from html.parser import HTMLParser

import pytest

# The app configures logging on import (spec 0009); LOG_LEVEL from the developer's shell must not
# reach the process under test, or caplog stops seeing records (0009 review F-1).
os.environ.pop("LOG_LEVEL", None)
os.environ["LEAVEMANAGER_STORAGE"] = "memory"  # spec 0017: no database file from the suite

import app as leave_app  # noqa: E402
from domain.auth import LoginService  # noqa: E402

TODAY = _dt.date(2026, 10, 23)


@pytest.fixture(autouse=True)
def frozen_today(monkeypatch):
    monkeypatch.setattr(leave_app.clock, "today", lambda: TODAY)


@pytest.fixture(autouse=True)
def opening_data():
    leave_app.storage.reset()


# Spec 0019 S-1: the suite's in-process clients are logged in as this account. The class method is
# swapped (not the instance): child processes that load app.py through runpy see the same class.
# Production code has no flag or environment switch for this.
TEST_ACCOUNT = {"email": "test@firma.com", "password_hash": "", "role": "IK", "employee_id": None,
                "active": True, "failed_attempts": 0, "locked_until": None}
_REAL_SESSION_ACCOUNT = LoginService.session_account


@pytest.fixture(autouse=True)
def logged_in(monkeypatch):
    monkeypatch.setattr(LoginService, "session_account", lambda self, email, login_at: TEST_ACCOUNT)


@pytest.fixture
def logged_out(monkeypatch):
    """The real session check: login tests (tests/test_login.py, tests/test_auth.py) use this."""
    monkeypatch.setattr(LoginService, "session_account", _REAL_SESSION_ACCOUNT)


@pytest.fixture
def svc():
    return leave_app.svc


@pytest.fixture
def client():
    leave_app.app.testing = True
    leave_app.app.config["WTF_CSRF_ENABLED"] = False  # spec 0011 D3; CSRF: tests/test_csrf.py
    with leave_app.app.test_client() as c:
        yield c


# --- spec 0026: concurrency tests open the race window themselves ------------------------------
# A counter's unprotected read-then-write window is a few bytecodes wide; lowering the switch
# interval does not open it (spec 0026, Observation). The hooks below make the first thread that
# reads the counter wait for a second one. Unprotected, a second thread reads the same value and
# both carry on with it: a duplicate number or a lost increment on every run. Protected, the
# second thread waits for the lock, so the first one times out once (RACE_WAIT) and goes on alone.
RACE_WAIT = 0.5  # seconds; paid once per protected test run (plan 0026 Risk 1)


class _Rendezvous:
    """One-shot meeting point of two threads; later calls pass straight through."""

    def __init__(self):
        self._barrier = threading.Barrier(2, timeout=RACE_WAIT)
        self._guard = threading.Lock()
        self._arrived = 0

    def meet(self):
        with self._guard:
            if self._arrived >= 2:
                return
            self._arrived += 1
        try:
            self._barrier.wait()
        except threading.BrokenBarrierError:
            pass  # no second thread came: the counter is protected


class _RaceConnection:
    """Wraps a sqlite3 connection; waits once right after a statement that starts with `sql`."""

    def __init__(self, db, sql, meet):
        self._race = (db, sql, meet)

    def execute(self, statement, *args):
        db, sql, meet = self._race
        cursor = db.execute(statement, *args)
        if statement.startswith(sql):
            meet()
        return cursor

    def __enter__(self):
        return self._race[0].__enter__()

    def __exit__(self, *exc):
        return self._race[0].__exit__(*exc)

    def __getattr__(self, name):
        return getattr(self._race[0], name)


class _RaceWindow:
    @staticmethod
    def counter(store, name):
        """Reading the store's counter attribute `name` waits once for a second reader."""
        assert name in vars(store), (
            f"{type(store).__name__} has no {name}: race hook not installed (spec 0026)")
        meet = _Rendezvous().meet
        backing = "_race" + name
        vars(store)[backing] = vars(store).pop(name)

        def read(self):
            value = vars(self)[backing]
            meet()
            return value

        def write(self, value):
            vars(self)[backing] = value

        cls = type(store)
        store.__class__ = type("Race" + cls.__name__, (cls,), {name: property(read, write)})

    @staticmethod
    def item(record, key):
        """A copy of `record` whose `key` waits once for a second reader."""
        meet = _Rendezvous().meet

        class RaceRecord(dict):
            def __getitem__(self, k):
                value = super().__getitem__(k)
                if k == key:
                    meet()
                return value

        return RaceRecord(record)

    @staticmethod
    def statement(store, sql):
        """The store's connection waits once right after a statement starting with `sql`."""
        assert hasattr(store, "_db"), (
            f"{type(store).__name__} has no _db: race hook not installed (spec 0026)")
        store._db = _RaceConnection(store._db, sql, _Rendezvous().meet)


@pytest.fixture
def race_window():
    return _RaceWindow


def end_after_workdays(start, n):
    """End date of a range starting at `start` that holds n weekdays (Mon-Fri), spec 0014. Skips
    only Saturday/Sunday and does not call production code: pick dates without public holidays
    (e.g. Nov-Dec 2026). Holiday cases are written with explicit dates in test_workdays.py."""
    assert n >= 1, "n >= 1 (review F-3: n <= 0 would loop forever)"
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
