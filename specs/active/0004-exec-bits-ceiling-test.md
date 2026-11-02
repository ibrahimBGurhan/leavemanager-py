# Spec 0004 — exec-bits-ceiling-test (mini)

- Status: Approved
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
- [ ] PB-1 — Sınır, proje kökünün üst dizinine fiziksel yolundan farklı bir yazımla verildiğinde
  ve o üst dizinde bir `.git` bulunduğunda (ör. boş bir `.git` dizini), araç o depoyu yargılamaz:
  atlandığını söyleyen notu yazar ve 0 ile çıkar. İki yazım sınanır:
  - **Windows 8.3 kısa adı** (yalnızca Windows);
  - **üst dizini gösteren bir symlink** (her platform).
- [ ] PB-2 — Bu davranış testlerle kilitlenir: sınırı fiziksel yola çevirmeyen bir araç (QA'nın
  M8 mutantı) Windows'ta ve Linux'ta (CI) en az birer testte kırmızıya düşer. Bugünkü araçla
  aynı testler yeşildir.
- [ ] PB-2a — Ortam senaryoyu kuramıyorsa ilgili varyant gerekçesiyle atlanır: birimde 8.3 kısa
  ad üretimi kapalıysa kısa ad varyantı, symlink oluşturma yetkisi yoksa (ör. Windows'ta
  geliştirici modu kapalı) symlink varyantı. Bu bir "yeşile ulaşmak için atlama" değildir; diğer
  varyant korumayı sürdürür. CI'da (Linux) symlink varyantı atlanmaz.
- [ ] PB-3 — Mevcut davranış ve testler aynen kalır: `tests/test_exec_bits.py`'deki mevcut
  testlerin hiçbiri değişmez, zayıflatılmaz ya da silinmez; `tools/check_exec_bits.py` ve
  `scripts/check.conf` değişmez.
- [ ] PB-4 — ANEW core dosyaları değişmez (`git diff main -- scripts/doctor scripts/check
  scripts/residue scripts/selftest scripts/init` boş), `./scripts/selftest` 82/82 geçer,
  `./scripts/residue` ve `--fast` CLEAN.
- [ ] PB-5 — CI (`doctor` ve `check` işleri) PR'da yeşildir.

## Out of scope
- Aracın davranışını değiştirmek.
- 0003 review round 1 F1 (araç `.git` dizininin kendisiyle çağrıldığında) — noise kararı geçerli.
- `check.conf`'taki `pwd -P` satırını değiştirmek.

## Definition of Done
- [ ] `scripts/check` green
- [ ] Independent review done; real findings fixed, noise rejected with written rationale
- [ ] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots)
- [ ] Spec moved to `specs/done/` (immutable there)
