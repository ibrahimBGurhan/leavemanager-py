# Spec 0011 — csrf-koruma (mini)

- Status: In progress
- Mode: lite
- Plan: `specs/plans/0011-plan.md`
- Source: #25
- Design: — (yeni ekran yok; mevcut Yeni Talep ve Talepler sayfalarında hata mesajı gösterilir)
- Supersedes: — (token'sız POST'un kabul edildiğini söyleyen bir kriter yok; davranış
  `docs/security.md`'deki kurala uyarlanıyor)

## Intent
Bugün uygulama açıkken başka bir sitedeki bir form, kullanıcının haberi olmadan izin talebi
girebiliyor, bir talebi onaylayabiliyor ya da reddedebiliyor. Spec 0010'la birlikte durum
değiştiren iki işlem daha eklendi ve risk büyüdü. Bu iş, `docs/security.md`'nin istediğini
uygular: durum değiştiren her form bir CSRF token'ı taşır. Token'sız ya da geçersiz token'lı
istek hiçbir şeyi değiştirmez ve kullanıcı anlaşılır bir Türkçe mesaj görür. Uygulamanın gizli
anahtarı (`SECRET_KEY`) koddan değil ortamdan gelir.

## Changed behavior
"Korunan istek" şu üç işlemdir: Yeni Talep kaydı, onay, red. "Geçerli token" = uygulamanın aynı
tarayıcı oturumu için ürettiği ve formda gönderilen token.

- [ ] CB-1 — **Formlar token taşır:** Yeni Talep formu ile Talepler ekranındaki her "Onayla" ve
  "Reddet" formu geçerli bir CSRF token'ı içerir. Kullanıcı ekrandan çalıştığında talep
  oluşturma, onay ve red bugünkü gibi çalışır (yönlendirme, mesaj, kayıt).
- [ ] CB-2 — **Token'sız ya da geçersiz token'lı istek reddedilir:** üç korunan işlemin her
  birinde token yoksa, bozuksa ya da başka bir oturuma aitse:
  - hiçbir kayıt oluşmaz ya da değişmez;
  - yanıt **400** olur;
  - "Form geçersiz ya da süresi dolmuş. Lütfen sayfayı yenileyip tekrar deneyin." mesajı
    gösterilir: Yeni Talep'te formun üstünde, onay ve redde Talepler listesinin üstünde;
  - Flask'ın İngilizce hata sayfası, istisna metni ya da iç ayrıntı gösterilmez.
- [ ] CB-3 — **Gizli anahtar ortamdan gelir (D2):**
  - `SECRET_KEY` ortam değişkeninden okunur; değer koda, repoya ya da log'a yazılmaz.
  - Tanımlı değilse uygulama yine açılır, süreç başına rastgele bir anahtar kullanır ve log'a
    anahtarın değerini içermeyen **tek** bir WARNING satırı yazar. Satır `app.secrets` logger'ından
    gelir (K-1), ör. `… WARNING app.secrets: SECRET_KEY tanımlı değil; …`. Bu durumda yeniden
    başlatma, açık formların token'larını geçersiz kılar.
  - Token'ın süre sınırı yoktur; tarayıcı oturumu boyunca geçerlidir (K-2).
  - Repoda `.env.example` bulunur ve `SECRET_KEY` için bir yer tutucu içerir (gerçek değer değil).
- [ ] CB-4 — **Belgeler güncel:** `docs/security.md` "Bugün" notundan CSRF eksikliği kalkar;
  CSRF'in nasıl sağlandığı ve `SECRET_KEY` yoksa ne olduğu yazılır. Yeni bağımlılıklar
  (Flask-WTF ve onun getirdiği WTForms, K-5) `requirements.txt`'de `==` ile sabitlenir ve `docs/conventions.md` sürüm satırına eklenir.

## Preserved behavior
- [ ] PB-1 — **Görüntüleme ve ekranlar değişmez:** GET istekleri token istemez. Ana sayfa,
  Talepler ve Yeni Talep ekranlarının görünen alanları, tablo hücreleri, hesapları ve 0008/0010
  mesajları aynı kalır. Talepler ekranındaki Durum hücresinin görünen metni yine yalnız durumdur.
- [ ] PB-2 — **İş kuralları ve hata kodları değişmez:** geçerli token'lı isteklerde 0008 ve
  0010'un tüm davranışları aynıdır: ihlal sırası, 400/404/500 kodları, mesaj metinleri, PRG ve
  başarı mesajının durum eşleşmesi.
- [ ] PB-3 — **Testler (D3):**
  - Mevcut test dosyalarının gövdeleri ve assert'leri bayt düzeyinde aynı kalır. İki istisna var,
    ikisi de birer satırlık test kurgusu değişikliğidir (R-08, plan 0011 Risk 1):
    - `tests/conftest.py`: ortak test istemcisi CSRF kapalı çalışır.
    - `tests/test_logging_config.py`: süreç betiğinin `serve()` fonksiyonunda CSRF kapatılır;
      testin konusu log biçimidir, assert'ler değişmez.
  - CSRF açık çalışan ayrı testler her korunan işlemi hem geçerli hem geçersiz token'la sınar.
  - `tests/test_security.py` ve `tests/test_architecture.py` değişmeden yeşil kalır.
- [ ] PB-4 — **Güvenlik ve log:**
  - `debug` kapalı kalır. Gizli anahtar hiçbir çıktıda görünmez.
  - 0009 log biçimi ve `LOG_LEVEL` davranışı aynıdır; CB-3'ün WARNING satırı da bu biçimdedir.
    `tests/test_logging_config.py` assert'leri değişmeden yeşil kalır (K-1; kurgu satırı PB-3).
  - Oturum çerezi `HttpOnly` ve `SameSite=Lax`; `Secure` zorlanmaz (iç ağ HTTP, K-3).

## Out of scope
- Kimlik doğrulama ve roller (auth spec'i); "yalnızca IK onaylar" kısıtı.
- Başarı mesajını flash'a taşımak (0010 VERIFY I-1, #25 yorumu). Oturum bu işle geliyor, ama bu
  ayrı bir davranış değişikliği.
- HTTPS zorlaması, güvenlik başlıkları (CSP, HSTS), oturum süresi politikası.
- Kalıcı veri (OD-8); `SECRET_KEY`'in bir sır yöneticisinden okunması.
- Token hatasından sonra Yeni Talep formunun girilen değerleri koruması (0008 S-3 ile tutarlı, K-4).

## Definition of Done
- [ ] `scripts/check` green
- [ ] Independent review done; real findings fixed, noise rejected with written rationale
- [ ] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots)
- [ ] Spec moved to `specs/done/` (immutable there)

## Kararlar (triage, İbrahim Gürhan, 2026-11-04)
- **Lane:** rubrik (a) → BUG (`docs/security.md` CSRF kuralından sapma). Yeni bağımlılık plan
  onayı, yeni yapılandırma ve korumalı `conftest.py` değişikliği gerektirdiği için CHANGE lane
  (mini-spec) ile yürütülür. Demir kural geçerli: BUILD kırmızı bir yeniden üretme testiyle
  başlar ve test kalıcıdır.
- **D1:** Flask-WTF `CSRFProtect` (BSD-3). Sürüm ve `pip-audit` planda.
- **D2:** `SECRET_KEY` yoksa süreç başına rastgele anahtar + tek WARNING; uygulama açılır.
- **D3:** `conftest.py`'deki ortak istemci CSRF kapalı; korumayı ayrı, CSRF açık testler kanıtlar.
- **D4:** geçersiz/eksik token → 400, kayıt yok, Türkçe mesaj, Flask hata sayfası yok.
- **D5:** kapsam üç POST + `SECRET_KEY` + `.env.example`; flash ve auth kapsam dışı.

## Kararlar (self-critique, spec onayında, İbrahim Gürhan, 2026-11-04)
- **K-1:** anahtar uyarısı `app.secrets` logger'ından; 0009'un `app` logger'ı iddiaları korunur,
  `tests/test_logging_config.py` değişmez.
- **K-2:** token süre sınırı yok; tarayıcı oturumu boyunca geçerli.
- **K-3:** oturum çerezi `HttpOnly` + `SameSite=Lax`; `Secure` zorlanmaz.
- **K-4:** token hatasında form değerleri korunmaz (kapsam dışı).
- **K-5:** Flask-WTF ve WTForms birlikte sabitlenir; sürüm ve `pip-audit` planda.

## Spec değişikliği (R-08, plan aşamasında, İbrahim Gürhan, 2026-11-04)
- **Neden:** 0009'un süreç testi gerçek uygulamaya token'sız `POST /new` gönderiyor ve 500
  bekliyor (`tests/test_logging_config.py:49-58`). CSRF açılınca 400 alır; 30 örneğin 28'i
  kırmızıya döner. Spec yazılırken görülmedi.
- **Karar:** PB-3 ve PB-4 güncellendi: `test_logging_config.py`'nin `serve()` fonksiyonuna
  `conftest.py` ile aynı nitelikte tek satırlık CSRF kapatma eklenir. Korumanın gerçek süreçte
  çalıştığı, BUILD kanıtında ve VERIFY'da gözlemle kanıtlanır.

## Scorecard (fill at ship — honest numbers make the process improvable)
| Metric | Value |
|---|---|
| Spec revisions | |
| Fix rounds | |
| Review findings: real / noise | |
| Regressions introduced | |
| Bugs escaped to production | |
