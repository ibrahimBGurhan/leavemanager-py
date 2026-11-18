"""2028 public holidays are not leave days — spec 0039.

The holiday list reaches 2028 (K-1: 14 dates, 6 on weekdays). 2028 arife half days count as
full working days (K-2/K-3). 2029 and later are outside the list: only weekends are dropped (K-4).
Opening data, today = 2026-10-23 (conftest).
"""
import datetime as dt

import pytest

import app as leave_app
from conftest import end_after_workdays, table_rows, visible_text
from domain.errors import InsufficientBalance

D = dt.date
HOLIDAYS_2028 = {
    D(2028, 1, 1), D(2028, 4, 23), D(2028, 5, 1), D(2028, 5, 19), D(2028, 7, 15),
    D(2028, 8, 30), D(2028, 10, 29),
    D(2028, 2, 26), D(2028, 2, 27), D(2028, 2, 28),               # Ramazan Bayramı
    D(2028, 5, 5), D(2028, 5, 6), D(2028, 5, 7), D(2028, 5, 8),   # Kurban Bayramı
}


# --- CB-1 -----------------------------------------------------------------------------------

def test_holidays_2028_list():
    from domain.workdays import HOLIDAYS
    assert {h for h in HOLIDAYS if h.year == 2028} == HOLIDAYS_2028
    assert max(h.year for h in HOLIDAYS) == 2028


def test_each_2028_holiday_is_zero(svc):
    for day in sorted(HOLIDAYS_2028):
        assert svc.calc_days(day, day) == 0, day


@pytest.mark.parametrize("start, end, days", [
    (D(2028, 5, 1), D(2028, 5, 5), 3),     # 1 Mayıs + Kurban Bayramı 1. gün (Cuma)
    (D(2028, 2, 28), D(2028, 3, 3), 4),    # Ramazan Bayramı 3. gün (Pazartesi)
    (D(2028, 8, 28), D(2028, 9, 1), 4),    # 30 Ağustos (Çarşamba)
    (D(2028, 5, 8), D(2028, 5, 8), 0),     # Kurban Bayramı 4. gün (Pazartesi)
])
def test_count_2028_ranges(svc, start, end, days):
    assert svc.calc_days(start, end) == days


# --- CB-2 -----------------------------------------------------------------------------------

@pytest.mark.parametrize("day, days", [
    (D(2028, 2, 25), 1),    # Ramazan arifesi, Cuma: tam iş günü
    (D(2028, 5, 4), 1),     # Kurban arifesi, Perşembe: tam iş günü
    (D(2028, 10, 28), 0),   # 29 Ekim arifesi, Cumartesi
])
def test_2028_arife_days(svc, day, days):
    assert svc.calc_days(day, day) == days


# --- CB-3 -----------------------------------------------------------------------------------

def test_2029_is_outside_list(svc):
    assert svc.calc_days(D(2029, 1, 1), D(2029, 1, 1)) == 1   # Pazartesi, liste dışı yıl


# --- CB-4 -----------------------------------------------------------------------------------

@pytest.mark.parametrize("pending_workdays, saved", [(10, True), (11, False)],
                         ids=["available-3-saved", "available-2-refused"])
def test_request_counts_2028_holidays(client, svc, pending_workdays, saved):
    """Zeynep (id 3): Kalan 14, Bekleyen 1. A pending request of 10 (11) working days in
    16–30 Nov 2026 (no holiday) leaves 3 (2) available; 1–5 May 2028 is 3 working days."""
    def add_pending():
        start = D(2026, 11, 16)
        leave_app.storage.add_request({"id": 9, "employee_id": 3, "start": start,
                                       "end": end_after_workdays(start, pending_workdays),
                                       "reason": "x", "status": "Beklemede"})

    add_pending()
    resp = client.post("/new", data={"employee_id": "3", "start": "2028-05-01",
                                     "end": "2028-05-05", "reason": "Bayram"})
    if saved:
        assert resp.status_code == 302
        rows = table_rows(client.get("/requests").get_data(as_text=True))[1:]
        assert rows[-1][1:5] == ["2028-05-01", "2028-05-05", "3", "Bayram"]
        assert len(leave_app.storage.requests()) == 10
    else:
        assert resp.status_code == 400
        text = visible_text(resp.get_data(as_text=True))
        assert "Kalan izin bakiyeniz yetersiz (kalan 14 gün, bekleyen 12 gün, talep 3 gün)." in text
        assert len(leave_app.storage.requests()) == 9

    leave_app.storage.reset()
    add_pending()
    try:
        service_saved = svc.create_request(3, D(2028, 5, 1), D(2028, 5, 5), "x") is True
    except InsufficientBalance:
        service_saved = False
    assert service_saved is saved


# --- PB-2 -----------------------------------------------------------------------------------

@pytest.mark.parametrize("start, end, days", [
    (D(2025, 1, 1), D(2025, 1, 1), 1),     # liste öncesi yıl, Çarşamba
    (D(2028, 1, 3), D(2028, 1, 7), 5),     # 2028'in tatilsiz haftası
])
def test_years_before_list_and_holiday_free_week(svc, start, end, days):
    assert svc.calc_days(start, end) == days
