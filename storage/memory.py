# Kalicilik: bugun bellekte, sonra SQL'e gecilecek (2016). SQL gelince yalniz bu katman degisir.
from datetime import date


def _opening_employees():
    return [
        {"id": 1, "name": "Ayse Yilmaz",  "department": "IT",       "hire_date": date(2008, 3, 15)},
        {"id": 2, "name": "Mehmet Demir", "department": "Muhasebe", "hire_date": date(2019, 6, 1)},
        {"id": 3, "name": "Zeynep Kaya",  "department": "IK",       "hire_date": date(2024, 11, 10)},
        {"id": 4, "name": "Ahmet Celik",  "department": "IT",       "hire_date": date(2020, 2, 29)},  # artik yil - dikkat
        {"id": 5, "name": "Elif Sahin",   "department": "Satis",    "hire_date": date(2026, 6, 1)},
    ]


def _opening_requests():
    return [
        {"id": 1, "employee_id": 1, "start": date(2026, 7, 6),  "end": date(2026, 7, 17), "reason": "Yaz tatili",      "status": "Onaylandi"},
        {"id": 2, "employee_id": 2, "start": date(2026, 11, 2), "end": date(2026, 11, 4), "reason": "Aile ziyareti",   "status": "Beklemede"},
        {"id": 3, "employee_id": 3, "start": date(2026, 11, 9), "end": date(2026, 11, 9), "reason": "Saglik",          "status": "Beklemede"},
        {"id": 4, "employee_id": 4, "start": date(2026, 12, 21),"end": date(2026, 12, 25),"reason": "Yilbasi oncesi",  "status": "Beklemede"},
        {"id": 5, "employee_id": 1, "start": date(2026, 12, 28),"end": date(2026, 12, 30),"reason": "Yil sonu",        "status": "Beklemede"},
        {"id": 6, "employee_id": 5, "start": date(2026, 10, 5), "end": date(2026, 10, 7), "reason": "Tasinma",         "status": "Reddedildi"},
        {"id": 7, "employee_id": 3, "start": date(2026, 9, 14), "end": date(2026, 9, 25), "reason": "Uzun tatil",      "status": "Reddedildi"},
        {"id": 8, "employee_id": 2, "start": date(2026, 8, 3),  "end": date(2026, 8, 3),  "reason": "Ozel is",         "status": "Reddedildi"},
    ]


class MemoryStorage:
    # Kayitlar sozluk: personel {id, name, department, hire_date};
    # talep {id, employee_id, start, end, reason, status}
    def __init__(self):
        self.reset()

    def employees(self):
        return self._employees

    def requests(self):
        return self._requests

    def add_employee(self, record):
        self._employees.append(record)

    def add_request(self, record):
        # sayaca dokunmaz; yeni numarayi next_request_id verir
        self._requests.append(record)

    def set_request_status(self, request_id, status):
        # is kurali bilmez; gecis karari domain'de verilir (spec 0010)
        for r in self._requests:
            if r["id"] == request_id:
                r["status"] = status

    def next_request_id(self):
        request_id = self._next_id
        self._next_id += 1
        return request_id

    def reset(self):
        # acilis verisi
        self._employees = _opening_employees()
        self._requests = _opening_requests()
        self._next_id = 9
