# Kullanici hesaplari (spec 0018, ADR-0002): hesap acma kurallari. Sifre ozeti disaridan verilen
# hasher ile uretilir (domain Werkzeug import etmez, mimari kural 1); sifrenin acik metni hicbir
# yerde saklanmaz ve log'a yazilmaz.
import logging

from domain.errors import (AccountEmployeeNotFound, EmailTaken, EmployeeAlreadyHasAccount,
                           EmployeeRequired, InvalidEmail, PasswordMismatch, PasswordTooShort,
                           UnknownRole)

logger = logging.getLogger(__name__)

ROLES = ("Personel", "Yonetici", "IK")
ROLES_NEEDING_EMPLOYEE = ("Personel", "Yonetici")
MIN_PASSWORD_LENGTH = 12


def normalize_email(email):
    """Bas/son bosluk atilir, kucuk harfe cevrilir (R-5)."""
    return (email or "").strip().lower()


def normalize_role(role):
    """`ik`, `YONETICI` gibi yazimlar ROLES'taki yazima cevrilir; bilinmeyen rol None (G-3)."""
    wanted = (role or "").strip().lower()
    return next((r for r in ROLES if r.lower() == wanted), None)


class AccountService:

    def __init__(self, storage, hasher):
        # hasher: hash(password) -> str, verify(password_hash, password) -> bool
        self._storage = storage
        self._hasher = hasher

    def check_account_details(self, email, role, employee_id):
        """Sifre disindaki girdileri dogrular; (e-posta, rol) doner. Sira: e-posta bicimi, var
        olan e-posta, rol, personel. Ihlalde AccountError ailesinden bir hata."""
        email = normalize_email(email)
        local, at, domain = email.partition("@")
        if not at or not local or not domain or "@" in domain or any(c.isspace() for c in email):
            raise InvalidEmail()
        if any(a["email"] == email for a in self._storage.accounts()):
            raise EmailTaken(email)
        canonical_role = normalize_role(role)
        if canonical_role is None:
            raise UnknownRole(role)
        if employee_id is None:
            if canonical_role in ROLES_NEEDING_EMPLOYEE:
                raise EmployeeRequired(canonical_role)
        else:
            if not any(e["id"] == employee_id for e in self._storage.employees()):
                raise AccountEmployeeNotFound(employee_id)
            if any(a["employee_id"] == employee_id for a in self._storage.accounts()):
                raise EmployeeAlreadyHasAccount(employee_id)
        return email, canonical_role

    def create_account(self, email, role, employee_id, password, password_again):
        """Yeni, aktif, kilitsiz bir hesap acar ve kaydi doner. Sifre oldugu gibi kullanilir
        (bosluk atilmaz, R-3). Herhangi bir ihlalde hicbir kayit olusmaz (R-7)."""
        email, role = self.check_account_details(email, role, employee_id)
        if password != password_again:
            raise PasswordMismatch()
        if len(password) < MIN_PASSWORD_LENGTH:
            raise PasswordTooShort(MIN_PASSWORD_LENGTH)
        record = {"email": email, "password_hash": self._hasher.hash(password), "role": role,
                  "employee_id": employee_id, "active": True, "failed_attempts": 0,
                  "locked_until": None}
        self._storage.add_account(record)
        logger.info("hesap oluşturuldu: %s (%s)", email, role)
        return record
