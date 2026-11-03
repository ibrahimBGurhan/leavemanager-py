# Spec 0005 — refactor-test-seams (mini)

- Status: Shipped
- Mode: lite
- Plan: `specs/plans/0005-plan.md`
- Source: #11
- Design: —
- Supersedes: —

## Intent
Katmanlara ayırma refactor'ından (`web → domain → storage`, `docs/architecture.md`) önce,
spec 0001'in karakterizasyon testleri `app.py`'nin iç yapısından ayrılır. Testler bugün "bugün"
tarihini `app` modülündeki `datetime`'ı değiştirerek donduruyor, `Db` sınıfının alanlarına doğrudan
erişiyor ve durum rozetinin HTML'ini `LeaveService` üzerinden sınıyor. Bu yüzden katmanlara
ayırmanın ilk adımı bile test değişikliği gerektiriyor. Bu iş testleri, katman ayrımı sırasında
yerinde kalacak bağlantı noktalarına taşır; böylece bir sonraki refactor sıfır test değişikliğiyle
yapılabilir. Ürün davranışı değişmez. "Bugün"ün tek noktadan verilmesi için `app.py`'de de küçük,
davranışı değiştirmeyen bir yapı değişikliği yapılır (tek bir tarih kaynağı); PB-1 bunu kapsar.

**Test değişikliği istisnası:** `workflows/refactor.md` ve `/refactor` komutu "sıfır test
değişikliği" der. Bu iş tanımı gereği testleri değiştirir; istisna #11'de ve bu spec'in onayında
insan kararıyla verilir (İbrahim Gürhan, 2026-11-02, spec onayında). İstisna yalnızca bu iş
içindir; sonraki katman refactor'ında kural tam geçerlidir.

## Changed behavior
none — no observable behavior change.

## Preserved behavior
- [x] PB-1 — Ürün davranışı aynen kalır: ana sayfa, talepler ekranı, yeni talep formu ve
  gönderimi, hak/kıdem/kullanılan/kalan hesapları ve durum rozetleri `main` ile aynı çıktıyı
  verir. `tests/test_baseline_screens.py`'deki test fonksiyonlarının gövdeleri değişmez.
- [x] PB-2 — Karakterizasyon testlerinin hiçbiri kaybolmaz ya da zayıflamaz: `test_baseline_*`
  dosyalarındaki test kimliklerinin listesi (ad + parametre, bugün 39) `main` ile aynıdır; her
  testin beklenen değerleri aynıdır; hiçbir test silinmez, atlanmaz ya da `xfail` yapılmaz.
  Testler bulundukları dosyada ve adlarıyla kalır; böylece kimlik listesi birebir karşılaştırılır.
  `test_status_badge` aynı 7 vakayı ve aynı iki assert'i (renk, durum metni) korur, ama rozeti
  talepler ekranında okur: açılış verisinde olmayan durumdaki talep, veri bağlantı noktası
  üzerinden eklenir.
- [x] PB-3 — Testler `app.py`'nin iç yapısına doğrudan dokunmaz: `tests/` altında `app`
  modülünün `datetime` adına, `Db` sınıfının alanlarına ve `LeaveService.status_badge`'e
  doğrudan erişim yoktur. "Bugün" testlere tek bir bağlantı noktasından verilir
  (`docs/architecture.md`: "bugün dışarıdan enjekte edilir"). Kanıt: `tests/` altında
  `leave_app.datetime`, `.Db.` ve `.status_badge(` için yapılan arama boş döner (arama erişime
  bakar, test adına değil; `test_status_badge` adı PB-2 gereği kalır). Kapsam `tests/`'in
  tamamıdır, `tests/test_security.py` dahil: veri o dosyada da `storage` üzerinden eklenir,
  testin sınadığı şey ve assert'leri değişmez.
- [x] PB-4 — Bağlantı noktalarının yeterliliği kanıtlanır: iş kuralları (`LeaveService`) ve veri
  (`Db`, `seed`) repo dışında, geçici bir kopyada `app.py`'den ayrı modüllere taşındığında testler
  **hiç değiştirilmeden** yeşil kalır. Bu kopya commit'lenmez.
- [x] PB-5 — Geri kalan her şey aynen kalır: `tests/test_exec_bits.py` ve araçları değişmez;
  ANEW core dosyaları değişmez (`git diff main -- scripts/doctor scripts/check scripts/residue
  scripts/selftest scripts/init` boş); `./scripts/selftest` 82/82; `./scripts/residue` ve
  `--fast` CLEAN; testler rastgele sırada da aynı sonucu verir (`ANEW_REVERSE_ORDER=1`, spec
  0001/AC-11); PR'da CI (`doctor` ve `check`) yeşil.

## Spec değişikliği (BUILD sırasında, 2026-11-03)
R-07 (plan sapması) ile bulundu, İbrahim Gürhan onayladı:
- **D-1:** PB-3 `tests/`'in tamamını kapsar; `tests/test_security.py:40-44` `Db` alanlarına
  doğrudan ekleme yapıyordu ve plan bu dosyayı listelememişti. Dosya kapsama alındı.
- **D-2:** PB-3'ün arama ifadesi `status_badge` → `.status_badge(` olarak netleşti; eski ifade
  PB-2'nin koruduğu `test_status_badge` adıyla çelişiyordu. Kuralın anlamı aynı.

## Out of scope
- Katmanlara ayırmanın kendisi (`web`, `domain`, `storage` paketleri) — sonraki iş, ayrı issue.
- Herhangi bir davranış değişikliği: OD-1…OD-8, BR-9, kalıcılık, kimlik doğrulama.
- Durum rozetinin HTML'ini web'e taşımak — bu iş yalnızca testin rozeti nereden sınadığını değiştirir.
- `tests/test_exec_bits.py`.

## Verification (VERIFY, 2026-11-03, HEAD `5819c7e`, bağımsız QA subagent; CI ile @ `d7840b5`)
Mutasyonlar ve PB-4 kopyası repo dışında, scratch'te; hiçbiri commit'lenmedi.

| Kriter | Kanıt | Durum |
|---|---|---|
| PB-1 | `./scripts/check` full yeşil (63 passed, 5 skipped); `git diff main...HEAD -- tests/test_baseline_screens.py` boş; `main` ve HEAD kopyalarında tüm ekranlar + 5 POST akışı, dört tarihte (2026-10-23, 2026-11-03, 2027-06-01, 2041-01-01) bayt düzeyinde aynı çıktı (sha256) | Pass |
| PB-2 | `pytest --collect-only tests/test_baseline_*.py`: `main` ve HEAD'de aynı 39 kimlik (security 5 de aynı); beklenen değerler aynı; mutantlar M4 (rozet rengi) 1, M5 (rozet basılmıyor) 7, M6 (`reset` boş) 17, M8 (`add_request` boş) 8 test kırar | Pass |
| PB-3 | `grep -rnE 'leave_app\.datetime\|\.Db\.\|\.status_badge\(' tests/` boş; testlerin eriştiği `leave_app.*` adları yalnızca `app`, `clock`, `storage`, `svc`; `test_security.py` diff'i iki ekleme satırı, M7 (`add_employee` boş) 3 test kırar | Pass |
| PB-4 | Kopyada `LeaveService`/`SystemClock` → `domain_mod.py`, `Db`/`seed`/`MemoryStorage` → `storage_mod.py`; testler HEAD ile bayt düzeyinde aynı; `63 passed, 5 skipped`, ters sırada da yeşil. Duyarlılık: gerçek saat 2031'e kaydırılınca seam'le yeşil (S0), servis `datetime.now()` çağırınca 16 failed (S1) | Pass |
| PB-5 | core, `tests/test_exec_bits.py`, `tools/`, `scripts/` diff'i boş · `./scripts/selftest` 82/82 · `RESIDUE CLEAN (full, 2 runs)` / `(fast, 2 runs)` · `ANEW_REVERSE_ORDER=1` 63 passed · PR #12: run 41597428527 (pull_request) ve 41597344383 (push), ikisi de `d7840b5`: `check` → `67 passed, 1 skipped`, `CHECK GREEN (full)`; `doctor` → selftest 82/82 | Pass |

Kayıtlar:
- F-1: düz saat mutasyonu (M3) 2026'da yeşil kalır — donmuş ve gerçek tarih aynı yılda, kıdem yıl
  farkı. Kanıt gerçek saat başka yıla kaydırılarak alındı (M0 yeşil / M1 16 failed).
- F-2…F-5 kabul; kararlar ve ikinci aşamaya devredilenler planda.
- UI before/after screenshots: N/A — "Changed behavior: none"; PB-1 bayt düzeyinde HTML
  karşılaştırmasıyla kanıtlandı.
- Linux CI `67 passed, 1 skipped` (Windows'a özel kısa ad testi); Windows `63 passed, 5 skipped`.

## Definition of Done
- [x] `scripts/check` green
- [x] Independent review done; real findings fixed, noise rejected with written rationale
- [x] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots — N/A, gerekçe yukarıda)
- [x] Spec moved to `specs/done/` (immutable there)

## Scorecard (fill at ship — honest numbers make the process improvable)
| Metric | Value |
|---|---|
| Spec revisions | 1 (BUILD'de R-07: D-1 `test_security.py` kapsama, D-2 PB-3 arama ifadesi) |
| Fix rounds | 0 |
| Review findings: real / noise | 0 / 2 (round 1 N-1, N-2 noise); VERIFY F-1…F-5 kabul, değişiklik gerektirmedi |
| Regressions introduced | 0 |
| Bugs escaped to production | 0 (henüz yayında değil) |
