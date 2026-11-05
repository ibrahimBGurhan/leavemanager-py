"""Leave days are working days — spec 0014 (OD-4).

Mon-Fri count, Saturday and Sunday do not, nor do the 2026-2027 public holidays (K-2). Arife
half days count as full working days (K-3). A request with no working day is refused (K-5).
Opening data, today = 2026-10-23 (conftest).
"""
import datetime as dt
import time

import pytest

import app as leave_app
from conftest import end_after_workdays, table_rows, visible_text
from domain.errors import EmployeeNotFound, InsufficientBalance, InvalidDateRange, NoWorkingDays

D = dt.date
MSG_NO_WORKING_DAYS = "Seçilen tarihler arasında iş günü yok."
K2_HOLIDAYS = {
    D(2026, 1, 1), D(2026, 4, 23), D(2026, 5, 1), D(2026, 5, 19), D(2026, 7, 15),
    D(2026, 8, 30), D(2026, 10, 29),
    D(2026, 3, 20), D(2026, 3, 21), D(2026, 3, 22),
    D(2026, 5, 27), D(2026, 5, 28), D(2026, 5, 29), D(2026, 5, 30),
    D(2027, 1, 1), D(2027, 4, 23), D(2027, 5, 1), D(2027, 5, 19), D(2027, 7, 15),
    D(2027, 8, 30), D(2027, 10, 29),
    D(2027, 3, 9), D(2027, 3, 10), D(2027, 3, 11),
    D(2027, 5, 16), D(2027, 5, 17), D(2027, 5, 18),
}


def post_new(client, emp_id, start, end):
    return client.post("/new", data={"employee_id": str(emp_id), "start": start.isoformat(),
                                     "end": end.isoformat(), "reason": "x"})


def assert_refused(resp, message):
    assert resp.status_code == 400
    html = resp.get_data(as_text=True)
    text = visible_text(html)
    assert message in text
    assert html.index(message) < html.index("<form")
    for leak in ("ERR-", "NoWorkingDays", "Traceback"):
        assert leak not in text
    assert len(leave_app.storage.requests()) == 8


# --- CB-1 -----------------------------------------------------------------------------------

@pytest.mark.parametrize("start, end, days", [
    (D(2026, 11, 16), D(2026, 11, 20), 5),   # Pzt–Cum
    (D(2026, 11, 13), D(2026, 11, 16), 2),   # Cum–Pzt: hafta sonu sayılmaz
    (D(2026, 10, 26), D(2026, 10, 30), 4),   # 29 Ekim
    (D(2026, 12, 28), D(2027, 1, 1), 4),     # 1 Ocak, yıl geçişi
    (D(2027, 3, 8), D(2027, 3, 12), 2),      # arife (tam gün, K-3) + bayram 9–11 Mart + Cuma
    (D(2026, 7, 6), D(2026, 7, 17), 9),      # açılış #1: iki hafta sonu + 15 Temmuz
    (D(2026, 11, 9), D(2026, 11, 9), 1),     # tek iş günü
    (D(2026, 11, 14), D(2026, 11, 15), 0),   # Cmt–Pzr
    (D(2026, 10, 29), D(2026, 10, 29), 0),   # yalnız tatil
    (D(2026, 5, 30), D(2026, 5, 30), 0),     # Cumartesiye denk gelen bayram günü
    (D(2026, 11, 2), D(2026, 11, 1), 0),     # ters aralık (BR-9 önce yakalar)
    (D(2028, 1, 3), D(2028, 1, 7), 5),       # liste dışı yıl: yalnız hafta sonu (K-4)
])
def test_count_workdays(svc, start, end, days):
    assert svc.calc_days(start, end) == days


def test_holidays_list_matches_k2():
    from domain.workdays import HOLIDAYS
    assert set(HOLIDAYS) == K2_HOLIDAYS


def test_no_holiday_is_counted(svc):
    for day in sorted(K2_HOLIDAYS):
        assert svc.calc_days(day, day) == 0


def test_arife_days_count_as_full_days(svc):
    """K-3: 19 Mar 2026, 26 May 2026, 28 Oct 2026/2027, 8 Mar 2027 are weekdays → 1 each."""
    for day in (D(2026, 3, 19), D(2026, 5, 26), D(2026, 10, 28), D(2027, 10, 28), D(2027, 3, 8)):
        assert svc.calc_days(day, day) == 1


def test_long_range_is_fast(svc):
    """S-1: the count does not walk the range day by day."""
    begin = time.perf_counter()
    days = svc.calc_days(D(2026, 1, 1), D(9999, 12, 31))
    assert time.perf_counter() - begin < 0.5
    weekdays_in_2026_2027 = 261 + 261
    weekday_holidays = sum(1 for h in K2_HOLIDAYS if h.weekday() < 5)
    assert days > 2_000_000
    assert svc.calc_days(D(2026, 1, 1), D(2027, 12, 31)) == weekdays_in_2026_2027 - weekday_holidays


# --- CB-2 -----------------------------------------------------------------------------------

@pytest.mark.parametrize("start, end", [(D(2026, 11, 14), D(2026, 11, 15)),
                                        (D(2026, 10, 29), D(2026, 10, 29))],
                         ids=["weekend", "holiday"])
def test_no_working_days_refused(client, svc, start, end):
    assert_refused(post_new(client, 2, start, end), MSG_NO_WORKING_DAYS)
    with pytest.raises(NoWorkingDays):
        svc.create_request(2, start, end, "x")
    assert len(leave_app.storage.requests()) == 8


def test_order_date_range_before_no_working_days(svc):
    with pytest.raises(InvalidDateRange):
        svc.create_request(2, D(2026, 11, 15), D(2026, 11, 14), "x")


def test_order_employee_before_no_working_days(svc):
    with pytest.raises(EmployeeNotFound):
        svc.create_request(99, D(2026, 11, 14), D(2026, 11, 15), "x")


def test_no_working_days_before_balance(client, svc):
    """K-5 order (review F-1): with a negative available balance (Zeynep: Kalan 14, Bekleyen 15,
    pre-0013 data) a weekend-only request reports no working days, not the balance."""
    start = D(2026, 11, 16)
    leave_app.storage.add_request({"id": 9, "employee_id": 3, "start": start,
                                   "end": end_after_workdays(start, 14), "reason": "x",
                                   "status": "Beklemede"})
    assert svc.get_pending_days(3) == 15
    with pytest.raises(NoWorkingDays):
        svc.create_request(3, D(2026, 11, 14), D(2026, 11, 15), "x")
    resp = post_new(client, 3, D(2026, 11, 14), D(2026, 11, 15))
    assert resp.status_code == 400
    text = visible_text(resp.get_data(as_text=True))
    assert MSG_NO_WORKING_DAYS in text
    assert "bakiyeniz yetersiz" not in text
    assert len(leave_app.storage.requests()) == 9


# --- CB-3 -----------------------------------------------------------------------------------

def test_screens_show_working_days(client):
    requests = table_rows(client.get("/requests").get_data(as_text=True))[1:]
    assert [row[3] for row in requests] == ["9", "3", "1", "5", "3", "3", "10", "1"]
    balances = table_rows(client.get("/").get_data(as_text=True))[1:]
    assert balances[0] == ["Ayse Yilmaz", "IT", "26", "9", "17", "3"]
    assert [row[2:] for row in balances[1:]] == [
        ["20", "0", "20", "3"], ["14", "0", "14", "1"], ["20", "0", "20", "5"], ["0", "0", "0", "0"],
    ]


# --- CB-4 -----------------------------------------------------------------------------------

@pytest.mark.parametrize("end, saved", [(D(2026, 12, 17), True), (D(2026, 12, 18), False)],
                         ids=["13-workdays", "14-workdays"])
def test_balance_counts_working_days(client, svc, end, saved):
    """Zeynep: Kalan 14, Bekleyen 1 → 13 working days available; 1–17 Dec = 13, 1–18 Dec = 14."""
    resp = post_new(client, 3, D(2026, 12, 1), end)
    if saved:
        assert resp.status_code == 302
    else:
        assert_refused(resp, "Kalan izin bakiyeniz yetersiz (kalan 14 gün, bekleyen 1 gün, talep 14 gün).")
    leave_app.storage.reset()
    try:
        service_saved = svc.create_request(3, D(2026, 12, 1), end, "x") is True
    except InsufficientBalance:
        service_saved = False
    assert service_saved is saved


def test_approval_counts_working_days(svc):
    """A pending request over a weekend uses only its working days on approval: Mehmet (Kalan 20)
    approves a 21-calendar-day / 15-working-day request, Kalan 20 → 5."""
    mehmet = next(e for e in leave_app.storage.employees() if e["name"] == "Mehmet Demir")
    request_id = leave_app.storage.next_request_id()
    leave_app.storage.add_request({"id": request_id, "employee_id": mehmet["id"],
                                   "start": D(2026, 11, 16), "end": D(2026, 12, 6),
                                   "reason": "x", "status": "Beklemede"})
    svc.approve_request(request_id)
    assert svc.get_remaining(mehmet) == 5
