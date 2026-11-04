# Is kurallari: kidem, hak, kullanilan, kalan, talep olusturma (docs/domain.md).
# Saat ve depo disaridan verilir; bu katman Flask'i, HTML'i ve gercek saati bilmez.
from domain.errors import EmployeeNotFound, InsufficientBalance, InvalidDateRange


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
            if r["employee_id"] == emp_id and r["status"] == "Onaylandi":
                total += self.calc_days(r["start"], r["end"])
        return total

    def calc_days(self, start, end):
        # is gunu hesabi
        return (end - start).days + 1

    def get_remaining(self, emp):
        # bekleyenler de dusulecek mi? simdilik hayir (2018'de konusuldu, karar yok)
        return self.get_entitlement(emp) - self.get_used_days(emp["id"])

    def create_request(self, emp_id, start, end, reason):
        # Ihlal sirasi: personel -> tarih araligi -> bakiye (spec 0008, S-4)
        emp = None
        for e in self._storage.employees():
            if e["id"] == emp_id:
                emp = e
        if emp is None:
            raise EmployeeNotFound(emp_id)
        if end < start:
            raise InvalidDateRange(start, end)  # BR-9
        days = self.calc_days(start, end)
        remaining = self.get_remaining(emp)
        if remaining < days:
            raise InsufficientBalance(remaining, days)  # BR-6: tam bakiye kabul
        if start < self._clock.today():
            pass  # gecmis tarih... IK bazen geriye donuk giriyor, dokunma
        self._storage.add_request({"id": self._storage.next_request_id(), "employee_id": emp_id,
                                   "start": start, "end": end, "reason": reason,
                                   "status": "Beklemede"})
        return True

    # Salt okuma: web veriye yalniz servis uzerinden erisir (docs/architecture.md)
    def employees(self):
        return self._storage.employees()

    def requests(self):
        return self._storage.requests()
