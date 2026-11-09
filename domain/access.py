# Rol bazli yetki (spec 0020, 0021; ADR-0002): bir hesabin gozunden izin verisi. Kural tek yerde,
# uc kapsam: IK her seyi gorur ve yapar; Yonetici kendi biriminin personelini ve taleplerini gorur,
# birimindeki baskasinin bekleyen talebini sonuclandirir (0021 R-1…R-5); baska her rol (Personel,
# bilinmeyen, birimi bos Yonetici) yalniz bagli oldugu personel kaydini gorur ve hicbir talebi
# sonuclandiramaz (0020 R-1, R-5; bilinmeyen rol yetki kazanmaz, plan 0020 Risk 2). Herkes yalniz
# kendi adina talep acar, IK haric. Yetki, talebin ya da personelin varligindan
# ve talebin durumundan once denetlenir (R-6). Bu katman Flask'i, HTML'i ve depoyu bilmez; veriye
# LeaveService'in public fonksiyonlariyla ulasir.
import logging

from domain.errors import NotAuthorized

logger = logging.getLogger(__name__)

ROLE_HR = "IK"
ROLE_MANAGER = "Yonetici"
# Durum degeri (docs/domain.md). leave_service bu modulu import ettigi icin oradan alinamaz;
# esitligi tests/test_access.py sinar.
PENDING = "Beklemede"

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
        # En az bir talebi sonuclandirabilir mi: IK ya da birim kapsamli Yonetici (plan 0021 Risk 6)
        return self.sees_everyone() or self._unit() is not None

    def can_decide_request(self, r):
        """Bu talebi sonuclandirabilir mi. IK: bekleyen her talep (kendi talebi dahil, 0020 S-2).
        Yonetici: birimindeki, kendisinin olmayan, bekleyen talep (0021 R-4, R-5, G-1)."""
        if r["status"] != PENDING:
            return False
        if self.sees_everyone():
            return True
        unit = self._unit()
        if unit is None:
            return False
        own = self.own_employee()
        return r["employee_id"] != own["id"] and any(e["id"] == r["employee_id"] for e in unit)

    def _unit(self):
        # Yonetici'nin birimi: bagli personelin Birim degeri, tam eslesme (0021 R-1, G-3). Bag yoksa,
        # kayit yoksa ya da Birim bos / yalniz bosluksa birim kapsami yok (G-2): None.
        if self._account.get("role") != ROLE_MANAGER:
            return None
        own = self.own_employee()
        if own is None or not (own.get("department") or "").strip():
            return None
        return [e for e in self._svc.employees() if e["department"] == own["department"]]

    def own_employee(self):
        """Hesabin bagli oldugu personel kaydi; bag yoksa ya da kayit artik yoksa None (R-7)."""
        emp_id = self._account.get("employee_id")
        if emp_id is None:
            return None
        return next((e for e in self._svc.employees() if e["id"] == emp_id), None)

    def employees(self):
        if self.sees_everyone():
            return self._svc.employees()
        unit = self._unit()
        if unit is not None:
            return unit
        own = self.own_employee()
        return [own] if own is not None else []

    def requests(self):
        if self.sees_everyone():
            return self._svc.requests()
        visible = {e["id"] for e in self.employees()}
        return [r for r in self._svc.requests() if r["employee_id"] in visible]

    def balance(self, emp):
        """(Hak, Kullanilan, Kalan, Bekleyen) — yalniz gorunur bir personel icin (R-2; plan 0020
        R-07 eki). Hesap LeaveService'te kalir; burada yalniz kapsam denetlenir."""
        if not self.sees_everyone() and emp["id"] not in {e["id"] for e in self.employees()}:
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
        # IK: denetim yok, domain hatalari (yok / sonuclanmis) bugunku gibi akar. Digerleri: talep
        # gorunur, kendisinin degil ve bekliyor olmali; yoksa ayni ret — "yok" ile "baska birimde"
        # disaridan ayirt edilemez (0021 R-6; plan 0021 Risk 1). Hedef ham olabilir (route numarayi
        # ayristirmadan sorar): yalniz ASCII rakam numara sayilir (web.parse_request_id kurali).
        if self.sees_everyone():
            return
        rid = target
        if isinstance(target, str):
            rid = int(target) if target.isascii() and target.isdigit() else None
        r = next((x for x in self.requests() if x["id"] == rid), None)             if isinstance(rid, int) else None
        if r is None or not self.can_decide_request(r):
            self._refuse(action, target)

    def create_request(self, emp_id, start, end, reason):
        self.authorize_create(emp_id)
        return self._svc.create_request(emp_id, start, end, reason)

    def approve_request(self, request_id):
        self.authorize_decide(ACTION_APPROVE, request_id)
        return self._svc.approve_request(request_id, decided_by=self._decider())

    def reject_request(self, request_id):
        self.authorize_decide(ACTION_REJECT, request_id)
        return self._svc.reject_request(request_id, decided_by=self._decider())

    def _decider(self):
        # Karar log'u icin "<e-posta> (<rol>)" (spec 0021 R-9)
        return "%s (%s)" % (self._account.get("email"), self._account.get("role"))

    def _refuse(self, action, target):
        # E-posta, islem ve hedef numara; talebin nedeni ve tarihleri yazilmaz (G-6). Hedef elle
        # yazilmis bir deger olabilir: %r ile, tek satir ve tirnak icinde yazilir.
        logger.warning("yetkisiz islem: %s, %s, hedef %r", self._account.get("email"), action,
                       target)
        raise NotAuthorized(action, target)
