"""Failed leave requests are reported, never shown as success — spec 0008.

Service tests pin the domain contract (typed exceptions, S-4 order); screen tests pin what the
user sees (message, status code, no redirect, no record).
"""
import datetime as dt

import pytest

import app as leave_app
from conftest import end_after_workdays, visible_text
from domain.errors import EmployeeNotFound, InsufficientBalance, InvalidDateRange

MSG_INVALID_INPUT = "Lütfen personeli ve geçerli başlangıç ve bitiş tarihlerini girin."
MSG_INVALID_DATE_RANGE = "Bitiş tarihi başlangıç tarihinden önce olamaz."
MSG_UNEXPECTED = "Talep kaydedilemedi. Lütfen daha sonra tekrar deneyin."


def by_name(name):
    return next(e for e in leave_app.storage.employees() if e["name"] == name)


def assert_shown_not_saved(resp, status, message):
    """A failed request: message above the form, no redirect, no new record."""
    assert resp.status_code == status
    html = resp.get_data(as_text=True)
    assert message in visible_text(html)
    assert "Kaydet" in html
    assert html.index(message) < html.index("<form")
    assert len(leave_app.storage.requests()) == 8


# --- service (CB-1, CB-3, CB-6) -------------------------------------------------------------

def test_insufficient_balance_carries_remaining_and_requested(svc):
    """CB-1/CB-6 (S-2): Elif, kalan 0, 1 günlük talep."""
    elif_ = by_name("Elif Sahin")
    with pytest.raises(InsufficientBalance) as err:
        svc.create_request(elif_["id"], dt.date(2026, 11, 16), dt.date(2026, 11, 16), "x")
    assert (err.value.remaining, err.value.requested) == (0, 1)
    assert len(leave_app.storage.requests()) == 8


def test_end_before_start_raises_invalid_date_range(svc):
    """CB-3 (BR-9): bitiş başlangıçtan önceyse kayıt oluşmaz."""
    mehmet = by_name("Mehmet Demir")
    with pytest.raises(InvalidDateRange):
        svc.create_request(mehmet["id"], dt.date(2026, 11, 18), dt.date(2026, 11, 16), "x")
    assert len(leave_app.storage.requests()) == 8


def test_end_equal_to_start_is_one_day(svc):
    """CB-3: bitiş = başlangıç geçerlidir ve 1 gün sayılır."""
    mehmet = by_name("Mehmet Demir")
    assert svc.create_request(mehmet["id"], dt.date(2026, 11, 16), dt.date(2026, 11, 16), "x") is True
    saved = leave_app.storage.requests()[-1]
    assert svc.calc_days(saved["start"], saved["end"]) == 1


@pytest.mark.parametrize(
    "name, expected",
    [("Yok", EmployeeNotFound), ("Elif Sahin", InvalidDateRange)],
    ids=["unknown-employee-before-date-range", "date-range-before-balance"],
)
def test_violations_are_reported_in_order(svc, name, expected):
    """CB-6 (S-4): personel -> tarih aralığı -> bakiye; yalnızca ilk ihlal bildirilir.
    Elif'in kalanı 0, yani tarih aralığı ters olmasa bakiye ihlali olurdu."""
    emp_id = 99 if name == "Yok" else by_name(name)["id"]
    with pytest.raises(expected):
        svc.create_request(emp_id, dt.date(2026, 11, 18), dt.date(2026, 11, 16), "x")


# --- screen (CB-1..CB-5) --------------------------------------------------------------------

@pytest.mark.parametrize("days, saved", [(12, True), (13, True), (14, False)])
def test_screen_and_service_agree_on_balance(client, svc, days, saved):
    """CB-1: Zeynep, kalan 14. Ekran ve servis aynı kararı verir. Spec 0013 K-2 (T6): bekleyen 1
    (#3), sınır kalan − bekleyen = 13 → 12, 13, 14."""
    start = dt.date(2026, 12, 1)
    end = end_after_workdays(start, days)  # 0014 T7: iş günü
    resp = client.post("/new", data={
        "employee_id": "3", "start": start.isoformat(), "end": end.isoformat(), "reason": "x"})
    if saved:
        assert resp.status_code == 302
    else:
        assert_shown_not_saved(resp, 400, "Kalan izin bakiyeniz yetersiz (kalan 14 gün, bekleyen 1 gün, talep 14 gün).")
    leave_app.storage.reset()
    try:
        service_saved = svc.create_request(3, start, end, "x") is True
    except InsufficientBalance:
        service_saved = False
    assert service_saved is saved


def test_screen_unknown_employee_shows_message(client):
    """CB-2: olmayan personel → mesaj formun üstünde, 400."""
    resp = client.post("/new", data={
        "employee_id": "99", "start": "2026-11-16", "end": "2026-11-18", "reason": "x"})
    assert_shown_not_saved(resp, 400, "Seçilen personel bulunamadı.")


def test_screen_end_before_start_shows_message(client):
    """CB-3 (BR-9): ters tarih → mesaj, 400."""
    resp = client.post("/new", data={
        "employee_id": "2", "start": "2026-11-18", "end": "2026-11-16", "reason": "x"})
    assert_shown_not_saved(resp, 400, MSG_INVALID_DATE_RANGE)


@pytest.mark.parametrize(
    "form",
    [
        {"employee_id": "2", "start": "", "end": "2026-11-16"},
        {"employee_id": "iki", "start": "2026-11-16", "end": "2026-11-16"},
        {"start": "2026-11-16", "end": "2026-11-16"},
        {"employee_id": "99", "start": "16.11.2026", "end": "2026-11-16"},
    ],
    ids=["empty-date", "non-numeric-employee", "missing-employee", "bad-date-before-unknown-employee"],
)
def test_screen_bad_input_shows_message(client, form):
    """CB-4 ve S-4 (bozuk girdi önce gelir): mesaj, 400."""
    resp = client.post("/new", data={**form, "reason": "x"})
    assert_shown_not_saved(resp, 400, MSG_INVALID_INPUT)


def test_screen_unexpected_error_is_logged_not_shown(client, monkeypatch, caplog):
    """CB-5: genel mesaj, 500; ayrıntı sayfada yok, stack trace logda."""
    def broken(record):
        raise RuntimeError("gizli ayrinti")
    monkeypatch.setattr(leave_app.storage, "add_request", broken)
    resp = client.post("/new", data={
        "employee_id": "2", "start": "2026-11-16", "end": "2026-11-16", "reason": "x"})
    assert_shown_not_saved(resp, 500, MSG_UNEXPECTED)
    html = resp.get_data(as_text=True)
    assert "gizli ayrinti" not in html
    assert "Traceback" not in html
    errors = [r for r in caplog.records if r.levelname == "ERROR"]
    assert len(errors) == 1
    assert errors[0].exc_info[0] is RuntimeError
