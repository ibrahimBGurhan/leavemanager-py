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

## Review triage (round 1, İbrahim Gürhan, 2026-11-04)
Bağımsız review (read-only reviewer subagent, HEAD `231e585`): güvenlik ve doğrulukta bulgu yok;
3 Low + 1 Info, hepsi test/bakım. Fix round 1 yalnız `tests/test_csrf.py`'ye dokundu; her
düzeltme scratch kopyada bir mutantla kırmızıya döndürüldü.
- **F-1 — real → fix-1 (`dbd17fb`):** ortak istemci CSRF kapalı çalıştığı için ileride token'sız
  eklenen bir POST formu testlerden geçerdi. Yeni test, argümansız her GET sayfasını CSRF açık
  ziyaret eder ve token'sız POST formu olan sayfaları listeler. Yeni bir ekrana token'sız form
  ekleyen mutant: test `['/yeni-ekran']` ile kırmızı, paketin geri kalanı yeşil.
- **F-2 — real → fix-1 (`3a3da55`):** "bozuk / başka oturum" testi yalnız `new` ve `approve`'u
  sınıyordu; CB-2 üç işlemi de istiyor. Artık `reject` de var; red rotasını muaf tutan mutant
  `reject-bozuk` ve `reject-baska-oturum`'da kırmızı.
- **F-3 — real → fix-1 (`1196b86`):** `test_secret_never_in_logs`'un ilk assert'i hiç
  kırılamıyordu. Test artık çalışan uygulamaya bilinen bir anahtar verir; anahtarı ya da üretilen
  token'ı log'a yazan mutantlar kırmızı. *Round 2 düzeltmesi:* "kırılamaz" öncülü eksikti; silinen
  çağrı bir regresyon korumasıydı (F-5), ve gönderilen token'ın loglanması bu testte sınanmıyordu
  (F-7). İkisi fix-2 ile kapandı.
- **F-4 — noise:** `conftest.py` satırı global yapılandırmayı geri almıyor. Spec PB-3 ve plan bu
  satırı birebir onayladı; mevcut `app.testing = True` kalıbıyla aynı; bugün sıraya bağımlılık
  yok (`csrf_client` `monkeypatch` kullanıyor). Değiştirmek korumalı dosyada yeni bir değişiklik
  ve R-08 olurdu.

## Review triage (round 2, İbrahim Gürhan, 2026-11-04)
Bağımsız review, fix diff `231e585..d912a81`: F-1 ve F-2 düzeltmeleri doğrulandı (mutantlarla);
F-3 kısmen. Fix round 2 yine yalnız `tests/test_csrf.py`; her düzeltme bir mutantla gösterildi.
- **F-5 — real → fix-2 (`9a5a5d7`):** fix-1'in getirdiği regresyon. F-3'te silinen
  `load_secret_key({"SECRET_KEY": …})` çağrısı, ortamdan gelen anahtarın loglanmasına karşı tek
  korumaydı. Aynı teste aynı bilinen değerle geri eklendi; anahtarı loglayan mutant paketin
  tamamında tek kırmızı verir.
- **F-6 — madde 1 real → fix-2 (`6e5b9ff`); madde 2–4 noise:** form taraması artık
  `method = "post"` (boşluklu) yazımını da yakalar; önceki desen bu mutantı geçiriyordu. Noise
  gerekçesi: açılış etiketindeki `>`, `formmethod="post"` ve argümanlı GET sayfaları bugün yok;
  sağlam çözüm (HTML ayrıştırıcı, argüman üretme) en küçük değişiklik kuralını aşar; argümanlı
  sayfa sınırı testin docstring'inde yazılı.
- **F-7 — real → fix-2 (`28ea78a`):** bozuk / başka oturum testleri artık gönderilen token'ın hiçbir
  log kaydında olmadığını da doğrular; onu loglayan mutant 6 örneğin hepsinde kırmızı. Round 1
  F-3 kaydındaki aşırı iddia düzeltildi.
- **F-8 — ship'te:** plan haritası (CB-1 yeni test, CB-2 üç işlem, PB-4) ship sırasında gerçek
  test adlarıyla hizalanır (0010 G-4 ile aynı uygulama).

## Scorecard (fill at ship — honest numbers make the process improvable)
| Metric | Value |
|---|---|
| Spec revisions | |
| Fix rounds | |
| Review findings: real / noise | |
| Regressions introduced | |
| Bugs escaped to production | |
