# Is kurallari: kidem, hak, kullanilan, kalan, talep olusturma, durum gecisleri (docs/domain.md).
# Saat ve depo disaridan verilir; bu katman Flask'i, HTML'i ve gercek saati bilmez.
import calendar
import logging
from datetime import date

from domain.access import AccountView
from domain.errors import (BeforeOpeningBalance, EmployeeNotFound, InsufficientBalance,
                           InvalidDateRange, InvalidEmployee, InvalidOpeningBalance,
                           NoWorkingDays, RequestAlreadyDecided, RequestNotFound)
from domain.leave_year import (last_anniversary, next_anniversary, rights_born, tier)
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
# Acilis bakiyesi gun siniri (spec 0041 K-1)
MAX_OPENING_DAYS = 365


def _log_safe(text):
    # Yazdirilamayan karakterler (CR, LF, sekme, U+2028 ...) Python kacisiyla tek satirda kalir;
    # yazdirilabilir metin (Turkce harfler dahil) degismez
    return "".join(c if c.isprintable() else repr(c)[1:-1] for c in text)


class LeaveService:

    def __init__(self, clock, storage):
        self._clock = clock
        self._storage = storage

    # Kidem -> hak edilen izin (BR-1, Is Kanunu md. 53): 0 -> 0, 1-5 -> 14, 6-14 -> 20,
    # 15 ve uzeri -> 26 gun (OD-1, spec 0038)
    def get_entitlement(self, emp):
        return tier(self.get_seniority_years(emp))

    def get_seniority_years(self, emp):
        # Kidem = tamamlanmis hizmet yili; yil donumu gunu yili tamamlar. 29 Subat'ta ise girenin
        # yil donumu artik olmayan yillarda 28 Subat. Ise giris bugunden sonraysa 0 (BR-2, OD-2,
        # spec 0038)
        today = self._clock.today()
        hire = emp["hire_date"]
        anniversary = (hire.month, hire.day)
        if anniversary == (2, 29) and not calendar.isleap(today.year):
            anniversary = (2, 28)
        years = today.year - hire.year - ((today.month, today.day) < anniversary)
        return max(years, 0)

    # --- Izin yili ve bakiye (spec 0040 K-8, K-9; OD-11). Kullanilmayan izin yanmaz (K-3) ------

    def _opening(self, emp_id):
        # Acilis bakiyesi (K-9): personel basina en fazla bir kayit; yoksa None
        return next((o for o in self._storage.opening_balances()
                     if o["employee_id"] == emp_id), None)

    def opening_balance(self, emp_id):
        # Personelin acilis bakiyesi kaydi (spec 0041); yoksa None
        return self._opening(emp_id)

    def pending_before_opening(self, emp_id):
        # Acilis tarihinden once baslayan bekleyen taleplerin numaralari (spec 0041 K-4, G-2)
        opening = self._opening(emp_id)
        if opening is None:
            return []
        return [r["id"] for r in self._storage.requests()
                if r["employee_id"] == emp_id and r["status"] == PENDING
                and r["start"] < opening["date"]]

    def set_opening_balance(self, employee_id, on, days, set_by=None):
        """Acilis bakiyesi (spec 0041 K-1, K-9). Ihlal sirasi personel -> tarih -> gun; ilk ihlal
        InvalidOpeningBalance olur. employee_id None ise personel secilmemistir; bir personele
        eslesmeyen her deger (bozuk metin dahil) "bulunamadi". on None ise tarih gecersizdir, days
        None ise gun gecersizdir (web ayristiramadigini None gecer). Ayni personelde kayit
        yerine gecer. Kaydi doner."""
        if employee_id is None:
            raise InvalidOpeningBalance("employee-missing")
        emp = next((e for e in self._storage.employees() if e["id"] == employee_id), None)
        if emp is None:
            raise InvalidOpeningBalance("employee-not-found")
        if not isinstance(on, date):
            raise InvalidOpeningBalance("date-invalid")
        if on < emp["hire_date"]:
            raise InvalidOpeningBalance("date-before-hire", emp["hire_date"])
        if on > self._clock.today():
            raise InvalidOpeningBalance("date-in-future")
        if (not isinstance(days, int) or isinstance(days, bool)
                or not 0 <= days <= MAX_OPENING_DAYS):
            raise InvalidOpeningBalance("days-invalid")
        record = {"employee_id": emp["id"], "date": on, "days": days}
        self._storage.set_opening_balance(record)
        # Ad, tarih ve gun yazilmaz (spec 0041 K-8); giren "<e-posta> (<rol>)"
        logger.info("acilis bakiyesi: #%d, giren: %s", emp["id"], set_by)
        return record

    def _approved_days(self, emp_id, since):
        # Baslangici since ya da sonrasinda olan onayli taleplerin izin gunu (since None: hepsi)
        total = 0
        for r in self._storage.requests():
            if (r["employee_id"] == emp_id and r["status"] == APPROVED
                    and (since is None or r["start"] >= since)):
                total += self.calc_days(r["start"], r["end"])
        return total

    def _used_since(self, emp):
        # Kullanilan'in baslangici: son yil donumu; acilis tarihi daha sonraysa o (K-8, K-9)
        last = last_anniversary(emp["hire_date"], self._clock.today())
        opening = self._opening(emp["id"])
        if opening is None:
            return last
        return opening["date"] if last is None else max(last, opening["date"])

    def get_this_year_right(self, emp):
        # Son yil donumunde dogan hak; ilk yil dolmadiysa ya da acilis bakiyesinin icindeyse 0
        hire = emp["hire_date"]
        last = last_anniversary(hire, self._clock.today())
        opening = self._opening(emp["id"])
        if last is None or (opening is not None and last <= opening["date"]):
            return 0
        return tier(last.year - hire.year)

    def get_used_days(self, emp_id):
        # Kullanilan: baslangici bu izin yilinda (ya da sonra) olan onayli talepler (K-5, K-8)
        emp = next((e for e in self._storage.employees() if e["id"] == emp_id), None)
        if emp is None:
            return 0
        return self._approved_days(emp_id, self._used_since(emp))

    def get_carried(self, emp):
        # Devreden: onceki izin yillarindan kalan = Kalan + Kullanilan - Bu yilin hakki (K-8)
        return (self.get_remaining(emp) + self.get_used_days(emp["id"])
                - self.get_this_year_right(emp))

    def get_next_right_date(self, emp):
        return next_anniversary(emp["hire_date"], self._clock.today())

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
        # Kalan = bugune kadar dogmus haklar - onayli talepler (K-8). Acilis bakiyesi varsa (K-9):
        # bakiye + acilistan sonraki yil donumlerinde doganlar - acilistan itibaren baslayanlar.
        # Bekleyenler burada dusulmez, yeni talepte sayilir (OD-3, 0013); tek hesap (R-2).
        today = self._clock.today()
        opening = self._opening(emp["id"])
        if opening is None:
            return (rights_born(emp["hire_date"], None, today)
                    - self._approved_days(emp["id"], None))
        return (opening["days"] + rights_born(emp["hire_date"], opening["date"], today)
                - self._approved_days(emp["id"], opening["date"]))

    def create_request(self, emp_id, start, end, reason):
        # Ihlal sirasi: personel -> tarih araligi -> acilis oncesi -> is gunu yok -> bakiye
        # (0008 S-4, 0014 K-5, 0041 K-6)
        emp = None
        for e in self._storage.employees():
            if e["id"] == emp_id:
                emp = e
        if emp is None:
            raise EmployeeNotFound(emp_id)
        if end < start:
            raise InvalidDateRange(start, end)  # BR-9
        opening = self._opening(emp_id)
        if opening is not None and start < opening["date"]:
            # Acilis oncesi donem acilis bakiyesinin icinde: yeni talep olmaz (spec 0041 K-6)
            raise BeforeOpeningBalance(opening["date"])
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
        opening = self._opening(emp["id"])
        if opening is None or r["start"] >= opening["date"]:
            # Acilis tarihinden once baslayan talep bakiyeden dusmez; onayda kontrol yok
            # (spec 0041 K-5). Digerleri BR-10.
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
        # Ad ve ise giris tarihi yazilmaz (KVKK, R-8). Birim kullanicinin yazdigi metin: kontrol
        # karakterleri kacislanir, log'a sahte satir yazilamaz (review 0022 F-1)
        logger.info("personel eklendi: #%d (%s), ekleyen: %s", record["id"],
                    _log_safe(department), added_by)
        return record

    def for_account(self, account):
        # Web veriye ve islemlere yalniz bu gorunumle ulasir; yetki kurali orada (spec 0020)
        return AccountView(self, account)

    # Salt okuma: web veriye yalniz servis uzerinden erisir (docs/architecture.md)
    def employees(self):
        return self._storage.employees()

    def requests(self):
        return self._storage.requests()
