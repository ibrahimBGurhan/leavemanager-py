# Spec 0016 — refactor-depo-sozlesmesi (mini)

- Status: Shipped
- Mode: lite
- Plan: `specs/plans/0016-plan.md`
- Source: ADR-0001 (`docs/decisions/0001-kalicilik-sqlite.md`), `docs/architecture.md` "hedeften kalan fark"
- Design: — (UI değişmez)
- Supersedes: —

## Intent
ADR-0001 kalıcı depoyu SQLite'a taşımaya karar verdi ve iki depo uygulamasının (`MemoryStorage`,
gelecek `SqliteStorage`) **aynı sözleşme testlerinden** geçmesini istedi. Bugün depo arayüzü
yazılı değil, yalnızca ortak metot adları (`docs/architecture.md`). Bu iş arayüzü yazılı bir
sözleşmeye çevirir ve sözleşme testlerini yazar; testler bugün yalnız `MemoryStorage`'a karşı
çalışır. Davranış değişmez. SQLite uygulaması bir sonraki spec'te (0017) aynı testlerden geçer.

## Changed behavior
- none — no observable behavior change

## Preserved behavior
- [x] PB-1 — **Tüm mevcut testler değişmeden yeşil:** `git diff main -- tests/` yalnız yeni
  sözleşme test dosyasını gösterir; mevcut test dosyaları blob-identical; `scripts/check` full yeşil.
- [x] PB-2 — **Uygulama kodu davranışı aynı:** `domain/`, `web/`, `app.py` değişmez; `MemoryStorage`
  metotlarının gövdeleri değişmez (yalnız sözleşmeye bağlayan yorum/tip bildirimi).
- [x] PB-3 — **Sözleşme mevcut davranışı yazar, yeni davranış icat etmez:** sözleşmedeki her
  madde bugünkü `MemoryStorage` ve onu kullanan kodun (domain, testler) davranışıdır; sözleşme
  testleri `MemoryStorage`'a karşı yeşildir.
- [x] PB-4 — **Katman kuralları:** `tests/test_architecture.py` değişmeden yeşil; sözleşme
  `storage` paketinde; `domain` storage'ı import etmeye başlamaz.

## Out of scope
- `SqliteStorage`, `DATABASE_PATH`, şema, demo verisi yükleme kuralı — spec 0017.
- `reset()` sözleşmeye girmez: testlerin açılış verisine dönme yardımcısıdır; demo verisinin nasıl
  yükleneceği 0017'de `SEED_DEMO_DATA` ile belirlenir.
- Domain'in depoyu tip bildirimiyle kullanması, depo metotlarının yeniden adlandırılması.

## 0017 için onaylanan kararlar (kayıt)
Kalıcılık spec'i (0017, `/new-feature`) bu kararlarla açılır (İbrahim Gürhan, 2026-11-05):
- **K-1** Personel ekleme ekranı kapsam dışı; ayrı spec, giriş sisteminden sonra. Demo ve test
  için `SEED_DEMO_DATA=1`.
- **K-2** Boş durumlar: sayaçlar 0, bakiye ve talep tabloları yalnız başlık, Yeni Talep'te personel
  listesi boş (gönderilirse "Seçilen personel bulunamadı.").
- **K-3** `SEED_DEMO_DATA=1` yalnız veritabanı boşsa yükler; var olan veri ezilmez, çoğaltılmaz.
- **K-4** Talep numarası yeniden başlatmadan sonra en büyük numaradan devam eder; yeniden
  kullanılmaz.
- **K-5** Veritabanı klasörü yoksa oluşturulur; yazılamıyorsa uygulama açılmaz, log'a açık hata;
  belleğe sessiz dönüş yok.
- **K-6** Mevcut testler bellek deposuyla değişmeden çalışır; sözleşme testleri iki depoda;
  yeniden başlatmada korunma aynı dosyaya yeni depo açılarak sınanır.
- **K-7** Yedekleme kodu yok; belgelere yöntem ve KVKK notu.
- **K-8** Bellekteki (demo) veri taşınmaz.

## Review (2026-11-05, bağımsız reviewer subagent)
- **Round 1** (HEAD `e04a9d9`): davranış korunmuş; 11 yanlış depo mutantının 11'i sözleşme
  testlerinde kırmızı, doğru kabul edilmesi gereken 8 varyant (boş başlayan depo, kopya döndüren
  depo) 8/8 yeşil. Bulgular F-1 (orta), F-2 (düşük) — yalnız sözleşme docstring'i.
- **Round 2** (HEAD `51db0ad`): F-1, F-2 düzeldi; yeni N-1 (düşük).
- **Round 3** (HEAD `441e41c`): **clean**; N-1 düzeldi.

### Triage (İbrahim Gürhan, 2026-11-05)
- **F-1 — real → fix-1 (`18c347c`):** "add_request sayaca dokunmaz" ile "var olan tüm
  numaralardan büyük" elle numaralanmış kayıtta çelişiyordu (MemoryStorage ikincisini
  sağlamıyordu). `add_request` ön koşul olarak yazıldı (numarayı çağıran `next_request_id()`'den
  alır, numaralar tekildir).
- **F-2 — real → fix-1 (`51db0ad`):** "yeniden verilmez" aynı depo nesnesiyle sınırlandı;
  yeniden başlatma 0017 K-4'e bırakıldı.
- **N-1 — real → fix-2 (`441e41c`):** fix-1 maddeyi fazla daraltıp açılışta var olan kayıtlarla
  çakışmama garantisini düşürmüştü; geri yazıldı, "tanımsız" yalnız açıldıktan sonra elle
  numaralanan kayıtlar. Plana sapma notu.

## Verification (refactor: bağımsız reviewer kanıtından)
Refactor iş akışında ayrı VERIFY segmenti yok; tablo üreticinin değil, bağımsız reviewer'ların
kanıtından kuruldu. Suite: `252 passed, 5 skipped`, `CHECK GREEN (full, 3 steps)`; round 3
reviewer kendi kopyasında `252 passed, 5 skipped`.

| Kriter | Kanıt | Durum |
|---|---|---|
| PB-1 | `git diff main -- tests/` yalnız yeni `tests/test_storage_contract.py`; mevcut test dosyaları blob-identical; `CHECK GREEN (full)` | Pass |
| PB-2 | `git diff main -- domain web app.py` boş; `storage/memory.py` diff'i tek yorum satırı | Pass |
| PB-3 | Sözleşme testleri `MemoryStorage`'a karşı, `contract.py` yazılmadan önce yeşildi (adım 2; yalnız `isinstance` testi kırmızı); her madde domain kullanımı ve `MemoryStorage` ile karşılaştırıldı (round 1–3); boş başlayan depo varyantı da geçiyor | Pass |
| PB-4 | `tests/test_architecture.py` değişmeden yeşil; sözleşme `storage` paketinde; `domain` storage'ı import etmiyor | Pass |

Plan sapması (kayıtlı): planlanan "`add_request` sonrası numara tam +1 artar" testi
`MemoryStorage`'a özgü olduğu için yazılmadı (plan Risk 1); sözleşme ifadesi review ile değişti
(plan Risk 4 notu).

## Definition of Done
- [x] `scripts/check` green
- [x] Independent review done; real findings fixed, noise rejected with written rationale
- [x] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots)
- [x] Spec moved to `specs/done/` (immutable there)

## Scorecard (fill at ship — honest numbers make the process improvable)
| Metric | Value |
|---|---|
| Spec revisions | 0 |
| Fix rounds | 2 (fix-1: F-1, F-2; fix-2: N-1 — hepsi sözleşme docstring'i) |
| Review findings: real / noise | 3 / 0 (F-1 orta, F-2 ve N-1 düşük; round 3 clean) |
| Regressions introduced | 0 (N-1, fix-1'in getirdiği bir ifade daralmasıydı; davranış değil, review'da yakalandı) |
| Bugs escaped to production | 0 (henüz yayında değil) |
