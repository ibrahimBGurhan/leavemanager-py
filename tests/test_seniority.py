"""Spec 0038 — kıdem tamamlanmış hizmet yılıdır; tam 15 yıl 26 gün hak eder (BR-1, BR-2).

"Bugün" testlerin sabit tarihi 2026-10-23'tür (conftest); CB-3 ve PB-1 saati test içinde değiştirir.
"""
import datetime as dt

import pytest

import app as leave_app
from conftest import table_rows, visible_text

D = dt.date


def employee(hire_date, emp_id=100):
    return {"id": emp_id, "name": "Test", "department": "IT", "hire_date": hire_date}


def set_today(monkeypatch, day):
    monkeypatch.setattr(leave_app.clock, "today", lambda: day)


def add(svc, hire_date, name="Kidem Test"):
    return svc.add_employee(name, "IT", hire_date)


def post_new(client, emp_id, start, end):
    return client.post("/new", data={"employee_id": str(emp_id), "start": start.isoformat(),
                                     "end": end.isoformat(), "reason": "x"})


def balance_row(client, name):
    return next(r for r in table_rows(client.get("/").get_data(as_text=True)) if r[0] == name)


# --- CB-1 -----------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "hire_date, years, days",
    [
        (D(2025, 10, 23), 1, 14),  # yıl dönümü günü yılı tamamlar (S-1)
        (D(2025, 10, 24), 0, 0),
        (D(2025, 12, 31), 0, 0),  # yıl farkı 1, tamamlanmış yıl 0
    ],
)
def test_seniority_counts_completed_years(svc, hire_date, years, days):
    """CB-1: kıdem tamamlanmış hizmet yılıdır."""
    emp = employee(hire_date)
    assert svc.get_seniority_years(emp) == years
    assert svc.get_entitlement(emp) == days


# --- CB-2 -----------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "hire_date, years, days",
    [
        (D(2020, 10, 23), 6, 20),
        (D(2020, 10, 24), 5, 14),
        (D(2011, 10, 23), 15, 26),  # tam 15 yıl: 26 gün (OD-1)
        (D(2011, 10, 24), 14, 20),
    ],
)
def test_tier_boundaries_follow_anniversary(svc, hire_date, years, days):
    """CB-2: kademe sınırları yıl dönümüne göre."""
    emp = employee(hire_date)
    assert svc.get_seniority_years(emp) == years
    assert svc.get_entitlement(emp) == days


# --- CB-3 -----------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "today, years",
    [
        (D(2027, 2, 27), 6),
        (D(2027, 2, 28), 7),  # artık olmayan yılda yıl dönümü 28 Şubat (K-2)
        (D(2028, 2, 28), 7),  # artık yılda yıl dönümü 29 Şubat
        (D(2028, 2, 29), 8),
    ],
)
def test_feb_29_anniversary(svc, monkeypatch, today, years):
    """CB-3: 29 Şubat'ta işe girenin yıl dönümü."""
    set_today(monkeypatch, today)
    assert svc.get_seniority_years(employee(D(2020, 2, 29))) == years


# --- CB-4 -----------------------------------------------------------------------------------

def test_15_years_shows_26_on_dashboard(client, svc):
    """CB-4: tam 15 yıl kıdemli personel bakiye tablosunda Hak 26, Kalan 26."""
    add(svc, D(2011, 10, 23))
    assert balance_row(client, "Kidem Test") == ["Kidem Test", "IT", "26", "0", "26", "0"]


@pytest.mark.parametrize("end, workdays, saved", [(D(2026, 12, 7), 26, True),
                                                  (D(2026, 12, 8), 27, False)],
                         ids=["26-accepted", "27-refused"])
def test_15_years_request_boundary(client, svc, end, workdays, saved):
    """CB-4: tam 15 yıl → 26 günlük talep kabul (eskiden ret), 27 ret. 2–30 Kasım ve 1–8 Aralık
    2026 arasında resmî tatil yok (plan 0038 Risk 3); gün sayısı sabit beklenir."""
    emp = add(svc, D(2011, 10, 23))
    start = D(2026, 11, 2)
    assert svc.calc_days(start, end) == workdays
    before = len(leave_app.storage.requests())
    resp = post_new(client, emp["id"], start, end)
    if saved:
        assert resp.status_code == 302
        assert len(leave_app.storage.requests()) == before + 1
    else:
        assert resp.status_code == 400
        assert ("Kalan izin bakiyeniz yetersiz (kalan 26 gün, bekleyen 0 gün, talep 27 gün)."
                in visible_text(resp.get_data(as_text=True)))
        assert len(leave_app.storage.requests()) == before


def test_before_first_anniversary_request_refused(client, svc):
    """CB-4: yıl dönümü gelmemiş personelin hakkı yeni talep kontrolünde de 0."""
    emp = add(svc, D(2025, 12, 31))
    before = len(leave_app.storage.requests())
    resp = post_new(client, emp["id"], D(2026, 11, 2), D(2026, 11, 2))
    assert resp.status_code == 400
    assert ("Kalan izin bakiyeniz yetersiz (kalan 0 gün, bekleyen 0 gün, talep 1 gün)."
            in visible_text(resp.get_data(as_text=True)))
    assert len(leave_app.storage.requests()) == before


# --- PB-1 -----------------------------------------------------------------------------------

def test_opening_balances_on_2026_11_17(client, monkeypatch):
    """PB-1 (S-4): Zeynep'in 10 Kasım yıl dönümünden sonra da açılış sayıları aynı."""
    set_today(monkeypatch, D(2026, 11, 17))
    rows = table_rows(client.get("/").get_data(as_text=True))
    assert [r[:5] for r in rows[1:]] == [
        ["Ayse Yilmaz", "IT", "26", "9", "17"],
        ["Mehmet Demir", "Muhasebe", "20", "0", "20"],
        ["Zeynep Kaya", "IK", "14", "0", "14"],
        ["Ahmet Celik", "IT", "20", "0", "20"],
        ["Elif Sahin", "Satis", "0", "0", "0"],
    ]


# --- PB-3 -----------------------------------------------------------------------------------

@pytest.mark.parametrize("hire_date", [D(2026, 12, 1), D(2027, 2, 1)])
def test_future_hire_has_zero_entitlement(svc, hire_date):
    """PB-3 (S-2): henüz başlamamış personelin kıdemi 0 (eksi değil), hakkı 0."""
    emp = employee(hire_date)
    assert svc.get_seniority_years(emp) == 0
    assert svc.get_entitlement(emp) == 0
