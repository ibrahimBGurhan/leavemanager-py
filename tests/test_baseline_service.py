"""Baseline (characterization) tests for LeaveService — spec 0001, AC-1..AC-6.

Tests named ``*_current`` pin CURRENT behavior that is known not to be the target rule
(docs/domain.md, BR-n / OD-n). A /change or /fix-bug that fixes the rule updates them in its spec.
"""
import datetime as dt

import pytest

import app as leave_app
from conftest import TODAY, badge_kind, status_cell_html
from domain.errors import EmployeeNotFound


def employee(hire_date, emp_id=100):
    return {"id": emp_id, "name": "Test", "department": "IT", "hire_date": hire_date}


def by_name(name):
    return next(e for e in leave_app.storage.employees() if e["name"] == name)


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


def test_entitlement_at_15_years(svc):
    """Spec 0038 CB-2 (supersedes 0001/AC-1 15 satırı; OD-1 kararı): tam 15 yıl 26 gün."""
    emp = employee(dt.date(TODAY.year - 15, 1, 1))
    assert svc.get_seniority_years(emp) == 15
    assert svc.get_entitlement(emp) == 26


# --- AC-2 -----------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "hire_date, years",
    [
        (dt.date(2025, 12, 31), 0),  # 10 ay hizmet: yıl tamamlanmadı
        (dt.date(2020, 2, 29), 6),
        (dt.date(2026, 6, 1), 0),
    ],
)
def test_seniority_is_completed_years(svc, hire_date, years):
    """Spec 0038 CB-1 (supersedes 0001/AC-2; OD-2 kararı): kıdem tamamlanmış hizmet yılıdır.
    Ayrıntı: tests/test_seniority.py."""
    assert svc.get_seniority_years(employee(hire_date)) == years


# --- AC-3 -----------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "start, end, days",
    [
        (dt.date(2026, 11, 9), dt.date(2026, 11, 9), 1),
        (dt.date(2026, 11, 2), dt.date(2026, 11, 8), 5),  # Pazartesi–Pazar: hafta sonu sayılmaz
        (dt.date(2026, 11, 2), dt.date(2026, 11, 1), 0),  # ters aralık doğrulanmıyor (BR-9)
    ],
)
def test_calc_days_counts_working_days(svc, start, end, days):
    """Spec 0014 CB-1 (supersedes 0001/AC-3; BR-3 kararı): iş günü sayılır. Ayrıntı:
    tests/test_workdays.py."""
    assert svc.calc_days(start, end) == days


# --- AC-4 -----------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "name, entitlement, used, remaining",
    [
        # Spec 0040 (supersedes AC-4's Kalan = Hak − Kullanılan): Kalan = all rights born by
        # today − all approved (AC-12); Hak (the tier) and Kullanılan (this leave year) unchanged
        ("Ayse Yilmaz", 26, 9, 345),  # 0014 T4: #1 = 9 iş günü
        ("Mehmet Demir", 20, 0, 110),
        ("Zeynep Kaya", 14, 0, 14),
        ("Ahmet Celik", 20, 0, 90),
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
        leave_app.storage.add_request({
            "id": 99, "employee_id": ayse["id"], "start": dt.date(2026, 11, 16),
            "end": dt.date(2026, 11, 20), "reason": "x", "status": status,
        })
    assert svc.get_used_days(ayse["id"]) == 9  # 0014 T4: iş günü
    assert svc.get_remaining(ayse) == 345  # spec 0040 AC-12 (supersedes 17)


# --- AC-5 -----------------------------------------------------------------------------------

def test_create_request_saves_pending_request(svc):
    """AC-5 (BR-7): yeterli bakiye → Beklemede, sıradaki numara (9), başarılı."""
    mehmet = by_name("Mehmet Demir")
    ok = svc.create_request(mehmet["id"], dt.date(2026, 11, 16), dt.date(2026, 11, 18), "Tatil")
    assert ok is True
    assert len(leave_app.storage.requests()) == 9
    saved = leave_app.storage.requests()[-1]
    assert saved == {
        "id": 9, "employee_id": mehmet["id"], "start": dt.date(2026, 11, 16),
        "end": dt.date(2026, 11, 18), "reason": "Tatil", "status": "Beklemede",
    }


def test_create_request_accepts_past_dates(svc):
    """AC-5 (BR-8): geçmiş tarihli talep de kaydedilir (IK geriye dönük giriş)."""
    mehmet = by_name("Mehmet Demir")
    ok = svc.create_request(mehmet["id"], dt.date(2026, 1, 5), dt.date(2026, 1, 6), "Geriye donuk")
    assert ok is True
    assert leave_app.storage.requests()[-1]["start"] == dt.date(2026, 1, 5)
    assert leave_app.storage.requests()[-1]["status"] == "Beklemede"


def test_create_request_accepts_when_remaining_equals_days(svc):
    """Spec 0008 CB-1 (BR-6 kararı; supersedes 0001/AC-5): bakiyeyi tam kullanan talep kaydedilir.
    Spec 0013 K-2 (T5): sınır Kalan − Bekleyen."""
    zeynep = by_name("Zeynep Kaya")  # kalan 14, bekleyen 1 (#3)
    ok = svc.create_request(zeynep["id"], dt.date(2026, 12, 1), dt.date(2026, 12, 13), "Uzun")
    assert ok is True
    assert len(leave_app.storage.requests()) == 9


def test_create_request_unknown_employee_raises(svc):
    """Spec 0008 CB-2/CB-6 (supersedes 0001/AC-5): olmayan personel EmployeeNotFound fırlatır,
    kayıt oluşmaz."""
    with pytest.raises(EmployeeNotFound):
        svc.create_request(99, dt.date(2026, 11, 16), dt.date(2026, 11, 16), "x")
    assert len(leave_app.storage.requests()) == 8


# --- AC-6 -----------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "status, kind",
    [
        ("Onaylandi", "success"),
        ("Beklemede", "warning"),
        ("Reddedildi", "danger"),
        ("BEKLEMEDE", "warning"),  # uyarı kuralı büyük/küçük harfe duyarsız
        ("onaylandi", "secondary"),  # diğerleri duyarlı
        ("reddedildi", "secondary"),
        ("Iptal", "secondary"),      # bilinmeyen durum nötr
    ],
)
def test_status_badge(client, status, kind):
    """AC-6: rozet türü ve metni — talepler ekranında, kullanıcının gördüğü yerde (spec 0005;
    renk yerine tür, spec 0035 R-6)."""
    leave_app.storage.add_request({
        "id": 99, "employee_id": 1, "start": dt.date(2026, 11, 16),
        "end": dt.date(2026, 11, 16), "reason": "rozet-testi", "status": status,
    })
    badge = status_cell_html(client.get("/requests").get_data(as_text=True), "rozet-testi")
    assert badge_kind(badge) == kind
    assert "color" not in badge
    assert status in badge
