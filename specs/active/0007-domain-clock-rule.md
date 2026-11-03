# Spec 0007 — domain-clock-rule (mini)

- Status: Approved
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
- [ ] CB-1 — Mimari testi, `domain` paketinde gerçek saate yapılan her erişimi reddeder:
  - `date.today`, `datetime.now`, `datetime.utcnow`, `datetime.today`;
  - bunların modül önekli yazımları: `datetime.date.today`, `datetime.datetime.now` vb.;
  - takma adla import edilmiş biçimleri: `from datetime import date as D` sonrası `D.today`,
    `import datetime as dt` sonrası `dt.date.today` vb. Kural, dosyanın import'larından
    `datetime` modülüne, `datetime.date`'e ya da `datetime.datetime`'a bağlanan bütün adları
    çözer.

  Kural çağrıya değil erişime bakar: çağrılmadan kullanılan bir erişim de reddedilir
  (`f = date.today`, `def x(today=date.today)`). Hata mesajı ihlalin dosyasını, satırını ve
  erişimi adıyla gösterir. Diğer mimari kuralları gibi kod import edilmeden, okunarak denetlenir.
- [ ] CB-2 — Kural, saatin enjekte edildiği kullanımı yanlış yakalamaz: bugünkü domain kodu
  (`self._clock.today()`) testi geçer. Başka bir nesnenin `today`/`now` adlı metodu da kural
  dışındadır; yalnızca `date` ve `datetime` üzerinden yapılan çağrılar reddedilir.
- [ ] CB-3 — Kural gerçek tarihte, saat kaydırmadan çalışır. CB-1'deki her yazım biçimi (önekli,
  takma adlı ve çağrısız erişim dahil), bilerek bozulmuş bir kopyada bu testi kırmızıya düşürür.
  Bunların arasında spec 0006'nın mutantı da var
  (`get_seniority_years` → `date.today()`); bugün gerçek tarihte (2026) yeşil kalan bu mutant
  da kırmızıya düşer.
- [ ] CB-4 — Belgeler kuralı söyler:
  - `docs/architecture.md` "Forbidden dependencies" listesine 5. kural eklenir: domain gerçek
    saati okumaz.
  - `docs/conventions.md` "enjekte edilen saat" kuralını "henüz araçla zorlanmayan" listesinden
    çıkarır.

## Preserved behavior
- [ ] PB-1 — Ürün kodu değişmez: `app.py`, `domain/`, `storage/` ve `web/` için
  `git diff main` boştur. Ekranlar ve servis aynı yanıtı verir.
- [ ] PB-2 — Mevcut testler değişmez:
  - `tests/test_architecture.py`'deki dört test ve yardımcıları aynı kalır; dosyaya yalnızca yeni
    kural eklenir.
  - Diğer test dosyaları bayt düzeyinde aynıdır.
  - Mevcut 72 test kimliğinin hepsi korunur.
  - Full profil yeşildir; ters sırada da (`ANEW_REVERSE_ORDER=1`).
- [ ] PB-3 — Geri kalan her şey aynen kalır:
  - `scripts/check.conf`, `tools/`, ANEW core ve bağımlılıklar değişmez;
  - `./scripts/selftest` 82/82, residue CLEAN, PR'da CI yeşil.

## Out of scope
- `web`, `storage` ve `app.py`'de saat kullanımı. Composition root'taki `SystemClock` gerçek
  saati okumak zorunda; kural yalnızca domain için.
- `time` modülü (`time.time()`, `time.localtime()` vb.). Domain'de bugün `time` modülü yok.
- Saat dilimi (`Europe/Istanbul`, `docs/conventions.md`) ve timezone-aware zaman damgaları.
- Storage sözleşme testi (spec 0006 VERIFY, G-3): kalıcı DB işine kaldı.
- Mimari testinin diğer sınırları (spec 0006 G-5).

## Definition of Done
- [ ] `scripts/check` green
- [ ] Independent review done; real findings fixed, noise rejected with written rationale
- [ ] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots — N/A, kullanıcı arayüzü yok)
- [ ] Spec moved to `specs/done/` (immutable there)

## Kararlar (spec onayında, İbrahim Gürhan, 2026-11-03)
- **S-1 — kabul:** takma adla import edilen biçimler de reddedilir (CB-1).
- **S-2 — kabul:** kural çağrıya değil erişime bakar (CB-1); çağrısız erişim de bir mutant olarak
  sınanır (CB-3).
- **S-3 — kabul, spec'e yazılmaz:** domain'de `date` adlı yerel bir değişken üzerinden yapılan
  `.today` erişimi yanlış pozitif verebilir; bugün böyle bir kod yok ve hata mesajı adı gösterir.
- **S-4 — `time` modülü kapsam dışı kalır** (Out of scope).
- **S-5 — bölünmez:** tek yetenek, 4 CB ve 3 PB.
