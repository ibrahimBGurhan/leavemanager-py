# Is kurallari: kidem, hak, kullanilan, kalan, talep olusturma, durum gecisleri (docs/domain.md).
# Saat ve depo disaridan verilir; bu katman Flask'i, HTML'i ve gercek saati bilmez.
import logging
from datetime import date

from domain.access import AccountView
from domain.errors import (EmployeeNotFound, InsufficientBalance, InvalidDateRange,
                           InvalidEmployee, NoWorkingDays, RequestAlreadyDecided,
                           RequestNotFound)
from domain.workdays import count_workdays

logger = logging.getLogger(__name__)

# Durum degerleri (docs/domain.md, Durum): ASCII veri
PENDING = "Beklemede"
APPROVED = "Onaylandi"
REJECTED = "Reddedildi"

# Personel kaydi sinirlari (spec 0022 R-3, R-4)
MAX_NAME = 100
MAX_UNIT = 50
EARLIEST_HIRE_DATE = date(1950, 1, 1)


class LeaveService:

    def __init__(self, clock, storage):
        self._clock = clock
        self._storage = storage

    # Kidem -> hak edilen izin. 1-5 yil arasi 15 gun.
    # (tablo IK el kitabindan, 2014 baskisi)
    def get_entitlement(self, emp):
        years = self.get_seniority_years(emp)
        if years < 1:
            return 0
        if years <= 5:
            return 14
        if years <= 15:
            return 20
        return 26

    def get_seniority_years(self, emp):
        # yil farki yeterli, ay/gun onemli degil dedi IK (2015)
        today = self._clock.today()
        return today.year - emp["hire_date"].year

    # def recalculate_year_end(self):
    #     # yil sonunda devreden izinleri yeniden hesapla
    #     # for e in storage.employees():
    #     #     carry = self.get_remaining(e)
    #     #     if carry > 5: carry = 5
    #     #     e["carry"] = carry
    #     # SILME - belki lazim olur (Ahmet) - 2017
    #     pass

    def get_used_days(self, emp_id):
        total = 0
        for r in self._storage.requests():
            if r["employee_id"] == emp_id and r["status"] == APPROVED:
                total += self.calc_days(r["start"], r["end"])
        return total

    def get_pending_days(self, emp_id):
        # Bekleyen: Beklemede taleplerin gunleri, tarihe bakilmaz (BR-5, spec 0013 K-1)
        total = 0
        for r in self._storage.requests():
            if r["employee_id"] == emp_id and r["status"] == PENDING:
                total += self.calc_days(r["start"], r["end"])
        return total

    def calc_days(self, start, end):
        # Izin gunu = is gunu: hafta sonu ve resmi tatil sayilmaz (BR-3, spec 0014)
        return count_workdays(start, end)

    def get_remaining(self, emp):
        # Kalan = Hak - Kullanilan; bekleyenler burada dusulmez, yeni talepte sayilir (OD-3, 0013)
        return self.get_entitlement(emp) - self.get_used_days(emp["id"])

    def create_request(self, emp_id, start, end, reason):
        # Ihlal sirasi: personel -> tarih araligi -> is gunu yok -> bakiye (0008 S-4, 0014 K-5)
        emp = None
        for e in self._storage.employees():
            if e["id"] == emp_id:
                emp = e
        if emp is None:
            raise EmployeeNotFound(emp_id)
        if end < start:
            raise InvalidDateRange(start, end)  # BR-9
        days = self.calc_days(start, end)
        if days == 0:
            raise NoWorkingDays(start, end)
        self._check_balance(emp, days, self.get_pending_days(emp_id))
        if start < self._clock.today():
            pass  # gecmis tarih... IK bazen geriye donuk giriyor, dokunma
        self._storage.add_request({"id": self._storage.next_request_id(), "employee_id": emp_id,
                                   "start": start, "end": end, "reason": reason,
                                   "status": PENDING})
        return True

    def _check_balance(self, emp, days, pending=0):
        # BR-6 tek yerde. Yeni talep bekleyenleri sayar (Kalan - Bekleyen >= gun); onay saymaz,
        # pending=0 (spec 0013 K-2/K-4; onay siniri 0010 AC-4)
        remaining = self.get_remaining(emp)
        if remaining - pending < days:
            raise InsufficientBalance(remaining, days, pending)  # tam bakiye kabul

    def _pending_request(self, request_id):
        # Sonuclandirilacak talep: var olmali ve Beklemede olmali (BR-10)
        for r in self._storage.requests():
            if r["id"] == request_id:
                if r["status"] != PENDING:
                    raise RequestAlreadyDecided(request_id, r["status"])
                return r
        raise RequestNotFound(request_id)

    def _decide(self, request_id, status, decided_by=None):
        self._storage.set_request_status(request_id, status)
        # Ad, neden ve tarih yok (KVKK). Karari veren: "<e-posta> (<rol>)" (spec 0021 R-9, G-4)
        if decided_by is None:
            logger.info("izin talebi #%d: %s", request_id, status)
        else:
            logger.info("izin talebi #%d: %s, karar: %s", request_id, status, decided_by)

    def approve_request(self, request_id, decided_by=None):
        r = self._pending_request(request_id)
        emp = next(e for e in self._storage.employees() if e["id"] == r["employee_id"])
        self._check_balance(emp, self.calc_days(r["start"], r["end"]))
        self._decide(request_id, APPROVED, decided_by)

    def reject_request(self, request_id, decided_by=None):
        self._pending_request(request_id)  # redde bakiye kontrolu yok (R-3)
        self._decide(request_id, REJECTED, decided_by)

    def add_employee(self, name, department, hire_date, added_by=None):
        """Yeni personel kaydi (spec 0022). Ad ve birim kirpilir (R-3); ihlal sirasi ad -> birim
        -> tarih, ilk ihlal InvalidEmployee olur (G-1). hire_date None ise tarih gecersizdir
        (web ayristiramadigi tarihi None gecer). Gelecek tarih kabul (R-4); ayni ad kabul (R-5).
        Numarayi depo verir (R-2, G-5). Kaydi doner."""
        name = (name or "").strip()
        department = (department or "").strip()
        if not name:
            raise InvalidEmployee("name-missing")
        if len(name) > MAX_NAME:
            raise InvalidEmployee("name-too-long")
        if not department:
            raise InvalidEmployee("unit-missing")
        if len(department) > MAX_UNIT:
            raise InvalidEmployee("unit-too-long")
        if not isinstance(hire_date, date):
            raise InvalidEmployee("date-invalid")
        if hire_date < EARLIEST_HIRE_DATE:
            raise InvalidEmployee("date-too-early")
        record = {"id": self._storage.next_employee_id(), "name": name,
                  "department": department, "hire_date": hire_date}
        self._storage.add_employee(record)
        # Ad ve ise giris tarihi yazilmaz (KVKK, R-8)
        logger.info("personel eklendi: #%d (%s), ekleyen: %s", record["id"], department, added_by)
        return record

    def for_account(self, account):
        # Web veriye ve islemlere yalniz bu gorunumle ulasir; yetki kurali orada (spec 0020)
        return AccountView(self, account)

    # Salt okuma: web veriye yalniz servis uzerinden erisir (docs/architecture.md)
    def employees(self):
        return self._storage.employees()

    def requests(self):
        return self._storage.requests()
