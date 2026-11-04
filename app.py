# -*- coding: utf-8 -*-
# LeaveManager - Personel Izin Takip Sistemi
# (c) 2015 - Ic gelistirme. Sorumlu: Ahmet
# NOT: Bu dosyaya dokunmadan once Ahmet'e sor. (Ahmet 2019'da ayrildi)
#
# Kurulum noktasi (composition root): katmanlari kurar ve birbirine baglar
# (web -> domain -> storage, docs/architecture.md).
import logging
import os
import sys
from datetime import datetime

from flask import Flask

from domain.leave_service import LeaveService
from storage.memory import MemoryStorage
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

app = Flask(__name__)

# ---------------------------------------------------------------
# Baglanti noktalari (spec 0005): testler yalniz clock, storage, svc ve app'e
# dokunur; bu adlar burada kalir
# ---------------------------------------------------------------
class SystemClock:
    # "bugun"un tek kaynagi
    def today(self):
        return datetime.now().date()

clock = SystemClock()

storage = MemoryStorage()

svc = LeaveService(clock, storage)

register_routes(app, svc)

if __name__ == "__main__":
    # Debug only locally and on purpose: FLASK_DEBUG=1 python app.py (docs/security.md)
    app.run(port=5000)
