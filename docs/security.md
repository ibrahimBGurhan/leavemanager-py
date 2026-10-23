# Security

> Bootstrap'te (2026-10-23) dolduruldu. Uygulama personel verisi (ad, birim, işe giriş tarihi,
> izin nedeni) tutar; bu veriler **KVKK kapsamında kişisel veridir**. İzin nedeni sağlık bilgisi
> içerebilir ("Saglik"), bu da özel nitelikli kişisel veri olabilir. Her plan ve review bu kurallara uyar.

## Secrets
- Secrets never enter the repo, specs, prompts, or chat. `.env` is gitignored; provide `.env.example`.
- Agents never print secret values, even when debugging.
- Flask `SECRET_KEY` (oturum ve CSRF için gerekli olacak) ortam değişkeninden okunur, koda yazılmaz.

## Input & output
- **Çıktı:** HTML yalnızca Jinja şablonlarında, otomatik kaçış (autoescape) açık olarak üretilir.
  Kullanıcı verisini içeren HTML'de string birleştirme ve `|safe` / `Markup` yasaktır.
  *Mevcut kod ihlal ediyor:* `{{ body|safe }}` ve `reason` alanı kaçışsız basılıyor → **stored XSS**.
- **Girdi:** form verisi web katmanında, sınırda doğrulanır: tarih formatı (`YYYY-MM-DD`),
  bitiş ≥ başlangıç, personel kimliği var olan bir personel, `reason` için uzunluk sınırı.
  Geçersiz girdi kullanıcıya anlaşılır bir mesajla döner; sessizce yönlendirilmez.
- **CSRF:** durum değiştiren her form (POST) CSRF token'ı taşır.
- **Hata mesajları:** stack trace, istisna metni ve iç kodlar kullanıcıya sızmaz (`docs/conventions.md`).
- **Debug:** `debug=True` koda yazılmaz. Debug yalnızca yerelde bir ortam değişkeniyle açılır.
  Werkzeug debugger ağdan erişilebilir olduğunda uzaktan kod çalıştırmaya izin verir.
  *Mevcut kod ihlal ediyor:* `app.run(debug=True)`.

## AuthN / AuthZ
- **Hedef:** varsayılan deny. Giriş yapmamış kullanıcı hiçbir sayfayı göremez.
- Roller: **Personel** (kendi bakiyesi ve talepleri) · **Yönetici** (biriminin taleplerini
  onaylar/reddeder) · **IK** (tüm personel, geriye dönük giriş).
- Yetki kontrolü sunucu tarafında, domain'e girmeden önce web katmanında yapılır ve domain
  servisi çağıranın rolünü parametre olarak alır. UI'da bir butonu gizlemek yetkilendirme sayılmaz.
- *Bugün:* kimlik doğrulama yok, herkes her şeyi görür ve herkes adına talep girebilir.
  Giriş sistemi ayrı bir feature'dır (açık karar, `docs/domain.md` OD-7).

## Dependencies
- Her yeni paket plan aşamasında gerekçesiyle önerilir ve **insan onaylar**.
- Kontroller: lisans MIT/BSD/Apache-2.0 uyumlu olmalı, aktif bakımda olmalı, `pip-audit` bilinen
  bir CVE göstermemeli.
- Sürümler `requirements*.txt` içinde `==` ile sabitlenir. Yükseltmeler ayrı ve dar commit'lerle yapılır.

## Review lens
Security is a mandatory dimension of every independent review (see `prompts/review.md`), not a
separate afterthought phase.
