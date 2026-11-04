# Spec 0008 — typed-domain-exceptions (mini)

- Status: Shipped
- Mode: lite
- Plan: `specs/plans/0008-plan.md`
- Source: #19
- Design: — (yeni ekran yok; mevcut "Yeni Talep" sayfasında hata mesajı gösterilir)
- Supersedes: 0001/AC-5 (kalan = gün reddi; olmayan personelde "başarılı" dönüş), 0001/AC-10
  (`ERR-412` mesajı; kalan = gün sessiz kaybı; bozuk girdi ve olmayan personelde sessiz
  yönlendirme)

## Intent
Bugün izin talebi kaydedilemediğinde kullanıcı çoğu zaman bunu fark etmiyor. Talepler listesine
yönlendiriliyor ve talebinin kaydedildiğini sanıyor. Bakiye yetersiz olduğunda ise ekranda iç
hata kodu ve dahili telefon numarası görüyor.

Bu iş, talebin neden kaydedilemediğini kullanıcıya anlaşılır bir Türkçe mesajla söyler. Başarısız
bir talebi başarılı gibi göstermez. Bakiye kararı tek yerde verilir. İş kuralı ihlalleri domain'de
tipli istisnalar olarak ifade edilir (`docs/conventions.md`, Error handling).

## Changed behavior
Tüm örnekler bugün = 2026-10-23 ve açılış verisi içindir. "Mesaj gösterilir" şu anlama gelir:
- Yeni Talep sayfası, formun üstünde mesajla birlikte yeniden gösterilir.
- Kayıt oluşmaz.
- Kullanıcı talepler ekranına yönlendirilmez.
- HTTP durumu, iş kuralı ihlalinde ve bozuk girdide **400**, beklenmeyen hatada **500** olur (S-1).
- Birden çok ihlal varsa yalnızca ilkinin mesajı gösterilir. Sıra: bozuk girdi → olmayan personel
  → ters tarih → bakiye (S-4).

- [x] CB-1 — **Bakiye (BR-6 kararı):**
  - Talep, Kalan ≥ izin günü ise kaydedilir. Bakiyeyi tam kullanan talep kabul edilir (ör. Zeynep
    Kaya, kalan 14, 14 günlük talep → kaydedilir).
  - Kalan < izin günü ise kalanı ve talep edilen günü söyleyen bir mesaj gösterilir (S-2). Örnek:
    Elif Sahin, kalan 0, 1 günlük talep → "Kalan izin bakiyeniz yetersiz (kalan 0 gün, talep
    1 gün)."
  - Mesajda iç kod (`ERR-…`), dahili telefon ya da "IT'ye bildirin" yoktur.
  - Ekran ve servis aynı kararı verir: kalan − 1, kalan ve kalan + 1 gün için sonuç ikisinde de
    aynıdır.
- [x] CB-2 — **Olmayan personel:** Formda var olmayan bir personel numarası gönderilirse
  "Seçilen personel bulunamadı." mesajı gösterilir (ör. 99).
- [x] CB-3 — **Tarih aralığı (BR-9):**
  - Bitiş tarihi başlangıçtan önceyse "Bitiş tarihi başlangıç tarihinden önce olamaz." mesajı
    gösterilir.
  - Bitiş = başlangıç geçerlidir ve 1 gün sayılır.
- [x] CB-4 — **Bozuk ya da eksik girdi:** Aşağıdaki durumlarda "Lütfen personeli ve geçerli
  başlangıç ve bitiş tarihlerini girin." mesajı gösterilir:
  - tarih biçimi geçersiz (ör. `16.11.2026`);
  - tarih alanı boş;
  - personel numarası sayı değil ya da eksik.
- [x] CB-5 — **Beklenmeyen hata:**
  - Talep kaydedilirken beklenmeyen bir hata olursa "Talep kaydedilemedi. Lütfen daha sonra
    tekrar deneyin." mesajı gösterilir.
  - Hata, stack trace'iyle uygulama loguna yazılır.
  - Kullanıcıya istisna metni, stack trace ya da iç ayrıntı gösterilmez.
- [x] CB-6 — **Domain sözleşmesi:**
  - Talep oluşturma, iş kuralı ihlalinde tipli bir istisna fırlatır: `InsufficientBalance`,
    `EmployeeNotFound`, `InvalidDateRange`.
  - `InsufficientBalance`, kalan gün sayısını ve talep edilen gün sayısını taşır (S-2).
  - Başarısızlığı dönüş değeriyle bildirmez ve hata yutmaz.
  - Olmayan personel ve yetersiz bakiye için servisi doğrudan çağıran da istisnayı alır.
- [x] CB-7 — **Belgeler kararları söyler (S-6):**
  - `docs/domain.md`: BR-6, Kalan ≥ gün kabul edilir şeklinde yazılır; "[IK onayı bekliyor]"
    ve "mevcut kod tutarsız" notları kalkar. BR-9 talep oluştururken uygulanır. Invariant'taki
    "bugün ihlal ediliyor" notu güncellenir.
  - `docs/architecture.md`: "Tipli domain istisnaları yok" hedeften kalan farklar listesinden
    çıkar.

## Preserved behavior
- [x] PB-1 — **Geçerli talep aynen çalışır:**
  - Kullanıcı talepler ekranına yönlendirilir ve talep `Beklemede` durumuyla, sıradaki numarayla
    (9) listelenir.
  - Nedeni boş bırakılmış talep yine kaydedilir.
  - Geçmiş tarihli talep kabul edilir (BR-8).
  - Servis, başarılı oluşturmada bugünkü gibi `True` döner.
- [x] PB-2 — **Diğer kurallar ve ekranlar değişmez:**
  - Hak, kıdem, kullanılan, kalan ve gün sayısı hesapları aynı kalır. `calc_days`'in ters
    aralıkta 0 dönmesi dahil (0001/AC-3); BR-9 talep oluşturmada uygulanır, hesap fonksiyonunda
    değil.
  - Ana sayfa, talepler ekranı ve yeni talep formunun alanları aynı kalır.
- [x] PB-3 — **Güvenlik:**
  - `tests/test_security.py` değişmeden yeşil kalır.
  - Hata mesajları kullanıcı girdisini HTML olarak yorumlamaz.
  - `debug` kapalı kalır.
- [x] PB-4 — **Katman kuralları:**
  - `tests/test_architecture.py` değişmeden yeşil kalır.
  - İstisnalar `domain`'de tanımlanır.
  - Türkçe kullanıcı mesajları `web`'dedir. Domain HTML ya da UI metni üretmez.
- [x] PB-5 — **Testlerde yalnızca bu spec'in değiştirdikleri değişir:**
  - Yalnızca Supersedes'te anılan davranışları sabitleyen 5 test bilinçli olarak güncellenir:
    - `test_create_request_rejects_when_remaining_equals_days_current`
    - `test_create_request_unknown_employee_reports_success_current`
    - `test_post_insufficient_balance_shows_error`
    - `test_post_remaining_equals_days_is_silently_dropped_current`
    - `test_post_invalid_input_redirects_without_saving_current`
  - Diğer mevcut testler bayt düzeyinde aynıdır.
  - Full ve ters sıra koşuları yeşil, selftest 82/82, residue CLEAN, PR'da CI yeşil.
  - Yeni çalışma zamanı bağımlılığı yok (`logging` standart kütüphane).

## Out of scope
- Split: önerilen bölünme 0008 domain istisnaları ve 0009 web mesajlarıydı. Tek tutuldu
  (İbrahim Gürhan, 2026-11-04). Kullanıcı yeteneği tek: "başarısız talep söylenir". Domain
  istisnası tek başına kullanıcıya bir şey göstermez (S-5).
- Onay/red akışı (OD-7), kimlik doğrulama, bekleyen taleplerin bakiyeden düşülmesi (OD-3), iş
  günü hesabı (OD-4).
- Rozet markup'ı ve Jinja şablonları (F-3). Mesaj bugünkü sayfa yapısı içinde gösterilir.
- Hata sonrası formun girilen değerleri koruması (S-3).
- `create_request`'teki ölü geçmiş tarih dalı (0005 F-2). BR-8 davranışı korunur.

## Verification (VERIFY, 2026-11-04, HEAD `8c3b734`, bağımsız QA subagent; CI ile @ `2cc8296`)
Mutantlar ve ekran görüntüleri repo dışında, scratch'teki `git archive` kopyalarında üretildi;
hiçbiri commit'lenmedi. Gerçek süreç `python app.py` ile koşuldu (`Debug mode: off`).

| Kriter | Kanıt | Durum |
|---|---|---|
| CB-1 | Testler: `test_post_insufficient_balance_shows_error`, `…remaining_equals_days_is_saved`, `…accepts_when_remaining_equals_days`, `…carries_remaining_and_requested`, `test_screen_and_service_agree_on_balance[13/14/15]`. Gerçek süreç: Elif 1 gün → 400, "Kalan izin bakiyeniz yetersiz (kalan 0 gün, talep 1 gün)."; Zeynep 13 gün → 302; 15 gün → 400. Sayfada `ERR-`, `4127` ve `IT'ye` yok. Mutantlar Q1 (`<=`), Q2, Q11 ve Q14 yakalandı | Pass |
| CB-2 | `test_screen_unknown_employee_shows_message` (fix-1), `test_post_invalid_input_shows_message[unknown-employee]`, `test_create_request_unknown_employee_raises`. Gerçek süreç: 99 → 400 ve mesaj | Pass |
| CB-3 | Ters tarih için servis ve ekran testleri; bitiş = başlangıç → 1 gün. `main`'de bu talep -1 günle kaydediliyordu. Mutantlar Q3 ve Q13 yakalandı | Pass |
| CB-4 | `test_screen_bad_input_shows_message[empty-date / non-numeric-employee / missing-employee / bad-date-before-unknown-employee]` ve `…shows_message[bad-date]`. Gerçek süreçte 4 biçimin hepsi → 400 ve aynı mesaj | Pass |
| CB-5 | `test_screen_unexpected_error_is_logged_not_shown`. Gerçek süreç: 500 ve genel mesaj; gövdede `gizli` ve `Traceback` yok; stderr'de `izin talebi kaydedilemedi` ve tam stack trace. Mutantlar Q6, Q9 ve Q15 yakalandı | Pass |
| CB-6 | Servis istisna testleri ve `test_violations_are_reported_in_order`; `except Exception: return True` kalktı. Mutant Q8 yakalandı | Pass |
| CB-7 | `docs/domain.md`: BR-6 kararı (kim, ne zaman), BR-9 ve invariant. `docs/architecture.md`: "Tipli domain istisnaları yok" maddesi kaldırıldı | Pass |
| PB-1 | Değişmeden yeşil: `test_post_valid_request_is_listed_as_pending`, `test_post_empty_reason_is_saved`, `test_create_request_saves_pending_request`, `test_create_request_accepts_past_dates`. Gerçek süreçte boş neden ve geçmiş tarih → 302 | Pass |
| PB-2 | Hesap ve ekran testleri AST düzeyinde değişmedi. GET `/`, `/requests` ve `/new` yanıtlarının sha256'sı `main` ile aynı (G-3: gözlemle) | Pass |
| PB-3 | `tests/test_security.py` blob'u `main` ile aynı ve yeşil. `Debug mode: off`. `employee_id=<script>…` → 400, girdi sayfaya yansımıyor | Pass |
| PB-4 | `tests/test_architecture.py` blob'u `main` ile aynı ve yeşil. İstisnalar yalnızca `domain/errors.py`'de; Türkçe mesajlar `web/routes.py`'de | Pass |
| PB-5 | AST karşılaştırması: yalnızca listelenen 5 test değişti (4 yeniden adlandırma, 1 gövde). Diğer test fonksiyonları aynı. `conftest`, `security`, `architecture`, `exec_bits`, `storage`, `app.py`, `scripts`, `tools` ve bağımlılık dosyaları değişmedi. Full ve ters sıra koşuları `83 passed, 5 skipped`; selftest 82/82; `RESIDUE CLEAN`. PR #22: run 41799334584 (pull_request) ve 41799280058 (push), ikisi de `2cc8296`: `check` → `87 passed, 1 skipped`, `CHECK GREEN (full)`; `doctor` → 0 fail, 0 warn, selftest 82/82 | Pass |

Kayıtlar:
- Test kimlikleri 73 → 88. Supersedes'teki 4 test yeniden adlandırıldı (eşleme planda ve VERIFY'da). `test_request_errors.py` 15 yeni kimlik getirdi (fix-1 dahil).
- Ters kontrol: HEAD'in testleri `main`'in kodu üzerinde `19 failed` veriyor.
- Review round 1: F-1 real (fix-1). VERIFY:
  - G-1: CI SHA'sı son HEAD ile eşleşti.
  - G-2: mesajın formun üstünde olduğu artık test ediliyor (fix-2; Q7 mutantı `8 failed`).
  - G-3 ve G-4 kabul (G-4 eşdeğer mutant).
  - N-1: log yapılandırması #21'e gitti.
  - `docs/security.md`'deki eskimiş not #20'ye gitti.
- UI before/after screenshots: 7 durum (GET /new, yetersiz bakiye, kalan = gün, olmayan personel, ters tarih, bozuk tarih, beklenmeyen hata) headless Chrome ile çekildi ve PR #22'ye eklendi; repoda değiller.
- Linux CI `87 passed, 1 skipped`, Windows `83 passed, 5 skipped` (exec-bits testleri NTFS'te atlanıyor).

## Definition of Done
- [x] `scripts/check` green
- [x] Independent review done; real findings fixed, noise rejected with written rationale
- [x] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots — PR #22)
- [x] Spec moved to `specs/done/` (immutable there)

## Kararlar (spec onayında, İbrahim Gürhan, 2026-11-04)
- **BR-6:** Kalan ≥ gün ise talep kabul edilir. Onaylayan: İbrahim Gürhan (IK adına),
  2026-11-04 (S-6).
- **BR-9:** Bitiş ≥ başlangıç, talep oluştururken uygulanır. `calc_days` değişmez.
- **S-1:** iş kuralı ihlali ve bozuk girdi 400, beklenmeyen hata 500.
- **S-2:** bakiye mesajı kalanı ve talep edilen günü söyler; istisna bu iki sayıyı taşır.
- **S-3:** formun değerleri koruması kapsam dışı; F-3 / Jinja işine kalır.
- **S-4:** ihlal sırası: bozuk girdi → olmayan personel → ters tarih → bakiye. Yalnızca ilk
  ihlal gösterilir.
- **S-5:** bölünmez.
- **S-6:** BR-6 kararı kayda geçti; belgeler CB-7 ile güncellenir.

## Scorecard (fill at ship — honest numbers make the process improvable)
| Metric | Value |
|---|---|
| Spec revisions | 0 (S-1…S-6 onay öncesi taslağa işlendi) |
| Fix rounds | 2 (fix-1 review F-1, fix-2 VERIFY G-2; ikisi de yalnızca test) |
| Review findings: real / noise | 1 / 0 (round 1: F-1 real; diff dışı not #20'ye); VERIFY G-1 ship'te kapandı, G-2 düzeltildi, G-3/G-4 kabul, N-1 → #21 |
| Regressions introduced | 0 |
| Bugs escaped to production | 0 (henüz yayında değil) |
