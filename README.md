# LeaveManager (Python/Flask)

Personel yıllık izin takibi. Proje kuralları: `AGENTS.md`.

Kurulum (Python 3.13):

    python -m venv .venv
    .venv/Scripts/python -m pip install -r requirements-dev.txt   # Linux/macOS: .venv/bin/python

Çalıştırma:

    .venv/Scripts/python app.py

Adres: http://localhost:5000

Yalnızca yerel geliştirmede debug modu (asla paylaşılan bir sunucuda değil):

    FLASK_DEBUG=1 .venv/Scripts/python app.py

Doğrulama (lint + testler):

    ./scripts/check          # full — tek kanıt
    ./scripts/check --fast   # iç döngü
