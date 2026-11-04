"""Baseline (characterization) tests for the three screens — spec 0001, AC-7..AC-10.

Assertions target what the user sees (texts, numbers, table cells), not exact markup (spec R-5).
Tests named ``*_current`` pin CURRENT behavior that is known not to be the target rule.
"""
from html.parser import HTMLParser

import pytest

from conftest import table_rows, visible_text

REQUESTS_HEADER = ["Personel", "Baslangic", "Bitis", "Gun", "Neden", "Durum"]
OPENING_REQUESTS = [
    ["Ayse Yilmaz", "2026-07-06", "2026-07-17", "12", "Yaz tatili", "Onaylandi"],
    ["Mehmet Demir", "2026-11-02", "2026-11-04", "3", "Aile ziyareti", "Beklemede"],
    ["Zeynep Kaya", "2026-11-09", "2026-11-09", "1", "Saglik", "Beklemede"],
    ["Ahmet Celik", "2026-12-21", "2026-12-25", "5", "Yilbasi oncesi", "Beklemede"],
    ["Ayse Yilmaz", "2026-12-28", "2026-12-30", "3", "Yil sonu", "Beklemede"],
    ["Elif Sahin", "2026-10-05", "2026-10-07", "3", "Tasinma", "Reddedildi"],
    ["Zeynep Kaya", "2026-09-14", "2026-09-25", "12", "Uzun tatil", "Reddedildi"],
    ["Mehmet Demir", "2026-08-03", "2026-08-03", "1", "Ozel is", "Reddedildi"],
]


def request_rows(client):
    rows = table_rows(client.get("/requests").get_data(as_text=True))
    assert rows[0] == REQUESTS_HEADER
    return rows[1:]


def post_new(client, employee_id, start, end, reason="Test"):
    return client.post("/new", data={
        "employee_id": str(employee_id), "start": start, "end": end, "reason": reason,
    })


def assert_redirects_to_requests(resp):
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/requests")


# --- AC-7 -----------------------------------------------------------------------------------

def test_dashboard_counts_and_balances(client):
    """AC-7: sayaçlar ve personel bakiyeleri."""
    html = client.get("/").get_data(as_text=True)
    text = visible_text(html)
    assert "Bekleyen: 4" in text
    assert "Onaylanan: 1" in text
    assert "Reddedilen: 3" in text
    assert table_rows(html) == [
        ["Ad", "Birim", "Hak", "Kullanilan", "Kalan"],
        ["Ayse Yilmaz", "IT", "26", "12", "14"],
        ["Mehmet Demir", "Muhasebe", "20", "0", "20"],
        ["Zeynep Kaya", "IK", "14", "0", "14"],
        ["Ahmet Celik", "IT", "20", "0", "20"],
        ["Elif Sahin", "Satis", "0", "0", "0"],
    ]


# --- AC-8 -----------------------------------------------------------------------------------

def test_requests_list_shows_all_requests_in_order(client):
    """AC-8: açılış verisindeki 8 talep, kayıt sırasıyla."""
    assert request_rows(client) == OPENING_REQUESTS


# --- AC-9 -----------------------------------------------------------------------------------

class _FormFields(HTMLParser):
    def __init__(self):
        super().__init__()
        self.options = []
        self.inputs = []
        self._option = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "option":
            self._option = [attrs.get("value"), ""]
        elif tag == "input":
            self.inputs.append(attrs)

    def handle_data(self, data):
        if self._option is not None:
            self._option[1] += data

    def handle_endtag(self, tag):
        if tag == "option" and self._option is not None:
            self.options.append(tuple(self._option))
            self._option = None


def test_new_request_form_fields(client):
    """AC-9: personel seçenekleri, tarih ve neden alanları, Kaydet düğmesi."""
    form = _FormFields()
    form.feed(client.get("/new").get_data(as_text=True))
    assert form.options == [
        ("1", "Ayse Yilmaz"), ("2", "Mehmet Demir"), ("3", "Zeynep Kaya"),
        ("4", "Ahmet Celik"), ("5", "Elif Sahin"),
    ]
    named = {i.get("name"): i.get("type") for i in form.inputs if i.get("name")}
    assert named == {"start": "date", "end": "date", "reason": "text"}
    assert any(i.get("type") == "submit" and i.get("value") == "Kaydet" for i in form.inputs)


# --- AC-10 ----------------------------------------------------------------------------------

def test_post_valid_request_is_listed_as_pending(client):
    """AC-10: geçerli talep → talepler ekranına yönlendirir, yeni satır Beklemede."""
    resp = post_new(client, 2, "2026-11-16", "2026-11-18", "Tatil")
    assert_redirects_to_requests(resp)
    rows = request_rows(client)
    assert rows[:8] == OPENING_REQUESTS
    assert rows[8:] == [["Mehmet Demir", "2026-11-16", "2026-11-18", "3", "Tatil", "Beklemede"]]


def test_post_insufficient_balance_shows_error(client):
    """AC-10: kalan < gün → hata mesajı, kayıt yok."""
    resp = post_new(client, 5, "2026-11-16", "2026-11-16")  # Elif: kalan 0
    assert resp.status_code == 200
    text = visible_text(resp.get_data(as_text=True))
    assert "ERR-412" in text
    assert "bakiye yetersiz" in text
    assert request_rows(client) == OPENING_REQUESTS


def test_post_remaining_equals_days_is_saved(client):
    """Spec 0008 CB-1 (BR-6 kararı; supersedes 0001/AC-10): bakiyeyi tam kullanan talep kaydedilir."""
    resp = post_new(client, 3, "2026-12-01", "2026-12-14")  # Zeynep: kalan 14, 14 gün
    assert_redirects_to_requests(resp)
    assert request_rows(client)[8:] == [
        ["Zeynep Kaya", "2026-12-01", "2026-12-14", "14", "Test", "Beklemede"],
    ]


@pytest.mark.parametrize(
    "employee_id, start, end",
    [
        (2, "16.11.2026", "18.11.2026"),  # bozuk tarih formatı
        (99, "2026-11-16", "2026-11-18"),  # olmayan personel
    ],
    ids=["bad-date", "unknown-employee"],
)
def test_post_invalid_input_redirects_without_saving_current(client, employee_id, start, end):
    """MEVCUT DAVRANIŞ — hedef değil (invariant: talep var olan personele bağlı; başarısız işlem
    başarılı gösterilmez · OD-7) · AC-10: hata yutulur, yönlendirir, kayıt oluşmaz."""
    resp = post_new(client, employee_id, start, end)
    assert_redirects_to_requests(resp)
    assert request_rows(client) == OPENING_REQUESTS


def test_post_empty_reason_is_saved(client):
    """AC-10: neden boş bırakılmış geçerli talep yine kaydedilir."""
    resp = post_new(client, 4, "2026-11-23", "2026-11-23", reason="")
    assert_redirects_to_requests(resp)
    assert request_rows(client)[8:] == [
        ["Ahmet Celik", "2026-11-23", "2026-11-23", "1", "", "Beklemede"],
    ]
