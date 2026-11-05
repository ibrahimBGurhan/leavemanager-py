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

import click
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import check_password_hash, generate_password_hash

from domain.accounts import AccountService
from domain.errors import (AccountEmployeeNotFound, EmailTaken, EmployeeAlreadyHasAccount,
                           EmployeeRequired, InvalidEmail, PasswordMismatch, PasswordTooShort,
                           UnknownRole)
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


# ---------------------------------------------------------------
# Kullanici hesaplari (spec 0018, ADR-0002): sifre ozeti Werkzeug ile (varsayilan scrypt);
# domain onu bu hasher uzerinden kullanir (mimari kural 1). Varsayilan hesap ya da sifre yok:
# ilk IK hesabi `flask --app app hesap-ac` ile acilir. `accounts` testlerin bir baglanti noktasi.
# ---------------------------------------------------------------
class WerkzeugHasher:
    def hash(self, password):
        return generate_password_hash(password)

    def verify(self, password_hash, password):
        return check_password_hash(password_hash, password)


hasher = WerkzeugHasher()
accounts = AccountService(storage, hasher)

ROLE_LIST = "Personel, Yonetici, IK"


def account_error_message(error):
    # Turkce ileti; sifre ya da ozeti hicbir iletide yer almaz (R-8)
    if isinstance(error, InvalidEmail):
        return ("Geçersiz e-posta adresi: tek bir @ içermeli, iki yanı dolu olmalı ve boşluk "
                "içermemeli.")
    if isinstance(error, EmailTaken):
        return "Bu e-posta adresiyle bir hesap zaten var: %s" % error.email
    if isinstance(error, UnknownRole):
        return "Bilinmeyen rol: '%s'. Geçerli roller: %s." % (error.role, ROLE_LIST)
    if isinstance(error, EmployeeRequired):
        return "%s hesabı bir personele bağlanmalı: --personel <numara>." % error.role
    if isinstance(error, AccountEmployeeNotFound):
        return "Personel bulunamadı: %s." % error.employee_id
    if isinstance(error, EmployeeAlreadyHasAccount):
        return "Bu personelin zaten bir hesabı var: %s." % error.employee_id
    if isinstance(error, PasswordMismatch):
        return "Şifreler eşleşmiyor."
    if isinstance(error, PasswordTooShort):
        return "Şifre en az %d karakter olmalı." % error.minimum
    raise error


def fail(message):
    click.echo("Hata: %s Hesap oluşturulmadı." % message, err=True)
    raise SystemExit(1)


@app.cli.command("hesap-ac")
@click.option("--eposta", default="", help="Giriş kimliği (e-posta adresi).")
@click.option("--rol", default="", help="Personel, Yonetici ya da IK.")
@click.option("--personel", default="", help="Bağlı personel numarası (Personel/Yonetici için zorunlu).")
def create_account_command(eposta, rol, personel):
    """Yeni kullanici hesabi acar; sifre ekranda gorunmeden iki kez sorulur (spec 0018)."""
    # Sifre arguman ya da ortam degiskeni olarak alinmaz: kabuk gecmisinde ve surec listesinde
    # gorunur (G-4). Bellek deposunda hesap kalici olmaz (R-9).
    if isinstance(storage, MemoryStorage):
        fail("Bellek deposu (LEAVEMANAGER_STORAGE=memory) kullanılıyor; hesap kalıcı olmaz. "
             "Aracı veritabanıyla çalıştırın.")
    employee_id = None
    if personel.strip():
        try:
            employee_id = int(personel)
        except ValueError:
            fail(account_error_message(AccountEmployeeNotFound(personel)))
    try:
        # Sifre sorulmadan once diger girdiler dogrulanir (plan 0018 Risk 4)
        accounts.check_account_details(eposta, rol, employee_id)
        password = click.prompt("Şifre", hide_input=True)
        password_again = click.prompt("Şifre (tekrar)", hide_input=True)
        record = accounts.create_account(eposta, rol, employee_id, password, password_again)
    except (InvalidEmail, EmailTaken, UnknownRole, EmployeeRequired, AccountEmployeeNotFound,
            EmployeeAlreadyHasAccount, PasswordMismatch, PasswordTooShort) as e:
        fail(account_error_message(e))
    click.echo("Hesap oluşturuldu: %s (%s)" % (record["email"], record["role"]))

if __name__ == "__main__":
    # Debug only locally and on purpose: FLASK_DEBUG=1 python app.py (docs/security.md)
    app.run(port=5000)
