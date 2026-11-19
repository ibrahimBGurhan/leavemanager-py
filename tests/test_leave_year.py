"""Leave year and carried balance — spec 0040 (OD-11, OD-6).

The entitlement is born on every hire anniversary (K-1, K-2, K-7) and never lapses (K-3). The
balance table shows Devreden · Bu yılın hakkı · Kullanılan · Bekleyen · Kalan · Sonraki hak
tarihi (K-8); an opening balance (K-9) starts the count. Today = 2026-10-23 (conftest) unless a
test moves the clock. Every expected number is written out, never computed by the service.

"P" (spec): hired 2023-06-01, no opening balance, no requests.
"""
import datetime as dt

import pytest

import app as leave_app
from conftest import table_rows, visible_text
from domain.auth import LoginService
from domain.errors import InsufficientBalance

D = dt.date
P_HIRE = D(2023, 6, 1)
MSG_NEW = "Kalan izin bakiyeniz yetersiz (kalan %d gün, bekleyen %d gün, talep %d gün)."
MSG_APPROVE = "Personelin kalan izin bakiyesi yetersiz (kalan %d gün, talep %d gün)."
HEADER = ["Ad", "Birim", "Devreden", "Bu yılın hakkı", "Kullanılan", "Bekleyen", "Kalan",
          "Sonraki hak tarihi"]
OPENING_ROWS = [
    ["Ayse Yilmaz", "IT", "328", "26", "9", "3", "345", "2027-03-15"],
    ["Mehmet Demir", "Muhasebe", "90", "20", "0", "3", "110", "2027-06-01"],
    ["Zeynep Kaya", "IK", "0", "14", "0", "1", "14", "2026-11-10"],
    ["Ahmet Celik", "IT", "70", "20", "0", "5", "90", "2027-02-28"],
    ["Elif Sahin", "Satis", "0", "0", "0", "0", "0", "2027-06-01"],
]


def set_today(monkeypatch, day):
    monkeypatch.setattr(leave_app.clock, "today", lambda: day)


def add(svc, hire_date=P_HIRE, name="Izin Yili"):
    return svc.add_employee(name, "Arge", hire_date)


def add_request(emp, start, end, status="Onaylandi"):
    rid = leave_app.storage.next_request_id()
    leave_app.storage.add_request({"id": rid, "employee_id": emp["id"], "start": start,
                                   "end": end, "reason": "x", "status": status})
    return rid


def opening(emp, on, days):
    leave_app.storage.set_opening_balance({"employee_id": emp["id"], "date": on, "days": days})


def balance(svc, emp):
    """(Devreden, Bu yılın hakkı, Kullanılan, Bekleyen, Kalan, Sonraki hak tarihi)"""
    return (svc.get_carried(emp), svc.get_this_year_right(emp), svc.get_used_days(emp["id"]),
            svc.get_pending_days(emp["id"]), svc.get_remaining(emp), svc.get_next_right_date(emp))


def row(client, name):
    return next(r for r in table_rows(client.get("/").get_data(as_text=True)) if r[0] == name)


def post_new(client, emp, start, end):
    return client.post("/new", data={"employee_id": str(emp["id"]), "start": start.isoformat(),
                                     "end": end.isoformat(), "reason": "x"})


def status_of(request_id):
    return next(r for r in leave_app.storage.requests() if r["id"] == request_id)["status"]


# --- AC-1 -----------------------------------------------------------------------------------

@pytest.mark.parametrize("today, expected", [
    (D(2026, 5, 31), (14, 14, 0, 0, 28, D(2026, 6, 1))),
    (D(2026, 6, 1), (28, 14, 0, 0, 42, D(2027, 6, 1))),    # yıl dönümü günü hak doğar
    (D(2026, 10, 23), (28, 14, 0, 0, 42, D(2027, 6, 1))),
], ids=["day-before", "anniversary", "today"])
def test_right_is_born_on_anniversary(svc, monkeypatch, today, expected):
    emp = add(svc)
    set_today(monkeypatch, today)
    assert balance(svc, emp) == expected


# --- AC-2 -----------------------------------------------------------------------------------

@pytest.mark.parametrize("hire, next_date", [(D(2026, 6, 1), D(2027, 6, 1)),
                                             (D(2027, 2, 1), D(2028, 2, 1))],
                         ids=["first-year", "future-hire"])
def test_first_year_and_future_hire(svc, hire, next_date):
    emp = add(svc, hire)
    assert balance(svc, emp) == (0, 0, 0, 0, 0, next_date)


# --- AC-3 -----------------------------------------------------------------------------------

@pytest.mark.parametrize("today, expected", [
    (D(2026, 10, 23), (56, 14, 0, 0, 70, D(2026, 11, 1))),   # 5. yıl: 14
    (D(2026, 11, 1), (70, 20, 0, 0, 90, D(2027, 11, 1))),    # 6. yıl: yalnız yeni hak 20
], ids=["5th-year", "6th-year"])
def test_new_tier_applies_only_to_new_right(svc, monkeypatch, today, expected):
    emp = add(svc, D(2020, 11, 1))
    set_today(monkeypatch, today)
    assert balance(svc, emp) == expected


# --- AC-4 -----------------------------------------------------------------------------------

@pytest.mark.parametrize("today, expected", [
    (D(2026, 10, 23), (70, 20, 0, 0, 90, D(2027, 2, 28))),   # artık olmayan yıl: 28 Şubat
    (D(2028, 2, 28), (90, 20, 0, 0, 110, D(2028, 2, 29))),   # artık yıl: 29 Şubat
], ids=["2026", "2028-02-28"])
def test_feb_29_anniversary_and_next_date(svc, monkeypatch, today, expected):
    emp = add(svc, D(2020, 2, 29))
    set_today(monkeypatch, today)
    assert balance(svc, emp) == expected


# --- AC-5 -----------------------------------------------------------------------------------

def test_request_spanning_anniversary_is_one_piece(svc):
    """25 May–5 Jun 2026 = 7 working days (Kurban Bayramı 27–29 May); it starts before the
    2026-06-01 anniversary, so it belongs to the previous leave year (K-5)."""
    emp = add(svc)
    add_request(emp, D(2026, 5, 25), D(2026, 6, 5))
    assert balance(svc, emp) == (21, 14, 0, 0, 35, D(2027, 6, 1))
    add_request(emp, D(2026, 6, 8), D(2026, 6, 12))
    assert balance(svc, emp) == (21, 14, 5, 0, 30, D(2027, 6, 1))


# --- AC-6 -----------------------------------------------------------------------------------

def test_future_approved_request_reduces_today(svc):
    emp = add(svc)
    add_request(emp, D(2027, 7, 5), D(2027, 7, 9))
    assert balance(svc, emp) == (28, 14, 5, 0, 37, D(2027, 6, 1))


# --- AC-7 -----------------------------------------------------------------------------------

@pytest.mark.parametrize("start, end, workdays, saved", [
    (D(2026, 11, 2), D(2026, 11, 19), 14, True),
    (D(2027, 6, 7), D(2027, 6, 25), 15, False),    # 2027-06-01'de doğacak hak sayılmaz (K-6)
], ids=["14-saved", "15-refused"])
def test_new_request_uses_rights_born_by_today(client, svc, start, end, workdays, saved):
    emp = add(svc, D(2025, 6, 1))
    assert svc.calc_days(start, end) == workdays
    before = len(leave_app.storage.requests())
    resp = post_new(client, emp, start, end)
    if saved:
        assert resp.status_code == 302
        assert len(leave_app.storage.requests()) == before + 1
    else:
        assert resp.status_code == 400
        assert MSG_NEW % (14, 0, 15) in visible_text(resp.get_data(as_text=True))
        assert len(leave_app.storage.requests()) == before
        with pytest.raises(InsufficientBalance):
            svc.create_request(emp["id"], start, end, "x")
        assert len(leave_app.storage.requests()) == before


# --- AC-8 -----------------------------------------------------------------------------------

@pytest.mark.parametrize("end, workdays, approved", [(D(2026, 12, 29), 42, True),
                                                     (D(2026, 12, 30), 43, False)],
                         ids=["42-approved", "43-stays-pending"])
def test_approval_uses_new_remaining(client, svc, end, workdays, approved):
    """2 Nov–29/30 Dec 2026 has no public holiday."""
    emp = add(svc)
    start = D(2026, 11, 2)
    assert svc.calc_days(start, end) == workdays
    rid = add_request(emp, start, end, status="Beklemede")
    resp = client.post(f"/requests/{rid}/approve")
    if approved:
        assert resp.status_code == 302
        assert status_of(rid) == "Onaylandi"
        assert svc.get_remaining(emp) == 0
    else:
        assert resp.status_code == 400
        assert MSG_APPROVE % (42, 43) in visible_text(resp.get_data(as_text=True))
        assert status_of(rid) == "Beklemede"
        assert svc.get_remaining(emp) == 42


# --- AC-9 -----------------------------------------------------------------------------------

def test_opening_balance_before_anniversary(svc):
    emp = add(svc)
    opening(emp, D(2026, 1, 1), 10)
    add_request(emp, D(2025, 12, 1), D(2025, 12, 5))   # before the opening date: inside the 10
    assert balance(svc, emp) == (10, 14, 0, 0, 24, D(2027, 6, 1))


# --- AC-10 ----------------------------------------------------------------------------------

def test_opening_balance_after_anniversary(svc, monkeypatch):
    emp = add(svc)
    opening(emp, D(2026, 7, 1), 10)
    assert balance(svc, emp) == (10, 0, 0, 0, 10, D(2027, 6, 1))
    add_request(emp, D(2026, 6, 15), D(2026, 6, 19))   # before the opening date: not counted
    assert balance(svc, emp) == (10, 0, 0, 0, 10, D(2027, 6, 1))
    add_request(emp, D(2026, 8, 3), D(2026, 8, 7))
    assert balance(svc, emp) == (10, 0, 5, 0, 5, D(2027, 6, 1))
    set_today(monkeypatch, D(2027, 6, 1))
    assert balance(svc, emp) == (5, 14, 0, 0, 19, D(2028, 6, 1))


# --- AC-11 ----------------------------------------------------------------------------------

def test_negative_remaining_is_shown_and_refuses(client, svc):
    emp = add(svc)
    opening(emp, D(2026, 7, 1), 2)
    add_request(emp, D(2026, 8, 3), D(2026, 8, 7))
    assert balance(svc, emp) == (2, 0, 5, 0, -3, D(2027, 6, 1))
    assert row(client, "Izin Yili") == ["Izin Yili", "Arge", "2", "0", "5", "0", "-3", "2027-06-01"]
    before = len(leave_app.storage.requests())
    resp = post_new(client, emp, D(2026, 11, 2), D(2026, 11, 2))
    assert resp.status_code == 400
    assert MSG_NEW % (-3, 0, 1) in visible_text(resp.get_data(as_text=True))
    assert len(leave_app.storage.requests()) == before


# --- AC-12 ----------------------------------------------------------------------------------

def test_dashboard_opening_data_hr(client):
    rows = table_rows(client.get("/").get_data(as_text=True))
    assert rows[0] == HEADER
    assert rows[1:] == OPENING_ROWS


def account(role, employee_id):
    return {"email": "kisi@firma.com", "password_hash": "", "role": role,
            "employee_id": employee_id, "active": True, "failed_attempts": 0,
            "locked_until": None}


@pytest.mark.parametrize("acc, names", [
    (account("Yonetici", 1), ["Ayse Yilmaz", "Ahmet Celik"]),   # IT birimi
    (account("Personel", 2), ["Mehmet Demir"]),                 # yalnız kendisi
], ids=["manager", "staff"])
def test_dashboard_scope_manager_and_staff(client, monkeypatch, acc, names):
    monkeypatch.setattr(LoginService, "session_account", lambda self, email, login_at: acc)
    rows = table_rows(client.get("/").get_data(as_text=True))
    assert rows[0] == HEADER
    assert rows[1:] == [r for r in OPENING_ROWS if r[0] in names]
