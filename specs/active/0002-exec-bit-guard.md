# Spec 0002 — exec-bit-guard (mini)

- Status: In progress
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
- [ ] CB-1 — Git'te izlenen, `adapters/` dışında olan, ilk satırı `#!` ile başlayan ve git modu
  `100644` olan bir normal dosya varsa `./scripts/check` **kırmızıdır** (hem full hem `--fast`).
  Çıktı, böyle her dosyanın yolunu olduğu gibi (boşluk içerse de) ve
  `git update-index --chmod=+x <yol>` düzeltme komutunu yazar. Symlink (`120000`) ve submodule
  (`160000`) girdileri değerlendirilmez.
- [ ] CB-2 — Böyle dosyaların hepsi `100755` ise kontrol geçer ve `./scripts/check` yeşildir.
  Bugünkü depo bu durumdadır.
- [ ] CB-3 — `adapters/` altındaki shebang'li ve `100644` dosyalar raporlanmaz. Bunlar yerinde
  çalıştırılmayan şablonlardır; `scripts/init` kopyalarken izni kendisi verir.
- [ ] CB-4 — Shebang'siz dosyalar (`app.py`, `scripts/check.conf`, `*.md` …) mode'larından
  bağımsız olarak raporlanmaz.
- [ ] CB-5 — Git çalışma ağacı olmayan bir kopyada (ör. zip) ya da `git` kurulu değilken kontrol
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
- [ ] PB-1 — ANEW core dosyaları değişmez: `git diff main -- scripts/doctor scripts/check scripts/residue scripts/selftest scripts/init` boştur ve `./scripts/selftest` 82/82 geçer.
- [ ] PB-2 — Mevcut `lint` ve `test` adımları aynı sırayla, aynı sonuçla çalışır: lint temiz,
  44 test geçer; full ve fast profillerin ikisinde de.
- [ ] PB-3 — Check geride süreç bırakmaz: `./scripts/residue` ve `./scripts/residue --fast` CLEAN.
- [ ] PB-4 — CI (`doctor` ve `check` işleri) PR'da yeşildir.

## Out of scope
- `scripts/doctor` veya başka bir ANEW core dosyasını değiştirmek (ileride upstream'e önerilebilir).
- Modu otomatik düzeltmek: kontrol yalnızca raporlar, değiştirmez.
- Henüz izlenmeyen (commit'lenmemiş, `git add` edilmemiş) dosyalar.
- Satır sonu (CRLF) kontrolü: `.gitattributes` zaten bunu çözüyor.
- `100755` olup shebang'i olmayan dosyaları raporlamak (ters yön).
- UTF-8 BOM ile başlayan dosyalar: çekirdek BOM'lu shebang'i tanımaz, dosya zaten çalışmaz; ayrı bir sorun.

## Definition of Done
- [ ] `scripts/check` green
- [ ] Independent review done; real findings fixed, noise rejected with written rationale
- [ ] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots)
- [ ] Spec moved to `specs/done/` (immutable there)
