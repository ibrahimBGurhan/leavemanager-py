# Security

> Bootstrap'te (2026-10-23) dolduruldu. Uygulama personel verisi (ad, birim, işe giriş tarihi,
> izin nedeni) tutar; bu veriler **KVKK kapsamında kişisel veridir**. İzin nedeni sağlık bilgisi
> içerebilir ("Saglik"), bu da özel nitelikli kişisel veri olabilir. Her plan ve review bu kurallara uyar.

## Secrets
- Secrets never enter the repo, specs, prompts, or chat. `.env` is gitignored; provide `.env.example`.
- Agents never print secret values, even when debugging.
- Flask `SECRET_KEY` (oturum ve CSRF token'larını imzalar) `SECRET_KEY` ortam değişkeninden okunur,
  koda yazılmaz; örnek `.env.example`'da (spec 0011). Tanımlı değilse uygulama süreç başına
  rastgele bir anahtar kullanır ve `app.secrets` logger'ından değeri içermeyen tek bir WARNING
  yazar; yeniden başlatmada açık formlar geçersizleşir. **Üretimde ve birden çok süreçte mutlaka
  tanımlanmalı** — her süreç farklı anahtar üretirse formlar rastgele reddedilir.

## Veri ve yedekleme
- Veritabanı dosyası (`DATABASE_PATH`, varsayılan `instance/leavemanager.db`) personel ve izin
  verisi taşır: **KVKK kapsamında kişisel veri**, izin nedeni sağlık bilgisi içerebilir. Repoya
  girmez (`instance/` gitignore'da); dosyayı ve yedeklerini yalnız uygulamayı işleten hesap
  okuyabilmeli (dosya izinleri kodla zorlanmaz, kurulumda ayarlanır).
- Yedekleme operasyonun işidir (ADR-0001, spec 0017 K-7): uygulama durdurulup dosya (ve varsa
  `-wal`, `-shm` dosyaları) kopyalanır ya da uygulama çalışırken `sqlite3 <dosya> ".backup <hedef>"`
  kullanılır. Yedekler aynı koruma altında saklanır; geri yükleme düzenli olarak denenir.
- Demo verisi üretimde yüklenmez; yalnız `SEED_DEMO_DATA=1` ve boş veritabanında.

## Input & output
- **Çıktı:** HTML yalnızca Jinja şablonlarında, otomatik kaçış (autoescape) açık olarak üretilir.
  Kullanıcı verisini içeren HTML'de string birleştirme ve `|safe` / `Markup` yasaktır.
  *Mevcut kod ihlal ediyor:* `{{ body|safe }}` ve `reason` alanı kaçışsız basılıyor → **stored XSS**.
- **Girdi:** form verisi web katmanında, sınırda doğrulanır: tarih formatı (`YYYY-MM-DD`),
  bitiş ≥ başlangıç, personel kimliği var olan bir personel, `reason` için uzunluk sınırı.
  Geçersiz girdi kullanıcıya anlaşılır bir mesajla döner; sessizce yönlendirilmez.
- **CSRF:** durum değiştiren her form (POST) CSRF token'ı taşır. Flask-WTF `CSRFProtect` ile
  sağlanır (spec 0011): token tarayıcı oturumuna bağlıdır, süre sınırı yoktur; eksik, bozuk ya da
  başka oturumun token'ı → 400, hiçbir kayıt değişmez, Türkçe mesaj. Oturum çerezi `HttpOnly` ve
  `SameSite=Lax`; `Secure` yalnız `SESSION_COOKIE_SECURE=1` ile (spec 0019). Testlerin
  ortak istemcisi korumayı kapatır;
  korumayı `tests/test_csrf.py` açık olarak sınar.
- **Form değerlerinin geri basılması:** Yeni Talep hata ekranında yalnız doğrulanmış değerler geri
  basılır: personel yalnız seçenek listesiyle tamsayı eşleşmesi, tarihler yalnız ayrıştırılmış
  `YYYY-MM-DD`, neden kaçışlı (`escape`) öznitelik değeri. Ham girdi sayfaya ulaşmaz. CSRF
  hatasında hiçbir değer geri basılmaz: isteğin kaynağı belirsizdir (spec 0015).
- **Hata mesajları:** stack trace, istisna metni ve iç kodlar kullanıcıya sızmaz (`docs/conventions.md`).
- **Debug:** `debug=True` koda yazılmaz. Debug yalnızca yerelde bir ortam değişkeniyle açılır.
  Werkzeug debugger ağdan erişilebilir olduğunda uzaktan kod çalıştırmaya izin verir.
  Kodda debug kapalıdır; bunu `tests/test_security.py::test_running_app_py_does_not_force_debug_mode` sınar.

## AuthN / AuthZ
- **Hedef:** varsayılan deny. Giriş yapmamış kullanıcı hiçbir sayfayı göremez.
- **Yöntem:** uygulama içi kullanıcı (e-posta) ve şifre; Werkzeug şifre özeti, Flask oturumu
  (en fazla 8 saat), 5 başarısız denemede 15 dakika kilit, en az 12 karakter, varsayılan şifre yok
  (ADR-0002). **Giriş sistemi yayına yalnız HTTPS ile çıkar**; `SESSION_COOKIE_SECURE` orada açılır.
- Roller (spec 0020): **IK** tüm personeli ve talepleri görür, herkes adına talep açar, talepleri
  onaylar / reddeder (kendi talebi dahil; görev ayrılığı yok). **Personel** yalnız bağlı olduğu
  personel kaydının bakiyesini ve taleplerini görür, yalnız kendi adına talep açar, hiçbir talebi
  sonuçlandıramaz. **Yönetici** bu sürümde Personel gibidir; birim görünümü ve onay ayrı spec'tir
  (0021). Bilinmeyen ya da bozuk rol Personel kapsamına düşer (fail-closed). Bağlı personel kaydı
  olmayan hesap hiçbir veri görmez, talep açamaz.
- Yetki kontrolü sunucu tarafında, tek yerde: `domain/access.py` (`AccountView`) hesabı parametre
  olarak alır; web her ekranı ve işlemi `svc.for_account(g.account)` üzerinden yapar ve ekranı
  (düğmeler, personel seçimi) ona göre çizer (plan 0020 Risk 1). Yetki, talebin ya da personelin
  varlığından ve durumundan önce denetlenir: yetkisiz deneme 403 + "Bu işlem için yetkiniz yok.",
  hiçbir kayıt değişmez, log'a WARNING (e-posta, işlem, hedef numara; neden ve tarih yok). Hata ve
  CSRF sayfaları da süzülür. UI'da bir butonu gizlemek yetkilendirme sayılmaz;
  `tests/test_architecture.py` web'in servise yalnız `for_account` ile gittiğini sınar.
- *Hesaplar (spec 0018):* kullanıcı hesapları `flask --app app hesap-ac` ile açılır; şifre
  yalnız Werkzeug özeti (scrypt) olarak saklanır, açık metni veritabanına, log'a ya da çıktıya
  yazılmaz; komut satırı argümanı ya da ortam değişkeni olarak alınmaz. Kodda varsayılan hesap ya
  da şifre yok (`tests/test_accounts.py`).
- *Giriş (spec 0019):* giriş ekranı (`/giris`) dışındaki her istek — bilinmeyen adresler ve
  sonradan eklenecek route'lar dahil — giriş yapmamış kullanıcıyı girişe yönlendirir; hiçbir
  kayıt değişmez (`web/auth.py`, `tests/test_login.py::test_every_route_is_closed`). Kapı
  `CSRFProtect`'ten önce çalışır: giriş yapmamış birinin token'sız POST'u CSRF hata sayfasına
  (Talepler, veriyle) ulaşmaz. Her ret nedeni (bilinmeyen e-posta, yanlış şifre, pasif, kilitli,
  boş alan) aynı iletiyi ve 401'i alır; bilinmeyen e-postada da bir şifre doğrulaması yapılır:
  asıl maliyet olan doğrulama işi iki yolda eşittir. Yanlış şifrede sayaç yazımı kadar küçük bir
  süre farkı kalır (review 0019 F-2: yerelde medyan ~80 ms'ye ~85 ms); 5 denemede gelen kilit
  bu farkın ağ gürültüsünden ayrılmasını zorlaştırır. Art arda 5 hatalı denemede 15 dakika
  kilit; sayaç veritabanında, aynı anda gelen denemelerde de kaybolmaz. E-posta en fazla 254,
  şifre en fazla 1024 karakter (uzun girdiyle özet hesaplatılamaz). Her başarısız deneme
  WARNING (var olan hesapta e-posta ve sayı; bilinmeyen e-postada yazılan metin değil "bilinmeyen
  hesap"), kilit ayrı WARNING, giriş ve çıkış INFO; şifre ve özet hiçbir kayıtta yok. Oturum
  girişten itibaren en fazla 8 saat (işlemle uzamaz); girişte önceki oturum verisi temizlenir; hesap
  pasife alınır ya da silinirse sonraki istekte oturum kapanır. Çıkış CSRF token'lı POST.
- *Bilinen sınır (plan 0019 Risk 4, kabul):* Flask oturumu imzalı çerezde durur; sunucuda iptal
  listesi yok. Çıkış tarayıcıdaki çerezi siler, ama çıkıştan önce **kopyalanmış** bir çerez 8 saat
  dolana kadar geçerli kalır (pasif hesap ve süre yine kapıda sınanır). Çerezde e-posta ve giriş
  zamanı imzalı ama şifresiz (base64) durur; şifre ya da özet durmaz. Sunucu tarafı oturum kaydı
  roller spec'inde ya da bir olay olursa yeniden değerlendirilir.
- *Rol bazlı yetki (spec 0020):* yukarıdaki roller uygulanır; Yönetici'nin birim görünümü ve onay
  yetkisi spec 0021'de değerlendirilir (`docs/domain.md` OD-7, BR-10).

## Dependencies
- Her yeni paket plan aşamasında gerekçesiyle önerilir ve **insan onaylar**.
- Kontroller: lisans MIT/BSD/Apache-2.0 uyumlu olmalı, aktif bakımda olmalı, `pip-audit` bilinen
  bir CVE göstermemeli.
- Sürümler `requirements*.txt` içinde `==` ile sabitlenir. Yükseltmeler ayrı ve dar commit'lerle yapılır.

## Review lens
Security is a mandatory dimension of every independent review (see `prompts/review.md`), not a
separate afterthought phase.
