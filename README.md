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

`WARNING` ve üstünde Werkzeug'un "Running on http://…" satırı ve geliştirme sunucusu uyarısı da
gizlenir. Uygulamayı yükleyen ortam log'u zaten kendisi yapılandırmışsa onun ayarı geçerli kalır.

Kullanıcı hesabı açma (spec 0018, ADR-0002). Varsayılan hesap ya da şifre yoktur; ilk IK hesabı
sunucuda bu komutla açılır. Şifre ekranda görünmeden iki kez sorulur (en az 12 karakter); komut
satırında ya da ortam değişkeninde verilmez:

    .venv/Scripts/python -m flask --app app hesap-ac --eposta ik@firma.com --rol IK
    .venv/Scripts/python -m flask --app app hesap-ac --eposta ayse@firma.com --rol Personel --personel 1

Roller: `Personel`, `Yonetici`, `IK`. Personel ve Yonetici hesabı bir personel numarasına bağlanır
(bir personele en fazla bir hesap); IK için `--personel` isteğe bağlı. Komut uygulamanın
veritabanını (`DATABASE_PATH`) kullanır; bellek deposunda (`LEAVEMANAGER_STORAGE=memory`) çalışmaz.

Personel ekleme (spec 0022). İK, menüdeki "Yeni Personel" ekranından (`/personel/yeni`) ad, birim
ve işe giriş tarihiyle yeni personel kaydı açar; numarayı sistem verir (kayıtlı en büyük numaradan
bir fazla, boş veritabanında 1) ve "Personel #N eklendi: …" iletisinde gösterir. Birim alanı
kayıtlı birimleri öneri olarak sunar; yazıldığı gibi saklanır (Yönetici birimi tam eşleşmeyle
bulur: "IT" ile "It" ayrı birimdir). Bağlantıyı ve ekranı yalnız İK görür. Personeli düzenleme ve
silme ekranı yoktur.

İlk kurulum sırası (üretim veritabanı boş başlar): 1) `hesap-ac --rol IK` ile ilk İK hesabı
(personele bağlanmadan), 2) İK uygulamaya girip "Yeni Personel"den personeli ekler, 3) Personel ve
Yönetici hesapları ekranda görünen numarayla açılır (`hesap-ac --rol Personel --personel <N>`).

Giriş (spec 0019). Giriş yapmamış kullanıcı her sayfadan giriş ekranına (`/giris`) yönlendirilir;
e-posta ve şifreyle girilir, oturum en fazla 8 saat sürer, menüdeki "Çıkış" ile kapanır. Art arda
5 hatalı denemede hesap 15 dakika kilitlenir. Oturumlar `SECRET_KEY` ile imzalanır: üretimde
mutlaka tanımlayın, yoksa her yeniden başlatmada herkes yeniden giriş yapar.

Roller ve yetki (spec 0020, 0021). `IK` her şeyi görür ve yapar: tüm personelin bakiyeleri ve
talepleri, herkes adına talep, onay ve red. `Yonetici` kendi biriminin (bağlı olduğu personelin
"Birim" değeri) bakiyelerini ve taleplerini görür, birimindeki başkalarının bekleyen taleplerini
onaylar ya da reddeder; kendi talebini İK ya da birimdeki başka bir Yönetici sonuçlandırır.
`Personel` yalnız kendi bakiyesini ve taleplerini görür, yalnız kendi adına talep açar, onay ve red
yapamaz. Herkes (İK hariç) yalnız kendi adına talep açar. Yetkisiz bir işlem "Bu işlem için yetkiniz
yok." iletisiyle reddedilir ve hiçbir kaydı değiştirmez.

**Giriş sistemi yayına yalnız HTTPS ile çıkar** (ADR-0002 D-6; ters vekil sunucu). HTTPS'li
dağıtımda oturum çerezinin yalnız HTTPS'te gönderilmesi için:

    SESSION_COOKIE_SECURE=1 .venv/Scripts/python app.py

Yalnız `1` değeri açar; değişken yoksa (yerel / iç ağ HTTP) kapalıdır. Düz HTTP'de açılırsa
tarayıcı çerezi geri göndermez ve giriş çalışmaz ("Form geçersiz").

Doğrulama (lint + testler):

    ./scripts/check          # full — tek kanıt
    ./scripts/check --fast   # iç döngü
