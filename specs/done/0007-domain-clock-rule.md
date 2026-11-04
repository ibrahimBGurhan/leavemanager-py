# Spec 0007 — domain-clock-rule (mini)

- Status: Shipped
- Mode: lite
- Plan: `specs/plans/0007-plan.md`
- Source: #16
- Design: —
- Supersedes: —

## Intent
Kıdem, hak ve bakiye hesapları "bugün"e bağlı. Bu yüzden domain'in saati yalnızca dışarıdan
verilen saat nesnesinden okuması gerekiyor (`docs/conventions.md`, Data rules). Bugün bunu yalnızca
dolaylı bir şey yakalıyor: testlerin sabit tarihi (2026) ile gerçek yılın farklı olması. 2026
bitene kadar domain'e eklenen bir `date.today()` çağrısı test setinde yeşil kalıyor (spec 0006
VERIFY, G-1).

Bu iş kuralı mimari testine ekliyor. Böylece ihlal, hangi yılda olursa olsun, ilk koşuda kırmızıya
düşecek. Ürünün davranışı değişmiyor.

## Changed behavior
- [x] CB-1 — Mimari testi, `domain` paketinde gerçek saate yapılan her erişimi reddeder:
  - `date.today`, `datetime.now`, `datetime.utcnow`, `datetime.today`;
  - bunların modül önekli yazımları: `datetime.date.today`, `datetime.datetime.now` vb.;
  - takma adla import edilmiş biçimleri: `from datetime import date as D` sonrası `D.today`,
    `import datetime as dt` sonrası `dt.date.today` vb. Kural, dosyanın import'larından
    `datetime` modülüne, `datetime.date`'e ya da `datetime.datetime`'a bağlanan bütün adları
    çözer.

  Kural çağrıya değil erişime bakar: çağrılmadan kullanılan bir erişim de reddedilir
  (`f = date.today`, `def x(today=date.today)`). Hata mesajı ihlalin dosyasını, satırını ve
  erişimi adıyla gösterir. Diğer mimari kuralları gibi kod import edilmeden, okunarak denetlenir.
- [x] CB-2 — Kural, saatin enjekte edildiği kullanımı yanlış yakalamaz: bugünkü domain kodu
  (`self._clock.today()`) testi geçer. Başka bir nesnenin `today`/`now` adlı metodu da kural
  dışındadır; yalnızca `date` ve `datetime` üzerinden yapılan çağrılar reddedilir.
- [x] CB-3 — Kural gerçek tarihte, saat kaydırmadan çalışır. CB-1'deki her yazım biçimi (önekli,
  takma adlı ve çağrısız erişim dahil), bilerek bozulmuş bir kopyada bu testi kırmızıya düşürür.
  Bunların arasında spec 0006'nın mutantı da var
  (`get_seniority_years` → `date.today()`); bugün gerçek tarihte (2026) yeşil kalan bu mutant
  da kırmızıya düşer.
- [x] CB-4 — Belgeler kuralı söyler:
  - `docs/architecture.md` "Forbidden dependencies" listesine 5. kural eklenir: domain gerçek
    saati okumaz.
  - `docs/conventions.md` "enjekte edilen saat" kuralını "henüz araçla zorlanmayan" listesinden
    çıkarır.

## Preserved behavior
- [x] PB-1 — Ürün kodu değişmez: `app.py`, `domain/`, `storage/` ve `web/` için
  `git diff main` boştur. Ekranlar ve servis aynı yanıtı verir.
- [x] PB-2 — Mevcut testler değişmez:
  - `tests/test_architecture.py`'deki dört test ve yardımcıları aynı kalır; dosyaya yalnızca yeni
    kural eklenir.
  - Diğer test dosyaları bayt düzeyinde aynıdır.
  - Mevcut 72 test kimliğinin hepsi korunur.
  - Full profil yeşildir; ters sırada da (`ANEW_REVERSE_ORDER=1`).
- [x] PB-3 — Geri kalan her şey aynen kalır:
  - `scripts/check.conf`, `tools/`, ANEW core ve bağımlılıklar değişmez;
  - `./scripts/selftest` 82/82, residue CLEAN, PR'da CI yeşil.

## Out of scope
- `web`, `storage` ve `app.py`'de saat kullanımı. Composition root'taki `SystemClock` gerçek
  saati okumak zorunda; kural yalnızca domain için.
- `time` modülü (`time.time()`, `time.localtime()` vb.). Domain'de bugün `time` modülü yok.
- Saat dilimi (`Europe/Istanbul`, `docs/conventions.md`) ve timezone-aware zaman damgaları.
- Storage sözleşme testi (spec 0006 VERIFY, G-3): kalıcı DB işine kaldı.
- Mimari testinin diğer sınırları (spec 0006 G-5).

## Verification (VERIFY, 2026-11-04, HEAD `09d53d9`, bağımsız QA subagent; CI ile @ `b010b37`)
Mutantlar repo dışında, scratch'teki `git archive` kopyalarında koşuldu; hiçbiri commit'lenmedi.
Hepsi gerçek tarihte, saat kaydırmadan çalıştırıldı.

| Kriter | Kanıt | Durum |
|---|---|---|
| CB-1 | `test_domain_does_not_read_the_real_clock`. 18 mutantın her biri tam suite'te yalnızca kural 5'i düşürüyor (`1 failed, 67 passed, 5 skipped`). Mutantlar planın (b)–(j) listesi ve QA'nın kendi kurduğu k–p, X5, X6: default argüman, `DT.utcnow`, `datetime.datetime.today`, `import os, datetime as _d`, yeni bir domain alt modülü, `staticmethod(date.today)`, `.today.__call__()`, parantezli ad. Hata mesajı dosya:satır ve yazıldığı haliyle ifadeyi gösteriyor (ör. `domain/leave_service.py:26 dt.datetime.now`) | Pass |
| CB-2 | HEAD'de kural yeşil. Ters kontrollerin hepsi yeşil, yanlış pozitif yok: R1 enjekte saat, R2 `date(…)` / `fromisoformat` / `strptime` / `min` / `max`, R3 göreli `.datetime`, R4 import yokken yerel `date`, R5 yorum ve string, R6–R7 `web/` ve `app.py`'de `datetime.now()`, R8 `timezone.utc` ve `self._storage.today`. S-3'te kabul edilen gölgeleme beklendiği gibi kırmızı | Pass |
| CB-3 | Mutant (a) (`get_seniority_years` → `date.today()`, 0006): HEAD testleriyle `1 failed, 67 passed` → `domain/leave_service.py:26 date.today`. Aynı mutant `main`'in test dosyasıyla (kural yok) `67 passed, 5 skipped` | Pass |
| CB-4 | `docs/architecture.md`: kural 5 ve review'da kontrol edilen sınırlar eklendi: `getattr`, `__import__`, atamayla takma ad (F-1), birden çok `datetime` import'una bağlanan ad (G-2), domain dışından import. `docs/conventions.md`: enjekte edilen saat artık "zorlanır" altında | Pass |
| PB-1 | `git diff --stat main -- app.py domain storage web` boş; mevcut ekran ve servis testleri yeşil | Pass |
| PB-2 | `test_architecture.py`'den yalnızca 2 docstring satırı silindi, gerisi ekleme. Diğer 5 test dosyasının blob'u `main` ile aynı. Test kimlikleri 72 → 73, kaybolan yok. `./scripts/check` → `68 passed, 5 skipped`, `CHECK GREEN (full)`; `ANEW_REVERSE_ORDER=1` ile de aynı | Pass |
| PB-3 | `scripts`, `tools`, bağımlılık dosyaları ve `.github` diff'i boş. `./scripts/selftest` 82/82, `RESIDUE CLEAN (full, 2 runs)`, doctor 0/0. PR #18: run 41785368512 (pull_request) ve 41785343537 (push), ikisi de `b010b37`: `check` → `72 passed, 1 skipped`, `CHECK GREEN (full)`; `doctor` → 0 fail, 0 warn, selftest 82/82 | Pass |

Kayıtlar:
- F-1 real: atamayla takma ad belgeye eklendi (fix-1). F-2 noise: `resolve()` yardımcısı plandaki dosya satırında sayılmamıştı; docstring'de 1. ve 4–5. satırlar değişti. Bilinen kaçışlar X1–X4 belgede "review'da kontrol edilir" diye yazılı.
- G-1: PR CI kanıtı, son HEAD `b010b37` üzerinde PR #18'de alındı. G-2: birden çok `datetime` import'una bağlanan ad belgeye eklendi (fix-2). Fix-2 yalnızca belge ve plan metnini değiştirdiği için VERIFY yeniden koşulmadı; CI yeşil.
- UI before/after screenshots: N/A. Kullanıcı arayüzü yok, ürün kodu diff'i boş.
- Linux CI `72 passed, 1 skipped`, Windows `68 passed, 5 skipped` (exec-bits testleri NTFS'te atlanıyor).

## Definition of Done
- [x] `scripts/check` green
- [x] Independent review done; real findings fixed, noise rejected with written rationale
- [x] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots — N/A, kullanıcı arayüzü yok)
- [x] Spec moved to `specs/done/` (immutable there)

## Kararlar (spec onayında, İbrahim Gürhan, 2026-11-03)
- **S-1 — kabul:** takma adla import edilen biçimler de reddedilir (CB-1).
- **S-2 — kabul:** kural çağrıya değil erişime bakar (CB-1); çağrısız erişim de bir mutant olarak
  sınanır (CB-3).
- **S-3 — kabul, spec'e yazılmaz:** domain'de `date` adlı yerel bir değişken üzerinden yapılan
  `.today` erişimi yanlış pozitif verebilir; bugün böyle bir kod yok ve hata mesajı adı gösterir.
- **S-4 — `time` modülü kapsam dışı kalır** (Out of scope).
- **S-5 — bölünmez:** tek yetenek, 4 CB ve 3 PB.

## Scorecard (fill at ship — honest numbers make the process improvable)
| Metric | Value |
|---|---|
| Spec revisions | 0 (S-1…S-5 onay öncesi taslağa işlendi) |
| Fix rounds | 2 (fix-1 review F-1, fix-2 VERIFY G-2; ikisi de yalnızca belge) |
| Review findings: real / noise | 1 / 1 (round 1: F-1 real, F-2 noise); VERIFY G-1 ship'te kapandı, G-2 belgeye eklendi |
| Regressions introduced | 0 |
| Bugs escaped to production | 0 (henüz yayında değil) |
