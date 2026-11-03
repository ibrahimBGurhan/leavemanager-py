# Spec 0006 — refactor-layers (mini)

- Status: Shipped
- Mode: lite
- Plan: `specs/plans/0006-plan.md`
- Source: #13
- Design: —
- Supersedes: —

## Intent
`app.py` bugün web, iş kuralları ve veriyi tek dosyada tutuyor. Bu iş onu
`docs/architecture.md`'deki üç katmana ayırır: `web → domain → storage`. Böylece iş kuralları
Flask olmadan sınanabilir hale gelir ve ileride kalıcı veritabanına geçiş yalnızca `storage`'ı
değiştirir. Ürün davranışı değişmez. Testler spec 0005'te bu işe hazırlandı; mevcut testlerin
hiçbiri değişmez.

## Changed behavior
none — no observable behavior change.

## Preserved behavior
- [x] PB-1 — Ürün davranışı aynen kalır: ana sayfa, talepler ekranı, yeni talep formu ve
  gönderimi (geçerli talep, yetersiz bakiye, bozuk girdi, geçmiş tarih) `main` ile bayt düzeyinde
  aynı yanıtı verir (durum kodu, yönlendirme adresi, gövde). Karşılaştırma birden çok "bugün"
  tarihinde, farklı yıllar dahil, yapılır.
- [x] PB-2 — Mevcut testler hiç değişmez: `git diff main -- tests/` yalnızca PB-5'teki yeni dosyayı
  gösterir; mevcut test dosyaları bayt düzeyinde aynıdır. Full profil yeşil, ters sırada da
  (`ANEW_REVERSE_ORDER=1`). Gereken bir test değişikliği davranış değişikliği demektir: iş durur,
  insana sorulur.
- [x] PB-3 — Bağlantı noktaları korunur (spec 0005 taahhüdü): `app.py` composition root olarak
  kalır ve `app.clock`, `app.storage`, `app.svc`, `app.app` adlarını aynı anlamla korur.
  `storage.employees()/requests()` bu anahtarlara sahip sözlükler döndürür; `add_*` aynı biçimi
  kabul eder. `python app.py` uygulamayı eskisi gibi başlatır.
- [x] PB-4 — "Bugün" dışarıdan verilir ve tek kaynaktan gelir: `domain` `datetime.now()` /
  `date.today()` çağırmaz; servis saati ve depoyu kurulumda parametre olarak alır. Kanıt yöntemi
  (spec 0005 F-1): bir kopyada gerçek saat başka bir yıla kaydırılır; kod olduğu gibiyken testler
  yeşil, servis saati yok sayınca kırmızı.
- [x] PB-5 — Katman kuralları test edilir: yeni bir mimari testi (`tests/test_architecture.py`,
  import taraması) `docs/architecture.md`'deki yasakları sınar:
  - `domain` `flask`, `werkzeug` veya `jinja2` import etmez;
  - `domain` HTML üretmez;
  - `web`, `storage`'ı doğrudan import etmez;
  - SQL kütüphaneleri yalnızca `storage`'da bulunur.

  Her kural, bilerek bozulmuş bir kopyada kırmızıya düşer.
- [x] PB-6 — Geri kalan her şey aynen kalır: `tests/test_exec_bits.py`, `tools/`,
  `scripts/check.conf` ve ANEW core dosyaları değişmez; `./scripts/selftest` 82/82; residue CLEAN;
  PR'da CI yeşil. Yeni bağımlılık yok.

## Kararlar (spec onayında, İbrahim Gürhan, 2026-11-03)
- **K-1 — Durum rozeti `web`'e taşınır**, çıktısı bayt düzeyinde aynı kalır. `test_status_badge`
  rozeti ekrandan okuduğu için (spec 0005) test değişmez. #13'teki "taşınırsa teste dokunulur"
  notu yanlıştı; #13'e düzeltme yorumu yazılır. Markup değişikliği (F-3) kapsam dışı kalır.
- **K-2 — Mimari testi bu işte eklenir** (PB-5): yeni dosya; mevcut testler değişmez (PB-2).
- **K-3 — Yerleşim:** kökte `domain/`, `storage/`, `web/` paketleri; `SystemClock` `app.py`'de
  (composition root); `LeaveService(clock, storage)`; route'lar veriye servisin salt okuma
  fonksiyonları üzerinden erişir.
- **K-4 — Belgeler bu işte güncellenir:** `docs/architecture.md` "Bugünkü durum",
  `docs/testing.md:19` (spec 0005 N-1).

## Out of scope
- Herhangi bir davranış değişikliği: OD-1…OD-8, BR-9, kalıcılık (SQL), kimlik doğrulama.
- HTML'in Jinja şablon dosyalarına taşınması ve rozet markup'ının değişmesi (F-3).
- mypy (`docs/testing.md`: "refactor sonrası") — ayrı iş.
- `create_request`'teki ölü geçmiş tarih dalının kaldırılması (spec 0005 F-2) — ayrı iş.

## Verification (VERIFY, 2026-11-03, HEAD `b2f14de`, bağımsız QA subagent; CI ile @ `b2f14de`)
Mutasyonlar ve karşılaştırma kopyaları repo dışında, scratch'te; hiçbiri commit'lenmedi.

| Kriter | Kanıt | Durum |
|---|---|---|
| PB-1 | `main` (`fe4762f`) ve HEAD kopyalarına aynı 13 istek gönderildi (3 GET, 7 POST: geçerli, yetersiz bakiye, bozuk tarih, geçmiş tarih + HTML'li neden, olmayan personel, boş neden, boş form; yeniden `/`, `/requests`, 404). Durum kodu, `Location`, gövde sha256'sı ve başlıklar 6 tarihte aynı: 2026-10-23, 2026-11-03, 2027-06-01, 2041-01-01, 2020-02-29, 2032-02-29. Tarihlerin toplam hash'leri birbirinden farklı. Karşılaştırma hatayı yakalıyor: rozetteki `.lower()` kaldırılınca iki `/requests` yanıtı farklılaşıyor | Pass |
| PB-2 | `git diff --stat main...HEAD -- tests/` yalnızca `tests/test_architecture.py`. 5 mevcut test dosyasının blob'u `main` ile aynı. Test kimlikleri 68 → 72, fark yalnızca 4 mimari testi. `./scripts/check` → `67 passed, 5 skipped`, `CHECK GREEN (full)`; `ANEW_REVERSE_ORDER=1` ile de aynı | Pass |
| PB-3 | İki kopyada seam çıktısı aynı: `clock/storage/svc/app`, url_map, kayıt anahtarları, `add_*`, `reset`. Gerçek `python app.py`: `Debug mode: off`, `GET /` 200, gövde sha256'sı main ile aynı. `test_running_app_py_does_not_force_debug_mode` yeşil; `debug=True` mutantında kırmızı | Pass |
| PB-4 | `grep -rn "datetime.now\|date.today" domain/` boş; `LeaveService(clock, storage)`. Gerçek saat 2031-03-15'e kaydırıldı: kod olduğu gibiyken `67 passed`. Mutant (`get_seniority_years` → `date.today()`) kaydırılmış saatte 16 failed, gerçek saatte (2026) `67 passed` (G-1) | Pass |
| PB-5 | Her kural mutantı yalnızca kendi testini düşürüyor (`1 failed, 3 passed`). Kural 1: flask / werkzeug / jinja2 import'u. Kural 2: `<b style…>`, `</td>`. Kural 3: `import storage`, `from storage.memory import …`, `from storage import memory`. Kural 4: domain'de, web'de, fonksiyon içinde ve `app.py`'de SQL import'u. Ters kontrol: storage'da `import sqlite3` → `4 passed` | Pass |
| PB-6 | `tools/`, `scripts/`, `tests/test_exec_bits.py`, bağımlılık dosyaları ve ANEW core diff'i boş. `./scripts/selftest` 82/82, `RESIDUE CLEAN (full, 2 runs)`, `doctor` 0 fail / 0 warn. PR #15 CI'si `b2f14de` üzerinde: run 41639378020 (pull_request) ve 41639024108 (push) başarılı; `check` → `71 passed, 1 skipped`, `CHECK GREEN (full)`; `doctor` → selftest 82/82 | Pass |

Kayıtlar:
- G-1: Domain'in gerçek saati okumasını, takvim yılı değişene kadar yakalayan kalıcı bir test yok. Kanıt saat kaydırmasıyla alındı. Kalıcı AST kuralı ayrı bir işe bırakıldı.
- G-2: CI kanıtı PR #15'te alındı (yukarıda).
- G-3: Plandaki "`add_request` sayaca dokunmaz… testler bu davranışa bağlı" iddiası yanlış; sayaç artsa da suite yeşil kalıyor. Bu işte aksiyon yok; kalıcı DB işindeki storage sözleşme testine not edildi.
- G-4: Public yüz bilinçli olarak değişti. `svc.status_badge` kalktı; `svc.employees()`, `svc.requests()` ve `storage.next_request_id()` eklendi. PR'da belirtildi.
- G-5: Mimari testinin sınırları (parçalı HTML, `svc._storage`, dinamik import) `docs/architecture.md`'de yazılı ve review'da kontrol ediliyor.
- UI before/after screenshots: N/A. Bu iş "Changed behavior: none" ve PB-1 bütün ekranlarda HTML'in bayt düzeyinde aynı olduğunu kanıtlıyor.
- Linux CI `71 passed, 1 skipped`; Windows `67 passed, 5 skipped` (exec-bits testleri NTFS'te atlanıyor).

## Definition of Done
- [x] `scripts/check` green
- [x] Independent review done; real findings fixed, noise rejected with written rationale
- [x] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots — N/A, gerekçe yukarıda)
- [x] Spec moved to `specs/done/` (immutable there)

## Scorecard (fill at ship — honest numbers make the process improvable)
| Metric | Value |
|---|---|
| Spec revisions | 1 (BUILD'de R-07: D-1 `docs/conventions.md` kapsama; review'da D-2 `AGENTS.md`) |
| Fix rounds | 2 (fix-1 belgeler, fix-2 plan metni) |
| Review findings: real / noise | 3 / 1 (round 1: F-1, F-2 real, F-3 noise; round 2: F-1 real); VERIFY G-1…G-5 kabul, kod değişikliği gerektirmedi |
| Regressions introduced | 0 |
| Bugs escaped to production | 0 (henüz yayında değil) |
