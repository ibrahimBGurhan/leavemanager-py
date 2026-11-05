# Spec 0016 — refactor-depo-sozlesmesi (mini)

- Status: In progress
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
- [ ] PB-1 — **Tüm mevcut testler değişmeden yeşil:** `git diff main -- tests/` yalnız yeni
  sözleşme test dosyasını gösterir; mevcut test dosyaları blob-identical; `scripts/check` full yeşil.
- [ ] PB-2 — **Uygulama kodu davranışı aynı:** `domain/`, `web/`, `app.py` değişmez; `MemoryStorage`
  metotlarının gövdeleri değişmez (yalnız sözleşmeye bağlayan yorum/tip bildirimi).
- [ ] PB-3 — **Sözleşme mevcut davranışı yazar, yeni davranış icat etmez:** sözleşmedeki her
  madde bugünkü `MemoryStorage` ve onu kullanan kodun (domain, testler) davranışıdır; sözleşme
  testleri `MemoryStorage`'a karşı yeşildir.
- [ ] PB-4 — **Katman kuralları:** `tests/test_architecture.py` değişmeden yeşil; sözleşme
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

## Definition of Done
- [ ] `scripts/check` green
- [ ] Independent review done; real findings fixed, noise rejected with written rationale
- [ ] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots)
- [ ] Spec moved to `specs/done/` (immutable there)

## Scorecard (fill at ship — honest numbers make the process improvable)
| Metric | Value |
|---|---|
| Spec revisions | |
| Fix rounds | |
| Review findings: real / noise | |
| Regressions introduced | |
| Bugs escaped to production | |
