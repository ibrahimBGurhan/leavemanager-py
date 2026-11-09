"""Login and session rules (domain/auth.py) — spec 0019 (ADR-0002 D-4, D-5).

The service runs with a fake clock (frozen, moved forward by the test), a fake hasher that counts
its verify calls (plan 0019 Risk 7: timing is proven by work done, not by measuring time) and its
own storage instance. The restart case uses a SQLite file in a pytest tmp dir.
"""
import datetime as dt
import logging
import threading

import pytest

from domain.auth import (LOCK_MINUTES, MAX_EMAIL_LENGTH, MAX_PASSWORD_LENGTH, SESSION_HOURS,
                         LoginService)
from domain.errors import LoginRefused, SessionExpired
from storage.memory import MemoryStorage
from storage.sqlite import SqliteStorage

pytestmark = pytest.mark.usefixtures("logged_out")    # the real session check (conftest)

T0 = dt.datetime(2026, 11, 6, 9, 0, 0)
EMAIL = "ali@firma.com"
PASSWORD = "dogru parola 12"
WRONG = "yanlis parola 1"


class FakeClock:
    def __init__(self, now=T0):
        self.current = now

    def now(self):
        return self.current

    def today(self):
        return self.current.date()

    def advance(self, **delta):
        self.current += dt.timedelta(**delta)


class FakeHasher:
    def __init__(self):
        self.verifies = 0
        self.hashes = 0

    def hash(self, password):
        self.hashes += 1
        return "fake$" + password

    def verify(self, password_hash, password):
        self.verifies += 1
        return password_hash == "fake$" + password


def add(store, email=EMAIL, password=PASSWORD, active=True):
    store.add_account({"email": email, "password_hash": "fake$" + password, "role": "IK",
                       "employee_id": None, "active": active, "failed_attempts": 0,
                       "locked_until": None})


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def hasher():
    return FakeHasher()


@pytest.fixture
def store():
    s = MemoryStorage()
    add(s)
    return s


@pytest.fixture
def logins(clock, store, hasher):
    return LoginService(clock, store, hasher)


def state(store, email=EMAIL):
    a = next(a for a in store.accounts() if a["email"] == email)
    return a["failed_attempts"], a["locked_until"]


def refused(logins, email, password):
    with pytest.raises(LoginRefused) as info:
        logins.authenticate(email, password)
    return info.value.reason


def fail(logins, times, email=EMAIL):
    return [refused(logins, email, WRONG) for _ in range(times)]


# --- R-2: success -------------------------------------------------------------------------------

@pytest.mark.parametrize("typed", [EMAIL, "  ALI@Firma.com  "])
def test_right_password_returns_the_account(logins, typed):
    assert logins.authenticate(typed, PASSWORD)["email"] == EMAIL


def test_password_is_used_as_typed(logins):
    assert refused(logins, EMAIL, PASSWORD + " ") == "sifre"
    assert refused(logins, EMAIL, PASSWORD.upper()) == "sifre"


# --- AC-4: lock --------------------------------------------------------------------------------

def test_four_failures_then_success_resets(logins, store):
    fail(logins, 4)
    assert state(store) == (4, None)
    logins.authenticate(EMAIL, PASSWORD)
    assert state(store) == (0, None)
    fail(logins, 4)                                     # a fresh run of four does not lock
    assert state(store) == (4, None)


def test_fifth_failure_locks(logins, store):
    assert fail(logins, 5) == ["sifre"] * 5
    assert state(store) == (5, T0 + dt.timedelta(minutes=LOCK_MINUTES))


def test_locked_rejects_right_password_and_keeps_count(logins, store, clock):
    fail(logins, 5)
    clock.advance(minutes=5)
    assert refused(logins, EMAIL, PASSWORD) == "kilitli"
    assert refused(logins, EMAIL, WRONG) == "kilitli"
    assert state(store) == (5, T0 + dt.timedelta(minutes=15))


@pytest.mark.parametrize("after, opens", [(dt.timedelta(minutes=15, seconds=-1), False),
                                          (dt.timedelta(minutes=15), True)],
                         ids=["14:59", "15:00"])
def test_lock_ends_at_fifteen_minutes(logins, store, clock, after, opens):
    fail(logins, 5)
    clock.current = T0 + after
    if opens:
        assert logins.authenticate(EMAIL, PASSWORD)["email"] == EMAIL
        assert state(store) == (0, None)
    else:
        assert refused(logins, EMAIL, PASSWORD) == "kilitli"


def test_first_failure_after_lock_counts_one(logins, store, clock):
    fail(logins, 5)
    clock.advance(minutes=15)
    assert refused(logins, EMAIL, WRONG) == "sifre"
    assert state(store) == (1, None)


def test_lock_survives_restart(tmp_path, clock, hasher):
    path = tmp_path / "leave.db"
    first = SqliteStorage(path)
    add(first)
    fail(LoginService(clock, first, hasher), 5)
    first.close()
    second = SqliteStorage(path)
    try:
        assert state(second) == (5, T0 + dt.timedelta(minutes=15))
        assert refused(LoginService(clock, second, hasher), EMAIL, PASSWORD) == "kilitli"
    finally:
        second.close()


@pytest.mark.parametrize("make_store", [MemoryStorage, lambda: SqliteStorage(":memory:")],
                         ids=["memory", "sqlite"])
def test_concurrent_failures_lock_by_the_fifth(make_store, clock, hasher):
    """G-4: wrong passwords arriving at the same time do not slip past the limit."""
    store = make_store()
    add(store)
    logins = LoginService(clock, store, hasher)
    start = threading.Barrier(5)

    def worker():
        start.wait()
        refused(logins, EMAIL, WRONG)

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    count, locked_until = state(store)
    assert count == 5 and locked_until == T0 + dt.timedelta(minutes=15)
    assert refused(logins, EMAIL, PASSWORD) == "kilitli"


# --- R-3, AC-3: every refusal -------------------------------------------------------------------

def test_refusal_reasons(logins, store):
    add(store, "pasif@firma.com", active=False)
    assert refused(logins, "yok@firma.com", PASSWORD) == "bilinmeyen"
    assert refused(logins, "pasif@firma.com", PASSWORD) == "pasif"
    assert refused(logins, "", PASSWORD) == "bos"
    assert refused(logins, "   ", PASSWORD) == "bos"
    assert refused(logins, EMAIL, "") == "bos"
    assert refused(logins, None, None) == "bos"


# --- AC-5: timing and counters ------------------------------------------------------------------

def test_unknown_email_costs_one_verify(logins, hasher, store):
    add(store, "pasif@firma.com", active=False)
    cost = {}
    for name, email, password in [("unknown", "yok@firma.com", PASSWORD), ("wrong", EMAIL, WRONG),
                                  ("inactive", "pasif@firma.com", PASSWORD)]:
        before = hasher.verifies
        refused(logins, email, password)
        cost[name] = hasher.verifies - before
    fail(logins, 4)                      # 5 wrong in total: the account is now locked
    before = hasher.verifies
    refused(logins, EMAIL, PASSWORD)
    cost["locked"] = hasher.verifies - before
    assert cost == {"unknown": 1, "wrong": 1, "inactive": 1, "locked": 1}


def test_dummy_hash_is_made_once_with_the_hasher(logins, hasher):
    refused(logins, "yok@firma.com", PASSWORD)
    refused(logins, "baska@firma.com", PASSWORD)
    assert hasher.hashes == 1


def test_unknown_and_inactive_touch_no_counter(logins, store):
    add(store, "pasif@firma.com", active=False)
    before = [dict(a) for a in store.accounts()]
    for _ in range(6):
        refused(logins, "yok@firma.com", WRONG)
        refused(logins, "pasif@firma.com", WRONG)
    assert [dict(a) for a in store.accounts()] == before


@pytest.mark.parametrize("email_len, password_len, accepted", [
    (MAX_EMAIL_LENGTH, MAX_PASSWORD_LENGTH, True),
    (MAX_EMAIL_LENGTH + 1, 20, False),
    (20, MAX_PASSWORD_LENGTH + 1, False),
], ids=["254/1024", "255-email", "1025-password"])
def test_input_limits(clock, hasher, email_len, password_len, accepted):
    email = "a" * (email_len - len("@firma.com")) + "@firma.com"
    password = "p" * password_len
    store = MemoryStorage()
    add(store, email, password)
    logins = LoginService(clock, store, hasher)
    if accepted:
        assert logins.authenticate(email, password)["email"] == email
    else:
        before = hasher.verifies
        assert refused(logins, email, password) == "sinir"
        assert hasher.verifies == before and hasher.hashes == 0
        assert state(store, email) == (0, None)


# --- AC-6: log ---------------------------------------------------------------------------------

def records(caplog):
    return [(r.levelname, r.getMessage()) for r in caplog.records if r.name == "domain.auth"]


def test_failure_and_lock_log_lines(logins, store, caplog):
    add(store, "pasif@firma.com", active=False)
    caplog.set_level(logging.INFO)
    fail(logins, 5)
    refused(logins, EMAIL, PASSWORD)
    refused(logins, "pasif@firma.com", PASSWORD)
    assert records(caplog) == [
        ("WARNING", "başarısız giriş: ali@firma.com (art arda 1)"),
        ("WARNING", "başarısız giriş: ali@firma.com (art arda 2)"),
        ("WARNING", "başarısız giriş: ali@firma.com (art arda 3)"),
        ("WARNING", "başarısız giriş: ali@firma.com (art arda 4)"),
        ("WARNING", "başarısız giriş: ali@firma.com (art arda 5)"),
        ("WARNING", "hesap kilitlendi: ali@firma.com (bitiş 2026-11-06T09:15:00)"),
        ("WARNING", "başarısız giriş: ali@firma.com kilitli (bitiş 2026-11-06T09:15:00)"),
        ("WARNING", "başarısız giriş: pasif@firma.com pasif"),
    ]


def test_login_and_logout_are_info(logins, caplog):
    caplog.set_level(logging.INFO)
    logins.authenticate(EMAIL, PASSWORD)
    logins.logout(EMAIL)
    assert records(caplog) == [("INFO", "giriş: ali@firma.com"), ("INFO", "çıkış: ali@firma.com")]


def test_secrets_never_logged(logins, caplog):
    caplog.set_level(logging.DEBUG)
    typed = "parola-yanlis-alana@firma.com"
    refused(logins, typed, PASSWORD)
    refused(logins, "x" * 300 + "@firma.com", PASSWORD)
    fail(logins, 5)
    refused(logins, EMAIL, PASSWORD)
    text = caplog.text
    for secret in (typed, PASSWORD, WRONG, "fake$", "x" * 300):
        assert secret not in text
    assert records(caplog)[0] == ("WARNING", "başarısız giriş: bilinmeyen hesap")
    assert records(caplog)[1] == ("WARNING", "başarısız giriş: girdi sınırı aşıldı")


# --- AC-7, AC-8: session -----------------------------------------------------------------------

@pytest.mark.parametrize("after, valid", [(dt.timedelta(hours=SESSION_HOURS, seconds=-1), True),
                                          (dt.timedelta(hours=SESSION_HOURS), False)],
                         ids=["7:59:59", "8:00:00"])
def test_session_lasts_eight_hours(logins, clock, after, valid):
    started = clock.now().isoformat()
    clock.current = T0 + after
    if valid:
        assert logins.session_account(EMAIL, started)["email"] == EMAIL
    else:
        with pytest.raises(SessionExpired):
            logins.session_account(EMAIL, started)


def test_activity_does_not_extend_session(logins, clock):
    started = clock.now().isoformat()
    for _ in range(7):
        clock.advance(hours=1)
        assert logins.session_account(EMAIL, started)
    clock.advance(hours=1)
    with pytest.raises(SessionExpired):
        logins.session_account(EMAIL, started)


@pytest.mark.parametrize("email, login_at", [
    (None, T0.isoformat()), (EMAIL, None), ("", ""), (EMAIL, "dun"),
    (EMAIL, (T0 + dt.timedelta(minutes=1)).isoformat()),      # from the future
    ("yok@firma.com", T0.isoformat()),
], ids=["no-email", "no-time", "empty", "bad-time", "future", "unknown"])
def test_no_session_account(logins, email, login_at):
    assert logins.session_account(email, login_at) is None


@pytest.mark.parametrize("change", ["inactive", "deleted"])
def test_inactive_or_deleted_account_has_no_session(logins, store, change):
    started = T0.isoformat()
    assert logins.session_account(EMAIL, started)
    if change == "inactive":
        store.set_account_active(EMAIL, False)
    else:
        store._accounts.clear()                       # no delete in the contract yet (G-2)
    assert logins.session_account(EMAIL, started) is None
