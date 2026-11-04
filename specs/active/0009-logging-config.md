# Spec 0009 — logging-config (mini)

- Status: Approved
- Mode: lite
- Plan: `specs/plans/0009-plan.md`
- Source: #21
- Design: — (kullanıcı arayüzü yok; değişiklik yalnızca sürecin log çıktısında)
- Supersedes: — (shipped bir kriter değişmiyor; 0008/CB-5 aşağıda korunan davranış olarak duruyor)

## Intent
Spec 0008'den beri beklenmeyen hatalar loglanıyor, ama uygulamada log yapılandırması yok. Kayıt
stderr'e zaman damgası, seviye ve kaynak bilgisi olmadan düşüyor ve seviye ayarlanamıyor.
İşletmede bir hatanın ne zaman ve nerede olduğu bu çıktıdan okunamıyor.

Bu iş, uygulamanın ürettiği her log satırını okunur bir biçime sokar ve log seviyesinin bir ortam
değişkeniyle ayarlanmasını sağlar. Hedef stderr olarak kalır; çıktıyı süreç yöneticisi ya da
konteyner toplar.

Bugünkü davranış (gözlem, 2026-11-04, `main` @ `9cad237`): beklenmeyen hatada stderr'e yalnızca
`izin talebi kaydedilemedi` satırı ve ardından stack trace düşüyor; zaman, seviye ve logger adı yok.

## Changed behavior
"Log satırı", uygulamanın (kendi kodu, Flask ve Werkzeug) `logging` ile ürettiği bir kayıttır.
- [ ] CB-1 — **Biçim:** her log satırı sırasıyla zaman damgasını (yerel saatle tarih ve saat), seviyeyi
  (`INFO`, `ERROR` …), logger adını (ör. `web.routes`) ve mesajı içerir. Stack trace taşıyan bir
  kayıtta stack trace bu satırın hemen altında gelir.
- [ ] CB-2 — **Hedef:** log satırları stderr'e yazılır. stdout'a log yazılmaz; diskte log dosyası
  oluşmaz.
- [ ] CB-3 — **Seviye ayarı:** seviye `LOG_LEVEL` ortam değişkeniyle seçilir (`DEBUG`, `INFO`,
  `WARNING`, `ERROR`, `CRITICAL`; büyük/küçük harf fark etmez). Değişken yoksa ya da boşsa seviye
  `INFO`'dur. Seçilen seviyenin altındaki kayıtlar yazılmaz. Örnek: `LOG_LEVEL=ERROR` iken
  Werkzeug'un istek satırları (INFO) yazılmaz, beklenmeyen hata (ERROR) yazılır.
- [ ] CB-4 — **Geçersiz değer:** `LOG_LEVEL` tanınmayan bir değer taşıyorsa (ör. `verbose`)
  uygulama yine başlar, seviye `INFO` olur ve stderr'e bir kez, geçersiz değeri ve kullanılan
  seviyeyi adıyla söyleyen bir `WARNING` satırı yazılır.
- [ ] CB-5 — **Tek kez:** her olay tam olarak bir log satırı (ve varsa stack trace'i) üretir; aynı
  kayıt iki farklı biçimde ya da iki kez yazılmaz. Werkzeug'un istek satırları da CB-1 biçimindedir.
- [ ] CB-6 — **Başlatma yolu:** yapılandırma, uygulama ister `python app.py` ile ister bir WSGI
  sunucusunun uygulamayı yüklemesiyle başlatılsın, aynı biçimde geçerli olur.

## Preserved behavior
- [ ] PB-1 — **0008/CB-5 aynen:** beklenmeyen hatada yanıt 500 ve genel mesajdır
  ("Talep kaydedilemedi. Lütfen daha sonra tekrar deneyin."); istisna metni ve stack trace sayfaya
  sızmaz; stack trace logda (artık CB-1 biçiminde) yer alır.
- [ ] PB-2 — **Debug kapalı:** `LOG_LEVEL=DEBUG` dahil hiçbir `LOG_LEVEL` değeri Werkzeug
  debugger'ını ya da Flask debug modunu açmaz (`docs/security.md`).
- [ ] PB-3 — **Ekranlar aynı:** GET `/`, `/requests`, `/new` ve geçerli/geçersiz talep POST'larının
  yanıtları (durum kodu ve gövde) `main` ile aynıdır.
- [ ] PB-4 — **Testler:** mevcut testler değişmeden geçer; `./scripts/check` (normal ve ters sıra)
  yeşil. Test koşusu repoda log dosyası bırakmaz (`docs/testing.md`).

## Out of scope
- Log dosyasına yazma, döndürme (rotation).
- Yapılandırılmış (JSON) log; düz metin yeterli (#21 kararı).
- Yeni log çağrıları eklemek (ör. her talebi INFO ile loglamak); yalnızca var olan kayıtların
  biçimi ve seviyesi ele alınır.
- Debug modunu açma yolu (`FLASK_DEBUG`); dokunulmaz.
- İstek kimliği (request id), kullanıcı bilgisi gibi bağlam alanları.

## Definition of Done
- [ ] `scripts/check` green
- [ ] Independent review done; real findings fixed, noise rejected with written rationale
- [ ] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI yok: kanıt gerçek süreçten
  alınmış stderr çıktısıdır)
- [ ] Spec moved to `specs/done/` (immutable there)

## Kararlar (spec onayında, İbrahim Gürhan, 2026-11-04)
- **S-1:** Ortam değişkeninin adı `LOG_LEVEL`. `FLASK_` öneki yok, böylece debug ile karışmaz.
- **S-2:** Geçersiz değerde uygulama başlar, seviye `INFO` olur ve bir `WARNING` yazılır (CB-4).
- **S-3:** Werkzeug'un istek satırları da aynı biçime girer (CB-5).
- **S-4:** Yapılandırma hem `python app.py` ile hem bir WSGI sunucusuyla yüklemede geçerlidir (CB-6).
- **S-5:** Zaman damgası yerel saatle yazılır, saat dilimi belirtilmez (CB-1). Gerekirse sonra
  değiştirilir.
- **S-6:** Yapılandırma, testlerin log yakalamasını (`caplog`) bozmaz. Bu, plana açık bir koşul
  olarak yazılır (PB-4).
