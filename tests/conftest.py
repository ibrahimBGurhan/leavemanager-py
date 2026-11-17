"""Shared fixtures for the baseline (characterization) tests — spec 0001.

- Tests touch app.py only through its seams (spec 0005): app.clock, app.storage, app.svc and
  app.app. The layer refactor keeps these names at the composition root.
- "Today" is frozen at 2026-10-23 through app.clock (docs/conventions.md, Data rules).
- Every test starts from the app's opening data (docs/testing.md, Resource hygiene rule 5).
- HTML helpers return what the user sees, so tests assert values, not markup (spec 0001, R-5).
"""
import datetime as _dt
import os
import re
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


# --- spec 0034: assertions read behavior, not markup -------------------------------------------
class _Page(HTMLParser):
    """What a browser offers on the page: controls (with their labels and button text), links
    and headings. Class names and attribute order do not matter (spec 0034 R-8)."""

    def __init__(self):
        super().__init__()
        self.controls, self.links, self.headings, self.labels = [], [], [], {}
        self.scripts, self.form_bs_attrs, self._forms = [], [], 0
        self._open = None   # ("button" | "a" | "h" | "label" | "script", record, label target)

    def handle_starttag(self, tag, attrs):
        a = {k: (v if v is not None else "") for k, v in attrs}
        if tag == "form":
            self._forms += 1
        if self._forms:
            self.form_bs_attrs += [k for k in a if k.startswith("data-bs-")]
        if tag == "script":
            script = {"src": a.get("src"), "text": ""}
            self.scripts.append(script)
            self._open = ("script", script, None)
        elif tag in ("input", "select", "textarea", "button"):
            control = {"tag": tag, **a}
            if tag == "button":
                control.setdefault("type", "submit")
                control["text"] = ""
                self._open = ("button", control, None)
            self.controls.append(control)
        elif tag == "a":
            link = {"href": a.get("href"), "aria-current": a.get("aria-current"), "text": ""}
            self.links.append(link)
            self._open = ("a", link, None)
        elif tag in ("h1", "h2", "h3"):
            heading = {"tag": tag, "text": ""}
            self.headings.append(heading)
            self._open = ("h", heading, None)
        elif tag == "label":
            self._open = ("label", {"text": ""}, a.get("for"))

    def handle_data(self, data):
        if self._open is not None:
            self._open[1]["text"] += data

    def handle_endtag(self, tag):
        if tag == "form" and self._forms:
            self._forms -= 1
        if self._open is None:
            return
        kind, record, target = self._open
        if (kind, tag) in (("button", "button"), ("a", "a"), ("label", "label"),
                           ("script", "script")) or (
                kind == "h" and tag in ("h1", "h2", "h3")):
            record["text"] = _normalize(record["text"])
            if kind == "label" and target:
                self.labels[target] = record["text"]
            self._open = None


def _page(html):
    p = _Page()
    p.feed(html)
    for control in p.controls:
        if control.get("id") in p.labels:
            control["label"] = p.labels[control["id"]]
    return p


def controls(html):
    """Form controls and buttons as dicts of their attributes; a <button> also has "text", a
    control with a <label for=…> also has "label"."""
    return _page(html).controls


def submit_labels(html):
    """Labels of the page's submit controls: <input type=submit value=…> or a button's text."""
    return [c.get("value") if c["tag"] == "input" else c["text"]
            for c in controls(html) if c.get("type") == "submit"]


def page_links(html):
    """Every link the user can follow, in page order, as (text, href); today only the menu has
    links."""
    return [(link["text"], link["href"]) for link in _page(html).links]


def headings(html):
    """Texts of the page's h1–h3 headings, in order."""
    return [h["text"] for h in _page(html).headings]


BOOTSTRAP_JS = "/static/vendor/bootstrap-5.3.8/bootstrap.bundle.min.js"


def scripts(html):
    """Every <script> as (src, inline text): spec 0034 allows only Bootstrap's vendored bundle."""
    return [(s["src"], s["text"].strip()) for s in _page(html).scripts]


def form_bs_attrs(html):
    """data-bs-* attributes inside forms: Bootstrap's JS bound to a form control (spec 0034)."""
    return _page(html).form_bs_attrs


def current_links(html):
    """Links marked as the current page (aria-current="page"), as (text, href)."""
    return [(link["text"], link["href"]) for link in _page(html).links
            if link["aria-current"] == "page"]


# --- spec 0035: screen bodies ------------------------------------------------------------------
_BADGE = re.compile(r"""<span class=["'][^"']*\btext-bg-(\w+)\b[^"']*["']>""")
_BOX = re.compile(r"""<div class=["']alert alert-(\w+)["'](?: role=["'](\w+)["'])?>(.*?)</div>""", re.S)


def badge_kind(cell_html):
    """Kind of the status badge in a status cell (success, warning, danger, secondary); None if
    the cell carries no badge (spec 0035 R-6)."""
    m = _BADGE.search(cell_html)
    return m.group(1) if m else None


def message_boxes(html):
    """Message boxes on the page as (kind, role, text): role "alert" is announced at once,
    "status" quietly, "" not at all (spec 0035 R-7)."""
    return [(kind, role or "", _normalize(text)) for kind, role, text in _BOX.findall(html)]


def table_wrapped(html):
    """For every <table>, whether it sits directly in a horizontally scrollable box (R-5)."""
    return [bool(re.search(r"""<div class=["'][^"']*\btable-responsive\b[^"']*["']>\s*$""",
                           html[:m.start()]))
            for m in re.finditer(r"<table\b", html)]
