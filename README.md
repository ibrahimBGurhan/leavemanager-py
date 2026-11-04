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

Loglar stderr'e `zaman seviye logger: mesaj` biçiminde yazılır. Seviye `LOG_LEVEL` ile seçilir
(`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`; varsayılan `INFO`):

    LOG_LEVEL=WARNING .venv/Scripts/python app.py

`WARNING` ve üstünde Werkzeug'un "Running on http://…" satırı da gizlenir. Uygulamayı yükleyen
ortam log'u zaten kendisi yapılandırmışsa onun ayarı geçerli kalır.

Doğrulama (lint + testler):

    ./scripts/check          # full — tek kanıt
    ./scripts/check --fast   # iç döngü
