# Spec 0026 — eszamanli-sayac-testleri (mini)

- Status: Shipped
- Mode: lite
- Plan: `specs/plans/0026-plan.md`
- Source: issue #43 — 0022 G-1 (spec 0022 VERIFY: "`test_concurrent_adds_get_distinct_numbers` ve
  `test_concurrent_next_employee_id_calls_get_distinct_numbers` iş parçacığı geçişini zorlasın;
  bugün `next_employee_id`'deki kilit kaldırılınca da geçebiliyorlar (GIL). Kod doğru, kilit var.")
- Design: —
- Supersedes: —

## Intent
İki kişi aynı anda personel eklediğinde her kayıt ayrı bir numara almalı; kod bunu bir kilitle
sağlıyor ve iki test bunu "kanıtlıyor" gibi görünüyor. Ama kilit kaldırılınca da bu testler yeşil
kalıyor, yani koruma testle kilitli değil: kilidi kaldıran bir değişiklik fark edilmeden geçer. Bu
iş davranışı değiştirmez; eşzamanlılık testlerini, koruma kalkınca güvenilir biçimde kırmızıya
düşecek hale getirir.

Triage kaydı (issue #43, 2026-11-10): rubrik (a) hata değil (kod doğru), (b) kriter değişmiyor,
(c) ortak kod yok; iş test olduğu için trivial lane'in "yeni bir test → yeniden triage" kuralı
gereği insan kararıyla CHANGE lane'de, mini-spec ile (spec 0023, 0024, 0025 kalıbı).

### Gözlem (ANALYZE, 2026-11-10, HEAD `21df279`, repo dışı kopyada)
- `storage/memory.py` ve `storage/sqlite.py`'de `next_employee_id` kilitsiz bırakıldı: iki test
  (her biri iki depo için, toplam 4 koşu) **5/5 denemede yeşil**.
- Aynı kopyada `sys.setswitchinterval(1e-6)` ile: **3/3 denemede yeşil** — issue'nun önerdiği
  "geçiş aralığını düşürmek" tek başına yetmiyor; okuma ile artırma arasındaki pencere çok dar.
- Aynı zayıflık spec 0019 G-4 testinde de var:
  `test_storage_contract.py::test_concurrent_login_failures_are_all_counted`, memory deposunda
  `record_login_failure` kilitsiz bırakılınca **3/3 yeşil** (bkz. S-2).
- Python 3.13.5 (GIL'li yapı).

## Changed behavior
none — no observable behavior change. Kanıtı aşağıdaki Preserved behavior kriterleri taşır.

## Preserved behavior
"Koruma kalkarsa" = ilgili sayaç işleminin eşzamanlı çağrılara karşı korunması (bugün kilit)
kaldırılırsa; VERIFY bunu repo dışı kopyada mutantla dener.

- [x] PB-1 — **Personel numarası, iki depo:** personel ekleme ve numara sayacı eşzamanlılık
  testleri bugünkü kodla yeşildir; sayacın koruması kalkarsa (memory ve sqlite deposunda ayrı
  ayrı) **her koşuda** kırmızıdır (VERIFY: her mutant için 10/10 kırmızı).
- [x] PB-2 — **Giriş hatası sayacı** (S-2 kabul edilirse): `record_login_failure` eşzamanlılık
  testi bugünkü kodla yeşildir; memory deposunda koruması kalkarsa her koşuda kırmızıdır
  (VERIFY: 10/10). sqlite deposu için aynı mutantın kurulabildiği yerde aynı şart (G-a).
- [x] PB-3 — **Bugünkü güvenceler korunur:** testlerin bugünkü assert'leri (ör. 8 iş parçacığı ×
  10 eklemede 80 ayrı numara, hiçbir kayıt kaybolmaz; 200 çağrıda 200 ayrı numara; hiçbir artış
  kaybolmaz) kaldırılmaz ve zayıflatılmaz.
- [x] PB-4 — **Kararlı ve hızlı:** bugünkü kodla ilgili testler 10 ardışık koşuda yeşildir
  (kararsızlık yok); testlerin süresi toplamda en fazla 5 s artar (G-b), `scripts/check` fast
  profilinde kalır.
- [x] PB-5 — Üretim kodu değişmez (`git diff main -- domain web storage app.py` boş); ilgili
  eşzamanlılık testleri dışında hiçbir test değişmez, zayıflatılmaz ya da silinmez;
  `scripts/check` full yeşil.

## Out of scope
- Kilidin kendisi ve sayaç kodu (doğru çalışıyor; değişmez).
- GIL'siz (free-threaded) Python yapısında çalıştırma.
- Diğer eşzamanlılık testleri (talep numarası vb.) — S-2 kararı yalnız giriş hatası sayacını
  kapsar; diğerleri için zayıflık gözlenmedi/denenmedi.
- Issue #43'ün diğer maddeleri (0020 F2-1(b); 0021 G-B, G-E; 0022 G-2).

## Decisions (ANALYZE; onay: İbrahim Gürhan, 2026-11-10 — S-1…S-4 ve self-critique G-a, G-b önerildiği gibi)
- **S-1 Kanıt ölçüsü:** "koruma kalkınca kırmızı" **her koşuda** (deterministik) olmalı, "çoğu
  zaman" değil. *Öneri: kabul* — ara sıra kırmızı olan bir test kanıt değildir ve CI'da kararsız
  (R-03) görünür; gözlem, geçiş aralığını düşürmenin yetmediğini gösteriyor.
- **S-2 Kapsam:** aynı zayıflığı taşıyan 0019 G-4 giriş hatası sayacı testi (PB-2) bu spec'e
  dahil. *Öneri: kabul* — aynı kök neden, aynı kalıp; birini kilitleyip ötekini sahte bırakmak
  tutarsız olur. Reddedilirse PB-2 silinir ve issue #43'e yeni madde olarak düşülür.
- **S-3 Üretim kodu değişmez** (PB-5). *Öneri: kabul* — 0023–0025 kalıbı; iş yalnız test. PLAN
  bunu sağlayamazsa durur ve spec değişikliği önerir (R-08), sessizce üretim koduna dokunmaz.
- **S-4 Yer:** mevcut eşzamanlılık testleri yerinde güçlendirilir (bugünkü assert'leri korunarak,
  PB-3); yanlarına aynı şeyi sınayan ikinci bir test eklenmez. *Öneri: kabul* — sahte güvence
  veren testi bırakıp yanına yenisini koymak yanıltıcı olur.
- **G-a (self-critique):** sqlite deposunda giriş hatası sayacının koruması farklı kalıpla
  (`with self._lock, self._db`) yazılı; PB-2 sqlite için "mutantın kurulabildiği yerde" der,
  VERIFY netleştirir. *Öneri: kabul.*
- **G-b (self-critique):** PB-4 süre sınırı kesin: en fazla 5 s (bugünkü full check ~55 s).
  *Öneri: kabul.*

## Verification (VERIFY, 2026-11-10, HEAD `0830595`, bağımsız QA subagent)
PB-1…PB-5 PASS; her mutant 10/10 kırmızı (repo dışı kopyada), bugünkü kod 10/10 yeşil, süre farkı
≈ 3,1 s. PB-2 sqlite: kırmızının mekanizması iş parçacığı çökmesi → kayıp artış (review F-1). Review
round 1: verdict clean; F-1 (düşük) noise, kabul + not. VERIFY bulguları: uygulama ayrıntısına
bağlılık kabul + issue #43 notu; G-1…G-5 aksiyon yok / bilgi. Ayrıntı: `specs/plans/0026-plan.md`
"Triage" ve "Verify".

## Definition of Done
- [x] `scripts/check` green
- [x] Independent review done; real findings fixed, noise rejected with written rationale
- [x] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots)
- [x] Spec moved to `specs/done/` (immutable there)
