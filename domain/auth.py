# Giris ve oturum kurallari (spec 0019, ADR-0002 D-4, D-5). Saat disaridan verilen clock'tan,
# sifre dogrulamasi disaridan verilen hasher'dan (domain Werkzeug import etmez, mimari kural 1;
# gercek saati okumaz, kural 5). Sifre ya da ozeti hicbir log kaydina yazilmaz.
import logging
import secrets
from datetime import datetime, timedelta

from domain.accounts import normalize_email
from domain.errors import LoginRefused, SessionExpired

logger = logging.getLogger(__name__)

MAX_FAILED_ATTEMPTS = 5
LOCK_MINUTES = 15
SESSION_HOURS = 8
MAX_EMAIL_LENGTH = 254
MAX_PASSWORD_LENGTH = 1024


class LoginService:

    def __init__(self, clock, storage, hasher):
        self._clock = clock
        self._storage = storage
        self._hasher = hasher
        self._dummy_hash = None

    def _account(self, email):
        return next((a for a in self._storage.accounts() if a["email"] == email), None)

    def _spend_a_verify(self, password_hash, password):
        # Reddedilecek denemede de bir dogrulama yapilir: yanit suresi hesabin varligini,
        # kilidi ya da pasif durumu ele vermez (R-5)
        self._hasher.verify(password_hash, password)

    def _dummy(self):
        # Bilinmeyen e-posta icin sahte ozet: gercek ozetlerle ayni hasher ve parametreler,
        # rastgele bir metinden; ilk gerektiginde bir kez uretilir
        if self._dummy_hash is None:
            self._dummy_hash = self._hasher.hash(secrets.token_hex(16))
        return self._dummy_hash

    def authenticate(self, email, password):
        """Dogru bilgiyle aktif, kilitsiz hesabi doner; aksi halde LoginRefused. Sira plan 0019
        Risk 6: bos -> sinir -> bilinmeyen -> kilitli -> pasif -> sifre."""
        email = normalize_email(email)
        password = password or ""
        if not email or not password:
            logger.warning("başarısız giriş: boş alan")
            raise LoginRefused("bos")
        if len(email) > MAX_EMAIL_LENGTH or len(password) > MAX_PASSWORD_LENGTH:
            # Ozet hesaplanmaz (G-3); girilen metin log'a yazilmaz
            logger.warning("başarısız giriş: girdi sınırı aşıldı")
            raise LoginRefused("sinir")
        account = self._account(email)
        if account is None:
            self._spend_a_verify(self._dummy(), password)
            logger.warning("başarısız giriş: bilinmeyen hesap")
            raise LoginRefused("bilinmeyen")
        now = self._clock.now()
        locked_until = account["locked_until"]
        if locked_until is not None:
            if now < locked_until:
                self._spend_a_verify(account["password_hash"], password)
                logger.warning("başarısız giriş: %s kilitli (bitiş %s)", email,
                               locked_until.isoformat(timespec="seconds"))
                raise LoginRefused("kilitli")
            # Kilit bitti: sayac sifirdan baslar (S-2)
            self._storage.clear_login_failures(email)
        if not account["active"]:
            self._spend_a_verify(account["password_hash"], password)
            logger.warning("başarısız giriş: %s pasif", email)
            raise LoginRefused("pasif")
        if self._hasher.verify(account["password_hash"], password):
            self._storage.clear_login_failures(email)
            logger.info("giriş: %s", email)
            return account
        count = self._storage.record_login_failure(email)
        logger.warning("başarısız giriş: %s (art arda %d)", email, count)
        if count >= MAX_FAILED_ATTEMPTS:
            until = now + timedelta(minutes=LOCK_MINUTES)
            self._storage.lock_account(email, until)
            logger.warning("hesap kilitlendi: %s (bitiş %s)", email,
                           until.isoformat(timespec="seconds"))
        raise LoginRefused("sifre")

    def session_account(self, email, login_at):
        """Oturumdaki hesap. Oturum yoksa, bozuksa, hesap yoksa ya da pasifse None (R-8); giristen
        8 saat gectiyse SessionExpired (R-7). login_at: girisin ISO zamani."""
        if not email or not login_at:
            return None
        try:
            started = datetime.fromisoformat(login_at)
        except (TypeError, ValueError):
            return None
        now = self._clock.now()
        if started > now:
            return None
        if now - started >= timedelta(hours=SESSION_HOURS):
            raise SessionExpired()
        account = self._account(email)
        if account is None or not account["active"]:
            return None
        return account

    def session_start(self):
        """Yeni oturumun baslangici (ISO); session_account'a geri verilir."""
        return self._clock.now().isoformat()

    def logout(self, email):
        logger.info("çıkış: %s", email)
