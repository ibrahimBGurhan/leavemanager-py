# Spec 0005 — refactor-test-seams (mini)

- Status: In progress
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
- [ ] PB-1 — Ürün davranışı aynen kalır: ana sayfa, talepler ekranı, yeni talep formu ve
  gönderimi, hak/kıdem/kullanılan/kalan hesapları ve durum rozetleri `main` ile aynı çıktıyı
  verir. `tests/test_baseline_screens.py`'deki test fonksiyonlarının gövdeleri değişmez.
- [ ] PB-2 — Karakterizasyon testlerinin hiçbiri kaybolmaz ya da zayıflamaz: `test_baseline_*`
  dosyalarındaki test kimliklerinin listesi (ad + parametre, bugün 39) `main` ile aynıdır; her
  testin beklenen değerleri aynıdır; hiçbir test silinmez, atlanmaz ya da `xfail` yapılmaz.
  Testler bulundukları dosyada ve adlarıyla kalır; böylece kimlik listesi birebir karşılaştırılır.
  `test_status_badge` aynı 7 vakayı ve aynı iki assert'i (renk, durum metni) korur, ama rozeti
  talepler ekranında okur: açılış verisinde olmayan durumdaki talep, veri bağlantı noktası
  üzerinden eklenir.
- [ ] PB-3 — Testler `app.py`'nin iç yapısına doğrudan dokunmaz: `tests/` altında `app`
  modülünün `datetime` adına, `Db` sınıfının alanlarına ve `LeaveService.status_badge`'e
  doğrudan erişim yoktur. "Bugün" testlere tek bir bağlantı noktasından verilir
  (`docs/architecture.md`: "bugün dışarıdan enjekte edilir"). Kanıt: `tests/` altında
  `leave_app.datetime`, `.Db.` ve `status_badge` için yapılan arama boş döner.
- [ ] PB-4 — Bağlantı noktalarının yeterliliği kanıtlanır: iş kuralları (`LeaveService`) ve veri
  (`Db`, `seed`) repo dışında, geçici bir kopyada `app.py`'den ayrı modüllere taşındığında testler
  **hiç değiştirilmeden** yeşil kalır. Bu kopya commit'lenmez.
- [ ] PB-5 — Geri kalan her şey aynen kalır: `tests/test_exec_bits.py` ve araçları değişmez;
  ANEW core dosyaları değişmez (`git diff main -- scripts/doctor scripts/check scripts/residue
  scripts/selftest scripts/init` boş); `./scripts/selftest` 82/82; `./scripts/residue` ve
  `--fast` CLEAN; testler rastgele sırada da aynı sonucu verir (`ANEW_REVERSE_ORDER=1`, spec
  0001/AC-11); PR'da CI (`doctor` ve `check`) yeşil.

## Out of scope
- Katmanlara ayırmanın kendisi (`web`, `domain`, `storage` paketleri) — sonraki iş, ayrı issue.
- Herhangi bir davranış değişikliği: OD-1…OD-8, BR-9, kalıcılık, kimlik doğrulama.
- Durum rozetinin HTML'ini web'e taşımak — bu iş yalnızca testin rozeti nereden sınadığını değiştirir.
- `tests/test_exec_bits.py`.

## Definition of Done
- [ ] `scripts/check` green
- [ ] Independent review done; real findings fixed, noise rejected with written rationale
- [ ] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots)
- [ ] Spec moved to `specs/done/` (immutable there)
