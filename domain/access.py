# Rol bazli yetki (spec 0020, ADR-0002): bir hesabin gozunden izin verisi. Kural tek yerde:
# IK her seyi gorur ve yapar; baska her rol (Personel, Yonetici, bilinmeyen) yalniz bagli oldugu
# personel kaydini gorur, yalniz kendi adina talep acar, hicbir talebi sonuclandiramaz (R-1, R-5;
# bilinmeyen rol yetki kazanmaz, plan 0020 Risk 2). Yetki, talebin ya da personelin varligindan
# ve talebin durumundan once denetlenir (R-6). Bu katman Flask'i, HTML'i ve depoyu bilmez; veriye
# LeaveService'in public fonksiyonlariyla ulasir.
import logging

from domain.errors import NotAuthorized

logger = logging.getLogger(__name__)

ROLE_HR = "IK"

# Log'a yazilan islem adlari (R-6, G-6)
ACTION_APPROVE = "onay"
ACTION_REJECT = "red"
ACTION_CREATE_FOR_OTHER = "baskasi adina talep"
ACTION_BALANCE = "bakiye"


class AccountView:

    def __init__(self, service, account):
        self._svc = service
        self._account = account

    def sees_everyone(self):
        return self._account.get("role") == ROLE_HR

    def can_decide(self):
        # Talepleri yalniz IK sonuclandirir, kendi talebi dahil (R-5, S-2)
        return self.sees_everyone()

    def own_employee(self):
        """Hesabin bagli oldugu personel kaydi; bag yoksa ya da kayit artik yoksa None (R-7)."""
        emp_id = self._account.get("employee_id")
        if emp_id is None:
            return None
        return next((e for e in self._svc.employees() if e["id"] == emp_id), None)

    def employees(self):
        if self.sees_everyone():
            return self._svc.employees()
        own = self.own_employee()
        return [own] if own is not None else []

    def requests(self):
        if self.sees_everyone():
            return self._svc.requests()
        own = self.own_employee()
        if own is None:
            return []
        return [r for r in self._svc.requests() if r["employee_id"] == own["id"]]

    def balance(self, emp):
        """(Hak, Kullanilan, Kalan, Bekleyen) — yalniz gorunur bir personel icin (R-2; plan 0020
        R-07 eki). Hesap LeaveService'te kalir; burada yalniz kapsam denetlenir."""
        if not self.sees_everyone():
            own = self.own_employee()
            if own is None or emp["id"] != own["id"]:
                self._refuse(ACTION_BALANCE, emp["id"])
        return (self._svc.get_entitlement(emp), self._svc.get_used_days(emp["id"]),
                self._svc.get_remaining(emp), self._svc.get_pending_days(emp["id"]))

    def calc_days(self, start, end):
        # Is gunu sayisi; kisiye bagli veri yok (BR-3)
        return self._svc.calc_days(start, end)

    # Yalniz denetleyen iki fonksiyon: kural burada tek yerde, islemler ve web ayni kontrolu
    # kullanir (review 0020 F-1). Yetki yoksa log + NotAuthorized; varsa hicbir sey yapmaz.
    def authorize_create(self, emp_id):
        if self.sees_everyone():
            return
        own = self.own_employee()
        if own is None or emp_id != own["id"]:
            self._refuse(ACTION_CREATE_FOR_OTHER, emp_id)

    def authorize_decide(self, action, target):
        if not self.can_decide():
            self._refuse(action, target)

    def create_request(self, emp_id, start, end, reason):
        self.authorize_create(emp_id)
        return self._svc.create_request(emp_id, start, end, reason)

    def approve_request(self, request_id):
        self.authorize_decide(ACTION_APPROVE, request_id)
        return self._svc.approve_request(request_id)

    def reject_request(self, request_id):
        self.authorize_decide(ACTION_REJECT, request_id)
        return self._svc.reject_request(request_id)

    def _refuse(self, action, target):
        # E-posta, islem ve hedef numara; talebin nedeni ve tarihleri yazilmaz (G-6). Hedef elle
        # yazilmis bir deger olabilir: %r ile, tek satir ve tirnak icinde yazilir.
        logger.warning("yetkisiz islem: %s, %s, hedef %r", self._account.get("email"), action,
                       target)
        raise NotAuthorized(action, target)
