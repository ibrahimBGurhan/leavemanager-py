"""Baseline (characterization) tests for LeaveService — spec 0001, AC-1..AC-6.

Tests named ``*_current`` pin CURRENT behavior that is known not to be the target rule
(docs/domain.md, BR-n / OD-n). A /change or /fix-bug that fixes the rule updates them in its spec.
"""
import datetime as dt

import pytest

import app as leave_app
from conftest import TODAY


def employee(hire_date, emp_id=100):
    return {"id": emp_id, "name": "Test", "department": "IT", "hire_date": hire_date}


def by_name(name):
    return next(e for e in leave_app.Db.employees if e["name"] == name)


# --- AC-1 -----------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "years, days",
    [
        (0, 0),
        (1, 14),
        (5, 14),
        (6, 20),
        (14, 20),
        (16, 26),
    ],
)
def test_entitlement_by_seniority(svc, years, days):
    """AC-1: kıdeme göre hak (15 yıl ayrı testte)."""
    emp = employee(dt.date(TODAY.year - years, 1, 1))
    assert svc.get_seniority_years(emp) == years
    assert svc.get_entitlement(emp) == days


def test_entitlement_at_15_years_current(svc):
    """MEVCUT DAVRANIŞ — hedef değil (BR-1 / OD-1) · AC-1: tam 15 yıl 20 gün; kanunda 26."""
    emp = employee(dt.date(TODAY.year - 15, 1, 1))
    assert svc.get_seniority_years(emp) == 15
    assert svc.get_entitlement(emp) == 20


# --- AC-2 -----------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "hire_date, years",
    [
        (dt.date(2025, 12, 31), 1),  # 10 ay hizmet, yine de 1 yıl
        (dt.date(2020, 2, 29), 6),
        (dt.date(2026, 6, 1), 0),
    ],
)
def test_seniority_is_year_difference_current(svc, hire_date, years):
    """MEVCUT DAVRANIŞ — hedef değil (BR-2 / OD-2) · AC-2: ay ve gün yok sayılır."""
    assert svc.get_seniority_years(employee(hire_date)) == years


# --- AC-3 -----------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "start, end, days",
    [
        (dt.date(2026, 11, 9), dt.date(2026, 11, 9), 1),
        (dt.date(2026, 11, 2), dt.date(2026, 11, 8), 7),  # Pazartesi–Pazar: hafta sonu da düşer
        (dt.date(2026, 11, 2), dt.date(2026, 11, 1), 0),  # ters aralık doğrulanmıyor (BR-9)
    ],
)
def test_calc_days_counts_calendar_days_current(svc, start, end, days):
    """MEVCUT DAVRANIŞ — hedef değil (BR-3 / OD-4, BR-9) · AC-3: takvim günü sayılır."""
    assert svc.calc_days(start, end) == days


# --- AC-4 -----------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "name, entitlement, used, remaining",
    [
        ("Ayse Yilmaz", 26, 12, 14),
        ("Mehmet Demir", 20, 0, 20),
        ("Zeynep Kaya", 14, 0, 14),
        ("Ahmet Celik", 20, 0, 20),
        ("Elif Sahin", 0, 0, 0),
    ],
)
def test_balances_at_opening_data(svc, name, entitlement, used, remaining):
    """AC-4: hak / kullanılan / kalan, açılış verisinde."""
    emp = by_name(name)
    assert svc.get_entitlement(emp) == entitlement
    assert svc.get_used_days(emp["id"]) == used
    assert svc.get_remaining(emp) == remaining


def test_only_approved_requests_count_as_used(svc):
    """AC-4 (BR-4 / BR-5): bekleyen ve reddedilen talepler kullanılanı değiştirmez."""
    ayse = by_name("Ayse Yilmaz")
    for status in ("Beklemede", "Reddedildi"):
        leave_app.Db.requests.append({
            "id": 99, "employee_id": ayse["id"], "start": dt.date(2026, 11, 16),
            "end": dt.date(2026, 11, 20), "reason": "x", "status": status,
        })
    assert svc.get_used_days(ayse["id"]) == 12
    assert svc.get_remaining(ayse) == 14


# --- AC-5 -----------------------------------------------------------------------------------

def test_create_request_saves_pending_request(svc):
    """AC-5 (BR-7): yeterli bakiye → Beklemede, sıradaki numara (9), başarılı."""
    mehmet = by_name("Mehmet Demir")
    ok = svc.create_request(mehmet["id"], dt.date(2026, 11, 16), dt.date(2026, 11, 18), "Tatil")
    assert ok is True
    assert len(leave_app.Db.requests) == 9
    saved = leave_app.Db.requests[-1]
    assert saved == {
        "id": 9, "employee_id": mehmet["id"], "start": dt.date(2026, 11, 16),
        "end": dt.date(2026, 11, 18), "reason": "Tatil", "status": "Beklemede",
    }


def test_create_request_accepts_past_dates(svc):
    """AC-5 (BR-8): geçmiş tarihli talep de kaydedilir (IK geriye dönük giriş)."""
    mehmet = by_name("Mehmet Demir")
    ok = svc.create_request(mehmet["id"], dt.date(2026, 1, 5), dt.date(2026, 1, 6), "Geriye donuk")
    assert ok is True
    assert leave_app.Db.requests[-1]["start"] == dt.date(2026, 1, 5)
    assert leave_app.Db.requests[-1]["status"] == "Beklemede"


def test_create_request_rejects_when_remaining_equals_days_current(svc):
    """MEVCUT DAVRANIŞ — hedef değil (BR-6) · AC-5: kalan = gün ise reddedilir."""
    zeynep = by_name("Zeynep Kaya")  # kalan 14
    ok = svc.create_request(zeynep["id"], dt.date(2026, 12, 1), dt.date(2026, 12, 14), "Uzun")
    assert ok is False
    assert len(leave_app.Db.requests) == 8


def test_create_request_unknown_employee_reports_success_current(svc):
    """MEVCUT DAVRANIŞ — hedef değil (invariant: talep var olan personele bağlı; başarısız işlem
    başarılı gösterilmez · OD-7) · AC-5: olmayan personel kaydedilmez ama True döner."""
    ok = svc.create_request(99, dt.date(2026, 11, 16), dt.date(2026, 11, 16), "x")
    assert ok is True
    assert len(leave_app.Db.requests) == 8


# --- AC-6 -----------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "status, color",
    [
        ("Onaylandi", "green"),
        ("Beklemede", "orange"),
        ("Reddedildi", "red"),
        ("BEKLEMEDE", "orange"),  # turuncu kuralı büyük/küçük harfe duyarsız
        ("onaylandi", "#999"),    # diğerleri duyarlı
        ("reddedildi", "#999"),
        ("Iptal", "#999"),        # bilinmeyen durum gri
    ],
)
def test_status_badge(svc, status, color):
    """AC-6: rozet rengi ve metni."""
    badge = svc.status_badge(status)
    assert f"color:{color}" in badge
    assert status in badge
