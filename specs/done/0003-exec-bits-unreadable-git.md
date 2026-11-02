# Spec 0003 — exec-bits-unreadable-git (mini)

- Status: Shipped
- Mode: lite
- Plan: `specs/plans/0003-plan.md`
- Source: #7
- Design: —
- Supersedes: 0002/CB-5 — yalnızca "`.git` olduğu hâlde git depoyu okuyamıyorsa" cümlesi: kırmızı
  artık `exec-bits` adımının kendisinden gelir. CB-5'in geri kalanı (atlama durumları) aynen geçerli.

## Intent
Proje kökünde `.git` olduğu hâlde git depoyu okuyamıyorsa (ör. dubious ownership), exec-bit
kontrolü bugün "atlandı" notu yazıp geçiyor; `./scripts/check`'i kırmızıya düşüren yalnızca
`test` adımındaki bir test. `test` adımı ileride yalnızca full profilde çalışırsa `--fast` bu
durumda yeşil kalır ve kontrol sessizce devre dışı kalır. Bundan sonra bu durum `exec-bits`
adımının kendisinde, git'in gerekçesiyle kırmızı olur; geliştirici asıl nedeni doğru adımda görür.

## Changed behavior
- [x] CB-1 — Proje kökünde bir `.git` (dizin ya da dosya) varken git depoyu okuyamıyorsa (ör.
  dubious ownership, bozuk `.git/HEAD`, var olmayan bir dizini gösteren `.git` dosyası, boş bir
  `.git` dizini), `exec-bits` adımı **kırmızıdır** ve `./scripts/check` bu adımda durur — hem
  full hem `--fast`. Araç `.git`'i başlangıç dizininde ve üst dizinlerinde arar, ama proje
  kökünün üstüne çıkmaz (git'in kendi arama kuralı ve `GIT_CEILING_DIRECTORIES` sınırı ile aynı);
  böylece bir alt dizin argümanıyla çalıştırıldığında da aynı sonuç alınır.
- [x] CB-2 — Bu durumda çıktı `exec-bits:` ile başlayan tek bir satırdır ve git'in kendi hata
  gerekçesini (git'in hata çıktısının ilk satırı) içerir. "skipped" kelimesi geçmez.
- [x] CB-3 — Bu durumda araç tek başına çalıştırıldığında da başarısız biter: çıkış kodu, ihlal
  bulunduğundaki kodla aynıdır (1). `./scripts/check`'in `test` adımı çalışmasa bile sonuç
  kırmızıdır.

## Preserved behavior
- [x] PB-1 — Atlama durumları değişmez (0002/CB-5): proje kökünde `.git` yoksa — zip/`git archive`
  kopyası, başka bir deponun içine açılmış kopya, kopyaya bir link/junction üzerinden girilmesi —
  `exec-bits` atlandığını söyleyen tek satırlık notu yazar ve `./scripts/check` (full ve `--fast`)
  yeşildir. Proje kökünün üstündeki bir depo hiçbir zaman yargılanmaz.
- [x] PB-2 — `git` kurulu değilken araç `NOTE: exec-bit check skipped - git is not installed`
  yazar ve 0 ile çıkar. Öncelik: git kurulu değilse proje kökünde `.git` olsa da atlanır — git
  yokken deponun okunabilir olup olmadığı bilinemez.
- [x] PB-3 — 0002'nin CB-1…CB-4 davranışları (ihlal raporu ve düzeltme komutu, `adapters/` hariç
  tutulması, shebang'siz dosyalar, symlink/submodule girdileri) ve var olmayan dizin argümanında
  exit 2 aynen kalır. `tests/test_exec_bits.py`'deki mevcut testlerin hiçbiri zayıflatılmaz ya da
  silinmez.
- [x] PB-4 — ANEW core dosyaları değişmez (`git diff main -- scripts/doctor scripts/check
  scripts/residue scripts/selftest scripts/init` boş), `./scripts/selftest` 82/82 geçer,
  `./scripts/residue` ve `--fast` CLEAN.
- [x] PB-5 — CI (`doctor` ve `check` işleri) PR'da yeşildir; Windows'ta atlanan testler Linux'ta
  koşar ve geçer.

## Out of scope
- `test` adımını full-only'ye taşımak ya da `check.conf` profillerini değiştirmek.
- Dubious ownership'i otomatik çözmek (`safe.directory` eklemek vb.): kontrol yalnızca raporlar.
- `GIT_DIR` / `GIT_WORK_TREE` gibi ortam değişkenleriyle dışarıdan verilen depolar.
- 0002'nin round 4a'da noise kararı verilen kök adı (`\n` ile biten) durumu.
- `test_current_repository_passes`'ın davranışı: `.git` varken katı assert'leri aynen kalır
  (çift güvence).

## Verification (VERIFY, 2026-11-02, HEAD `34a32c4`, bağımsız QA subagent; PB-5 CI ile @ `93c2e93`)
Testler `tests/test_exec_bits.py` içinde. Kırmızıya düşebildikleri, aracın scratch kopyalarında
10 mutasyonla gösterildi (9'u yakalandı; M8 aşağıda).

| Kriter | Kanıt | Durum |
|---|---|---|
| CB-1 | `::test_unreadable_git_fails_the_step[dubious, corrupt-head, dangling-gitfile, empty-git-dir]`, `::test_unreadable_git_is_found_from_a_subdirectory`, `::test_unreadable_git_above_the_ceiling_is_not_judged`. Önce/sonra gözlemi (scratch clone'lar, full + `--fast`): bozuk `.git/HEAD` → `main`'de `CHECK FAILED … at step: test`, HEAD'de `CHECK FAILED … at step: exec-bits`; `GIT_TEST_ASSUME_DIFFERENT_OWNER=1` → `main`'de **CHECK GREEN**, HEAD'de `CHECK FAILED … at step: exec-bits` | Pass |
| CB-2 | `::test_unreadable_git_fails_the_step` (tek `exec-bits:` satırı, git'in gerekçesi canlı karşılaştırılır, `skipped` yok) | Pass |
| CB-3 | `::test_unreadable_git_fails_the_step` (exit 1); araç tek başına exit 1 (kök, alt dizin argümanı, ceiling'siz) | Pass |
| PB-1 | `::test_skips_outside_a_git_work_tree`, `::test_current_repository_passes`, `::test_unreadable_git_above_the_ceiling_is_not_judged`; `git archive` kopyası, `bad.sh`'li dış deponun içindeki kopya, junction yolu → full + `--fast` NOTE + `CHECK GREEN`; dış deponun `.git/HEAD`'i bozukken de yeşil | Pass |
| PB-2 | `::test_skips_when_git_is_not_installed`, `::test_git_missing_wins_over_an_unreadable_git` | Pass |
| PB-3 | 0002'nin 15 testi değişmeden geçiyor; `tests/test_exec_bits.py`'den silinen satır yok; `::test_missing_directory_argument_is_a_usage_error` geçiyor | Pass |
| PB-4 | core diff boş; `./scripts/selftest` 82 passed, 0 failed; `RESIDUE CLEAN (full, 2 runs)` / `(fast, 2 runs)` (ilk turlardaki survivor'lar ilgisiz Windows süreçleri) | Pass |
| PB-5 | PR #8: run 41490112844 (pull_request) ve 41489900739 (push), ikisi de `93c2e93`: `check` → `66 passed` (0 skipped), `CHECK GREEN (full)`; `doctor` → selftest 82/82 | Pass |

Kayıtlar:
- Windows'ta `62 passed, 4 skipped`; Linux CI'da `66 passed` — POSIX'e özel 4 test ve `dubious`
  vakası Linux git'inde koştu (plan Risk 1 kapandı).
- G2 (real, düşük, ertelendi): ceiling yolunun `resolve()` edilmesini koruyan test yok (mutant M8
  hayatta). `scripts/check` hattından ulaşılamaz; kısa adlı test varyantı bir sonraki değişiklikte.
- Review round 1 F1 noise (araç `.git` dizininin kendisiyle çağrılınca kırmızı); gerekçe planda.

## Definition of Done
- [x] `scripts/check` green
- [x] Independent review done; real findings fixed, noise rejected with written rationale
- [x] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots)
- [x] Spec moved to `specs/done/` (immutable there)

## Scorecard (fill at ship — honest numbers make the process improvable)
| Metric | Value |
|---|---|
| Spec revisions | 0 (self-critique maddeleri onaydan önce eklendi) |
| Fix rounds | 0 |
| Review findings: real / noise | 0 / 1 (VERIFY: G2 real, düşük, ertelendi) |
| Regressions introduced | 0 |
| Bugs escaped to production | 0 (henüz yayında değil) |
