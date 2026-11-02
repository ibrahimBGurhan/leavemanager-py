# Spec 0003 — exec-bits-unreadable-git (mini)

- Status: In progress
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
- [ ] CB-1 — Proje kökünde bir `.git` (dizin ya da dosya) varken git depoyu okuyamıyorsa (ör.
  dubious ownership, bozuk `.git/HEAD`, var olmayan bir dizini gösteren `.git` dosyası, boş bir
  `.git` dizini), `exec-bits` adımı **kırmızıdır** ve `./scripts/check` bu adımda durur — hem
  full hem `--fast`. Araç `.git`'i başlangıç dizininde ve üst dizinlerinde arar, ama proje
  kökünün üstüne çıkmaz (git'in kendi arama kuralı ve `GIT_CEILING_DIRECTORIES` sınırı ile aynı);
  böylece bir alt dizin argümanıyla çalıştırıldığında da aynı sonuç alınır.
- [ ] CB-2 — Bu durumda çıktı `exec-bits:` ile başlayan tek bir satırdır ve git'in kendi hata
  gerekçesini (git'in hata çıktısının ilk satırı) içerir. "skipped" kelimesi geçmez.
- [ ] CB-3 — Bu durumda araç tek başına çalıştırıldığında da başarısız biter: çıkış kodu, ihlal
  bulunduğundaki kodla aynıdır (1). `./scripts/check`'in `test` adımı çalışmasa bile sonuç
  kırmızıdır.

## Preserved behavior
- [ ] PB-1 — Atlama durumları değişmez (0002/CB-5): proje kökünde `.git` yoksa — zip/`git archive`
  kopyası, başka bir deponun içine açılmış kopya, kopyaya bir link/junction üzerinden girilmesi —
  `exec-bits` atlandığını söyleyen tek satırlık notu yazar ve `./scripts/check` (full ve `--fast`)
  yeşildir. Proje kökünün üstündeki bir depo hiçbir zaman yargılanmaz.
- [ ] PB-2 — `git` kurulu değilken araç `NOTE: exec-bit check skipped - git is not installed`
  yazar ve 0 ile çıkar. Öncelik: git kurulu değilse proje kökünde `.git` olsa da atlanır — git
  yokken deponun okunabilir olup olmadığı bilinemez.
- [ ] PB-3 — 0002'nin CB-1…CB-4 davranışları (ihlal raporu ve düzeltme komutu, `adapters/` hariç
  tutulması, shebang'siz dosyalar, symlink/submodule girdileri) ve var olmayan dizin argümanında
  exit 2 aynen kalır. `tests/test_exec_bits.py`'deki mevcut testlerin hiçbiri zayıflatılmaz ya da
  silinmez.
- [ ] PB-4 — ANEW core dosyaları değişmez (`git diff main -- scripts/doctor scripts/check
  scripts/residue scripts/selftest scripts/init` boş), `./scripts/selftest` 82/82 geçer,
  `./scripts/residue` ve `--fast` CLEAN.
- [ ] PB-5 — CI (`doctor` ve `check` işleri) PR'da yeşildir; Windows'ta atlanan testler Linux'ta
  koşar ve geçer.

## Out of scope
- `test` adımını full-only'ye taşımak ya da `check.conf` profillerini değiştirmek.
- Dubious ownership'i otomatik çözmek (`safe.directory` eklemek vb.): kontrol yalnızca raporlar.
- `GIT_DIR` / `GIT_WORK_TREE` gibi ortam değişkenleriyle dışarıdan verilen depolar.
- 0002'nin round 4a'da noise kararı verilen kök adı (`\n` ile biten) durumu.
- `test_current_repository_passes`'ın davranışı: `.git` varken katı assert'leri aynen kalır
  (çift güvence).

## Definition of Done
- [ ] `scripts/check` green
- [ ] Independent review done; real findings fixed, noise rejected with written rationale
- [ ] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots)
- [ ] Spec moved to `specs/done/` (immutable there)
