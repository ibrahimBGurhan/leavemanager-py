# Spec 0004 — exec-bits-ceiling-test (mini)

- Status: Shipped
- Mode: lite
- Plan: `specs/plans/0004-plan.md`
- Source: #9
- Design: —
- Supersedes: —

## Intent
Exec-bit kontrolü, proje kökünün üstündeki bir depoyu hiçbir zaman yargılamaz (0002/CB-5,
0003/PB-1). Bunu, sınır (ceiling) yolunu fiziksel yola çevirerek sağlıyor; böylece Windows'taki
kısa adlar ve link yolları doğru karşılaştırılıyor (plan 0003, Risk 3). Bugün bu davranış doğru,
ama onu koruyan bir test yok: spec 0003 VERIFY'ında bu çeviri kaldırıldığında bütün testler yine
geçti (mutant M8, açık G2). Bu iş davranışı değiştirmez; yalnızca bir refactor'ın onu sessizce
bozamamasını sağlar.

Triage kaydı (#9, 2026-11-02): rubrik TRIVIAL çıkardı, ancak trivial lane'in "yeni bir test →
yeniden triage" kuralı nedeniyle insan kararıyla CHANGE lane'de, mini-spec ile yürütülüyor.

## Changed behavior
none — no observable behavior change. Kanıtı aşağıdaki Preserved behavior kriterleri taşır.

## Preserved behavior
- [x] PB-1 — Sınır, proje kökünün üst dizinine fiziksel yolundan farklı bir yazımla verildiğinde
  ve o üst dizinde bir `.git` bulunduğunda (ör. boş bir `.git` dizini), araç o depoyu yargılamaz:
  atlandığını söyleyen notu yazar ve 0 ile çıkar. İki yazım sınanır:
  - **Windows 8.3 kısa adı** (yalnızca Windows);
  - **üst dizini gösteren bir symlink** (her platform).
- [x] PB-2 — Bu davranış testlerle kilitlenir: sınırı fiziksel yola çevirmeyen bir araç (QA'nın
  M8 mutantı) Windows'ta ve Linux'ta (CI) en az birer testte kırmızıya düşer. Bugünkü araçla
  aynı testler yeşildir.
- [x] PB-2a — Ortam senaryoyu kuramıyorsa ilgili varyant gerekçesiyle atlanır: birimde 8.3 kısa
  ad üretimi kapalıysa kısa ad varyantı, symlink oluşturma yetkisi yoksa (ör. Windows'ta
  geliştirici modu kapalı) symlink varyantı. Bu bir "yeşile ulaşmak için atlama" değildir; diğer
  varyant korumayı sürdürür. CI'da (Linux) symlink varyantı atlanmaz.
- [x] PB-3 — Mevcut davranış ve testler aynen kalır: `tests/test_exec_bits.py`'deki mevcut
  testlerin hiçbiri değişmez, zayıflatılmaz ya da silinmez; `tools/check_exec_bits.py` ve
  `scripts/check.conf` değişmez.
- [x] PB-4 — ANEW core dosyaları değişmez (`git diff main -- scripts/doctor scripts/check
  scripts/residue scripts/selftest scripts/init` boş), `./scripts/selftest` 82/82 geçer,
  `./scripts/residue` ve `--fast` CLEAN.
- [x] PB-5 — CI (`doctor` ve `check` işleri) PR'da yeşildir.

## Out of scope
- Aracın davranışını değiştirmek.
- 0003 review round 1 F1 (araç `.git` dizininin kendisiyle çağrıldığında) — noise kararı geçerli.
- `check.conf`'taki `pwd -P` satırını değiştirmek.

## Verification (VERIFY, 2026-11-02, HEAD `6bd96ca`, bağımsız QA subagent; CI ile @ `3bbebe9`)
Testler `tests/test_exec_bits.py` içinde. M8 mutantı = `find_dot_git`'te
`{pathlib.Path(p).resolve()` → `{pathlib.Path(p)` (ceiling çözülmüyor).

| Kriter | Kanıt | Durum |
|---|---|---|
| PB-1 (kısa ad, Windows) | `::test_ceiling_given_as_a_short_name_is_honoured` — `CHECK GREEN (full, 3 steps, 8 s)` içinde koştu ve geçti | Pass |
| PB-1 (symlink) | `::test_ceiling_given_through_a_symlink_is_honoured` — Windows'ta `1314` ile atlandı; Linux CI'da koştu ve geçti (aşağıdaki sayım) | Pass |
| PB-2 (Windows) | Önce/sonra, scratch kopyada: `main`'in test seti + M8 → `18 passed, 4 skipped` (yeşil); HEAD'in test seti + M8 → `test_ceiling_given_as_a_short_name_is_honoured` FAILED (`assert 1 == 0`, dış depo yargılandı); bugünkü araçla `19 passed, 5 skipped` | Pass |
| PB-2 (Linux) | Akıl yürütme, gözlem değil (plan Risk 1, kabul edildi). Destek: Windows'ta junction ile çözülmemiş ceiling'in dış `.git`'i bulduğu gözlendi (M8 → exit 1, bugünkü araç → exit 0) | Kabul edilmiş risk |
| PB-2a | Skip koşulları koddan: 8.3 kapalıysa kısa ad testi atlanır; symlink testi yalnızca Windows + `winerror 1314`'te atlanır, POSIX'te `raise`. Linux CI'da symlink testi atlanmadı | Pass |
| PB-3 | `tests/test_exec_bits.py`'den silinen satır 0 (yalnızca 49 satır ekleme); `git diff main -- tools/ scripts/check.conf` boş | Pass |
| PB-4 | core diff boş; `./scripts/selftest` 82 passed, 0 failed; `RESIDUE CLEAN (full, 2 runs)` / `(fast, 2 runs)` | Pass |
| PB-5 | PR #10: run 41501091078 (pull_request) ve 41499933453 (push), ikisi de `3bbebe9`: `check` → `67 passed, 1 skipped`, `CHECK GREEN (full)`; `doctor` → selftest 82/82 | Pass |

Kayıtlar:
- Linux CI sayımı: 0003'te `66 passed, 0 skipped`; bu iş 2 test ekledi → 68. Linux'ta atlanan tek
  test, `skipif(sys.platform != "win32")` taşıyan kısa ad testi. Symlink testinin POSIX'te atlama
  yolu yok (hata `raise` eder), bu yüzden yeşil CI onun koştuğunu gösterir.
- Windows'ta `63 passed, 5 skipped` (4 POSIX'e özel test + yetkisiz symlink testi).
- VERIFY F-a (kısa ad API'si başarısız olursa da skip) noise; gerekçe planda.

## Definition of Done
- [x] `scripts/check` green
- [x] Independent review done; real findings fixed, noise rejected with written rationale
- [x] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots)
- [x] Spec moved to `specs/done/` (immutable there)

## Scorecard (fill at ship — honest numbers make the process improvable)
| Metric | Value |
|---|---|
| Spec revisions | 0 (self-critique maddeleri onaydan önce eklendi) |
| Fix rounds | 1 |
| Review findings: real / noise | 1 / 1 (round 1 F1 real; VERIFY F-a noise) |
| Regressions introduced | 0 |
| Bugs escaped to production | 0 (henüz yayında değil) |
