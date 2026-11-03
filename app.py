# -*- coding: utf-8 -*-
# LeaveManager - Personel Izin Takip Sistemi
# (c) 2015 - Ic gelistirme. Sorumlu: Ahmet
# NOT: Bu dosyaya dokunmadan once Ahmet'e sor. (Ahmet 2019'da ayrildi)
#
# Kurulum noktasi (composition root): katmanlari kurar ve birbirine baglar
# (web -> domain -> storage, docs/architecture.md).
from datetime import datetime

from flask import Flask

from domain.leave_service import LeaveService
from storage.memory import MemoryStorage
from web.routes import register_routes

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
