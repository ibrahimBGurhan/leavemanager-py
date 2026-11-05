# -*- coding: utf-8 -*-
# LeaveManager - Personel Izin Takip Sistemi
# (c) 2015 - Ic gelistirme. Sorumlu: Ahmet
# NOT: Bu dosyaya dokunmadan once Ahmet'e sor. (Ahmet 2019'da ayrildi)
#
# Kurulum noktasi (composition root): katmanlari kurar ve birbirine baglar
# (web -> domain -> storage, docs/architecture.md).
import logging
import os
import secrets
import sys
from datetime import datetime

from flask import Flask
from flask_wtf.csrf import CSRFProtect

from domain.leave_service import LeaveService
from storage.demo import demo_employees, demo_requests
from storage.memory import MemoryStorage
from storage.sqlite import SqliteStorage, StorageUnavailable
from web.routes import register_routes

# ---------------------------------------------------------------
# Log yapilandirmasi (spec 0009): seviye LOG_LEVEL'dan, hedef stderr.
# Katmanlar yalniz logging.getLogger(__name__) kullanir.
# ---------------------------------------------------------------
LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def configure_logging(value):
    # Kok logger'da zaten handler varsa (pytest, ya da log'u kendisi kuran bir host)
    # yapilandirma kurulmaz; host'un ayari gecerli kalir (plan 0009, R-1)
    name = (value or "").strip().upper() or "INFO"
    invalid = name not in LOG_LEVELS
    level = "INFO" if invalid else name
    if not logging.getLogger().handlers:
        logging.basicConfig(level=level, format=LOG_FORMAT, stream=sys.stderr)
        # Werkzeug, logger'inin seviyesi bos ise INFO koyar; LOG_LEVEL ona da gecsin
        logging.getLogger("werkzeug").setLevel(level)
    if invalid:
        logging.getLogger("app").warning(
            "LOG_LEVEL=%r tanınmıyor; seviye INFO kullanılıyor", value)


configure_logging(os.environ.get("LOG_LEVEL"))


# ---------------------------------------------------------------
# Gizli anahtar ve CSRF (spec 0011): anahtar ortamdan gelir, koda yazilmaz
# (docs/security.md). Yoksa surec basina rastgele anahtar + tek WARNING;
# uyari "app.secrets" logger'indan (spec 0011 K-1). Deger hicbir yere yazilmaz.
# ---------------------------------------------------------------
def load_secret_key(environ):
    key = (environ.get("SECRET_KEY") or "").strip()
    if key:
        return key
    logging.getLogger("app.secrets").warning(
        "SECRET_KEY tanımlı değil; süreç başına rastgele bir anahtar kullanılıyor "
        "(yeniden başlatmada açık formlar geçersizleşir)")
    return secrets.token_hex(32)


app = Flask(__name__)
app.config["SECRET_KEY"] = load_secret_key(os.environ)
app.config["WTF_CSRF_TIME_LIMIT"] = None        # token tarayici oturumu boyunca gecerli (K-2)
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"   # HttpOnly varsayilan; Secure zorlanmaz (K-3)
CSRFProtect(app)

# ---------------------------------------------------------------
# Baglanti noktalari (spec 0005): testler yalniz clock, storage, svc ve app'e
# dokunur; bu adlar burada kalir
# ---------------------------------------------------------------
class SystemClock:
    # "bugun"un tek kaynagi
    def today(self):
        return datetime.now().date()

clock = SystemClock()

# ---------------------------------------------------------------
# Kalici depo (ADR-0001, spec 0017): SQLite dosyasi DATABASE_PATH'ten, yoksa uygulama
# klasorunde instance/leavemanager.db. Demo verisi yalniz SEED_DEMO_DATA=1 ve bos veritabaninda.
# LEAVEMANAGER_STORAGE=memory yalniz test/gelistirme: veri kalici degildir, her acilista WARNING.
# Veritabani acilamazsa uygulama acilmaz (K-5); bellege sessiz donus yok.
# ---------------------------------------------------------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))


def database_path(environ):
    return environ.get("DATABASE_PATH") or os.path.join(APP_DIR, "instance", "leavemanager.db")


def build_storage(environ):
    log = logging.getLogger("app.storage")
    if environ.get("LEAVEMANAGER_STORAGE") == "memory":
        log.warning("bellek deposu: veri kalıcı değil (yalnız test/geliştirme)")
        return MemoryStorage()
    path = database_path(environ)
    seed = (demo_employees(), demo_requests()) if environ.get("SEED_DEMO_DATA") == "1" else None
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        return SqliteStorage(path, seed_records=seed)
    except (OSError, StorageUnavailable) as e:
        log.error("veritabanı açılamadı: %s (%s)", path, e)
        raise SystemExit(1)


storage = build_storage(os.environ)

svc = LeaveService(clock, storage)

register_routes(app, svc)

if __name__ == "__main__":
    # Debug only locally and on purpose: FLASK_DEBUG=1 python app.py (docs/security.md)
    app.run(port=5000)
