# Spec 0002 — exec-bit-guard (mini)

- Status: Shipped
- Mode: lite
- Plan: `specs/plans/0002-plan.md`
- Source: #5
- Design: —
- Supersedes: —

## Intent
Windows'tan commit'lenen POSIX script'ler çalıştırma izni (exec biti) olmadan, `100644` olarak
gelebiliyor ve Linux CI'da "Permission denied" (exit 126) ile kırılıyor (PR #1). Bu durum artık
`./scripts/check` içinde, yerelde ve CI'da aynı kontrolle, sorunlu dosyanın adı ve düzeltme
komutuyla yakalanır. Kontrol projeye ait doğrulama sözleşmesinde (`scripts/check.conf`) yaşar;
ANEW core dosyası `scripts/doctor` değişmez (ANALYZE kararı, #5).

## Changed behavior
- [x] CB-1 — Git'te izlenen, `adapters/` dışında olan, ilk satırı `#!` ile başlayan ve git modu
  `100644` olan bir normal dosya varsa `./scripts/check` **kırmızıdır** (hem full hem `--fast`).
  Çıktı, böyle her dosyanın yolunu olduğu gibi (boşluk içerse de) ve
  `git update-index --chmod=+x <yol>` düzeltme komutunu yazar. Symlink (`120000`) ve submodule
  (`160000`) girdileri değerlendirilmez.
- [x] CB-2 — Böyle dosyaların hepsi `100755` ise kontrol geçer ve `./scripts/check` yeşildir.
  Bugünkü depo bu durumdadır.
- [x] CB-3 — `adapters/` altındaki shebang'li ve `100644` dosyalar raporlanmaz. Bunlar yerinde
  çalıştırılmayan şablonlardır; `scripts/init` kopyalarken izni kendisi verir.
- [x] CB-4 — Shebang'siz dosyalar (`app.py`, `scripts/check.conf`, `*.md` …) mode'larından
  bağımsız olarak raporlanmaz.
- [x] CB-5 — Git çalışma ağacı olmayan bir kopyada (ör. zip) ya da `git` kurulu değilken kontrol
  kırmızıya düşmez; atlandığını söyleyen tek satırlık bir not yazar. Bu, `exec-bits` adımıyla
  sınırlı değildir: depo kökünde `.git` yoksa `./scripts/check`'in tamamı (full ve `--fast`)
  yeşildir; CB-2'nin gerçek depo kanıtı yalnızca `.git` varken uygulanır. `.git` olduğu hâlde
  git depoyu okuyamıyorsa (ör. `safe.directory` / dubious ownership) bu bir atlama sayılmaz:
  `./scripts/check` kırmızıdır. *(R-08, review round 4 F-1 — 2026-11-02.)*
  Yargılanan depo yalnızca proje kökünün kendi deposudur. Proje kökünün üstündeki bir depo (ör.
  dotfiles deposu olan bir `$HOME`, ya da bir monorepo) hiçbir zaman yargılanmaz. Kopya başka bir
  deponun içinde dursa bile, kökte `.git` yoksa bu bir atlamadır. *(R-08, review round 5 R5-1 —
  2026-11-02.)*

## Preserved behavior
- [x] PB-1 — ANEW core dosyaları değişmez: `git diff main -- scripts/doctor scripts/check scripts/residue scripts/selftest scripts/init` boştur ve `./scripts/selftest` 82/82 geçer.
- [x] PB-2 — Mevcut `lint` ve `test` adımları aynı sırayla, aynı sonuçla çalışır: lint temiz,
  44 test geçer; full ve fast profillerin ikisinde de.
- [x] PB-3 — Check geride süreç bırakmaz: `./scripts/residue` ve `./scripts/residue --fast` CLEAN.
- [x] PB-4 — CI (`doctor` ve `check` işleri) PR'da yeşildir.

## Out of scope
- `scripts/doctor` veya başka bir ANEW core dosyasını değiştirmek (ileride upstream'e önerilebilir).
- Modu otomatik düzeltmek: kontrol yalnızca raporlar, değiştirmez.
- Henüz izlenmeyen (commit'lenmemiş, `git add` edilmemiş) dosyalar.
- Satır sonu (CRLF) kontrolü: `.gitattributes` zaten bunu çözüyor.
- `100755` olup shebang'i olmayan dosyaları raporlamak (ters yön).
- UTF-8 BOM ile başlayan dosyalar: çekirdek BOM'lu shebang'i tanımaz, dosya zaten çalışmaz; ayrı bir sorun.

## Verification (VERIFY, 2026-11-02, HEAD `dc65bcf`, bağımsız QA subagent; PB-4 CI ile)
Testler `tests/test_exec_bits.py` içinde. Ana testlerin kırmızıya düşebildiği, aracın scratch bir
kopyasında kasıtlı bozulmasıyla (8 mutasyon) gösterildi.

| Kriter | Kanıt | Durum |
|---|---|---|
| CB-1 | `::test_reports_shebang_file_without_exec_bit`, `::test_report_is_utf8_and_keeps_non_ascii_paths`, `::test_ignores_symlink_and_submodule_entries`, `::test_subdirectory_argument_is_judged_from_the_repo_root`. Gözlem: clone'da `git update-index --chmod=-x scripts/selftest` → `./scripts/check` ve `--fast` `CHECK FAILED … at step: exec-bits` + düzeltme komutu | Pass |
| CB-2 | `::test_passes_when_every_shebang_file_is_executable`, `::test_current_repository_passes`; `./scripts/check` → `CHECK GREEN (full, 3 steps, 8 s)` | Pass |
| CB-3 | `::test_ignores_templates_under_adapters`; gerçek ağaçta `adapters/claude-code/.claude/hooks/protect-shipped.sh` (`100644` + `#!`) raporlanmıyor | Pass |
| CB-4 | `::test_ignores_files_without_shebang` | Pass |
| CB-5 | `::test_skips_outside_a_git_work_tree`, `::test_skips_when_git_is_not_installed`, `::test_current_repository_passes`. Gözlemler (full + `--fast`, `git archive HEAD` kopyaları): `.git`'siz kopya; boş bir dış deponun içinde kopya; index'inde `bad.sh` (`100644` + `#!`) olan dış deponun içinde kopya; aynı kopyaya dış deponun dışından junction/symlink ile girmek → hepsi NOTE + `CHECK GREEN`. Bozuk `.git/HEAD` → `CHECK FAILED at step: test` | Pass |
| PB-1 | `git diff main -- scripts/doctor scripts/check scripts/residue scripts/selftest scripts/init` boş; `./scripts/selftest` 82 passed, 0 failed | Pass |
| PB-2 | lint `All checks passed!`; eski 44 test tek başına geçiyor; Windows'ta 55 passed + 4 skipped, Linux CI'da 59 passed | Pass |
| PB-3 | `./scripts/residue` → `RESIDUE CLEAN (full, 2 runs)`; `--fast` → `RESIDUE CLEAN (fast, 2 runs)` | Pass |
| PB-4 | PR #6, run 41471998060 (pull_request, `dc65bcf`): `check` ve `doctor` pass. Run 41470868800 (push, `dc65bcf`): `59 passed`, `CHECK GREEN (full, 3 steps, 1 s)`; selftest 82/82 | Pass |

CB-5 link yolu gözlemi (Windows; POSIX'te junction yerine `ln -s`):
```
O=<scratch>/outer; git -C $O init -q
printf '#!/bin/sh\necho bad\n' > $O/bad.sh; git -C $O add bad.sh; git -C $O update-index --chmod=-x bad.sh
mkdir $O/copy; git -C <repo> archive HEAD | tar -x -C $O/copy
MSYS_NO_PATHCONV=1 cmd /c mklink /J "$(cygpath -w <scratch>/link)" "$(cygpath -w $O/copy)"
cd <scratch>/link; ./scripts/check; ./scripts/check --fast   # beklenen: NOTE + CHECK GREEN
```

Kayıtlar:
- Windows'ta atlanan 4 test (non-UTF-8 yol ×2, boşluklu kök, girilemeyen dizin) Linux CI'da koştu
  ve geçti (59 passed, 0 skipped).
- Gerçek dubious ownership ile uçtan uca check koşusu yerine vekiller kullanıldı; bu durumda kırmızıyı
  `test` adımı üretir. `test` ileride full-only olursa `--fast` bu durumda yeşil kalır.
- Review round 1 F-4 kaydı: çıktı uzun tire yerine ASCII `-` kullanır (plan `—` yazıyor);
  `::test_report_is_utf8_and_keeps_non_ascii_paths` plan haritası dışında eklendi.
- `::test_skips_outside_a_git_work_tree` atlama notunu parantezine kadar assert ediyor; not metni
  değişirse kırılır (düşük etki).

## Definition of Done
- [x] `scripts/check` green
- [x] Independent review done; real findings fixed, noise rejected with written rationale
- [x] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots)
- [x] Spec moved to `specs/done/` (immutable there)

## Scorecard (fill at ship — honest numbers make the process improvable)
| Metric | Value |
|---|---|
| Spec revisions | 2 (R-08: review round 4 F-1, round 5 R5-1) |
| Fix rounds | 6 |
| Review findings: real / noise | 16 / 2 (+2 yalnızca kayıt: round 1 F-4, round 7 N7-1) |
| Regressions introduced | 1 (R5-1, fix-4 ile geldi; dal içinde yakalandı) |
| Bugs escaped to production | 0 (henüz yayında değil) |
