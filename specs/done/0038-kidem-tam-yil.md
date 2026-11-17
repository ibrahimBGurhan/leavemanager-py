# Spec 0038 — kidem-tam-yil (mini)

- Status: Shipped
- Mode: lite
- Plan: `specs/plans/0038-plan.md`
- Source: `docs/domain.md` OD-1, OD-2 (karar: İbrahim Gürhan, IK adına, 2026-11-17)
- Design: — (ekran düzeni değişmez; yalnız bazı personelin Hak/Kalan sayıları. Açılış verisinde
  hiçbir sayı değişmediği için önce/sonra ekran görüntüsü kanıt değildir; kanıt testlerdir)
- Supersedes: 0001/AC-1 (yalnız "15 → 20" satırı), 0001/AC-2 (kıdem = yıl farkı)

## Intent
Yıllık izin hakkı kıdeme göre belirlenir (İş Kanunu md. 53), ama bugün kıdem yalnız yıl farkıyla
hesaplanıyor: Aralık 2025'te işe giren biri Ocak 2026'da "1 yıl kıdemli" sayılıp 14 gün hak
alıyor, hakkı ise 0. Tam 15 yıl kıdemi olan personel de 26 yerine 20 gün alıyor. IK kararıyla
(İbrahim Gürhan, IK adına, 2026-11-17) kıdem tamamlanmış hizmet yılıdır ve tam 15 yıl 26 gün hak
eder. Hak, Kalan ve yeni talepteki bakiye kontrolü bu doğru kıdemle çalışır.

## Kararlar (clarify)
- **K-1 Kıdem (OD-2):** kıdem, işe giriş tarihinden "bugün"e kadar tamamlanmış hizmet yılı
  sayısıdır. Yıl, işe giriş yıl dönümü **günü** tamamlanmış sayılır (yıl dönümü günü dahil).
  İşe giriş tarihi bugünden sonraysa kıdem 0'dır, hiçbir zaman eksi değildir.
- **K-2 29 Şubat (OD-2):** 29 Şubat'ta işe girenin yıl dönümü artık yıl olmayan yıllarda
  **28 Şubat**, artık yıllarda 29 Şubat'tır.
- **K-3 Hak (OD-1, BR-1):** kıdem 0 → 0 gün · 1–5 → 14 · 6–14 → 20 · 15 ve üzeri → 26.
- **K-4 Tek hesap:** bakiye tablosundaki Hak ve Kalan, yeni talepteki ve onaydaki bakiye
  kontrolü aynı kıdem/hak hesabını kullanır (bugün de öyle; değişmez).
- **K-5 "Bugün":** kıdem, domain'e dışarıdan verilen günün tarihiyle hesaplanır (0007 kuralı).

## Changed behavior
Örneklerde bugün = 2026-10-23 (testlerin sabit tarihi).
- [x] CB-1 — **Kıdem tamamlanmış yıldır:** 2025-10-23'te işe giren → kıdem 1, hak 14;
  2025-10-24'te işe giren → kıdem 0, hak 0; 2025-12-31'de işe giren → kıdem 0, hak 0 (bugün 1/14).
- [x] CB-2 — **Kademe sınırları yıl dönümüne göre:** 2020-10-23 → 6 / 20 gün; 2020-10-24 → 5 /
  14 gün; 2011-10-23 → **15 / 26 gün** (bugün 20); 2011-10-24 → 14 / 20 gün.
- [x] CB-3 — **29 Şubat:** 2020-02-29'da işe giren için bugün 2027-02-27 → kıdem 6; 2027-02-28 →
  7; 2028-02-28 → 7; 2028-02-29 → 8.
- [x] CB-4 — **Ekranlar yeni hakkı kullanır:** bugün tam 15 yıl kıdemli bir personel bakiye
  tablosunda Hak 26 ve (onaylı talebi yokken) Kalan 26 görünür; bu personelin 21–26 iş günlük
  yeni talebi bakiye yüzünden reddedilmez (bugün reddediliyor). Yıl dönümü henüz gelmemiş bir
  personelin hakkı, yeni talep bakiye kontrolünde de 0 kabul edilir.
- [x] CB-5 — **Alan dokümanı:** `docs/domain.md`'de BR-1 ve BR-2 kararı yazar ("IK onayı
  bekliyor" ve "Mevcut kod" notları kalkar), OD-1 ve OD-2 kapandı olarak işaretlenir (karar,
  kişi, tarih, spec 0038); sözlükteki Kıdem satırı güncellenir. Yeni açık karar **OD-11 "İzin
  yılı / hakkın yenilenmesi"** eklenir (Kullanılan tüm zamanların onaylı taleplerini sayıyor, hak
  yıl dönümünde yenilenmiyor; IK kararı bekler).

## Preserved behavior
- [x] PB-1 — **Açılış verisi sayıları değişmez:** Ayse Yilmaz 26 / 9 / 17, Mehmet Demir 20 / 0 /
  20, Zeynep Kaya 14 / 0 / 14, Ahmet Celik 20 / 0 / 20, Elif Sahin 0 / 0 / 0 (Hak / Kullanılan /
  Kalan) — hem 2026-10-23'te hem 2026-11-17'de (Zeynep'in 10 Kasım yıl dönümü bu iki tarihin
  arasında; hakkı ikisinde de 14).
- [x] PB-2 — **Yıl dönümüne göre değişmeyen kademeler:** 1 Ocak'ta işe girenler için kıdem 0 → 0,
  1 → 14, 5 → 14, 6 → 20, 14 → 20, 16 → 26 (0001/AC-1'in 15 dışındaki satırları).
- [x] PB-3 — **Henüz başlamamış personel:** işe giriş tarihi bugünden sonra olan personelin
  hakkı 0'dır — aynı yıl içinde de (2026-12-01), sonraki yıllarda da (2027-02-01; 0022 ekranı:
  `Deniz Ak, IT, 0, 0, 0, 0`).
- [x] PB-4 — **Geri kalan her şey aynı:** Kullanılan, Bekleyen, iş günü sayımı, talep/onay
  akışının hata sırası ve mesajları, kim hangi satırı görür (IK / Yönetici / Personel), ekran
  düzeni ve mimari kurallar (domain gerçek saati okumaz) değişmez; `./scripts/check` yeşil.

## Out of scope
- İzin yılı / hakkın yıl dönümünde yenilenmesi: Kullanılan bugün tüm zamanların onaylı
  taleplerini sayar ve Hak tek bir yıllık değerdir; bu model değişmez (S-3; OD-11 olarak
  kaydedilir, CB-5).
- OD-5 (yaşa göre en az 20 gün), OD-6 (devreden izin), OD-9 (arife yarım günleri), OD-10 (tatil
  listesinin 2027 sonrası).
- Önceki işyerlerindeki hizmetin kıdeme eklenmesi; kıdemin ekranda gösterilmesi; işe giriş
  tarihinin düzenlenmesi.
- 0001/AC-1 ve AC-2'yi sabitleyen iki `*_current` test bu spec'in kriterleriyle **yerine konur**
  (supersede; test zayıflatma değildir — dosya başındaki not bunu öngörüyor).

## Self-critique (spec onayında karara bağlandı — İbrahim Gürhan, 2026-11-17: tümü önerildiği gibi)
- **S-1 Yıl dönümü günü:** yılı tamamlar (K-1). Kanunda bir yıllık hizmet yıl dönümünde dolar.
- **S-2 Gelecekteki işe giriş:** kıdem 0, hiçbir zaman eksi değil (K-1; PB-3).
- **S-3 İzin yılı yok:** kapsam dışı; `docs/domain.md`'ye OD-11 olarak eklenir (CB-5).
- **S-4 Gerçek tarih kanıtı:** açılış verisi hem 2026-10-23'te hem 2026-11-17'de (PB-1).
- **S-5 `*_current` testleri:** 0001/AC-1 (15 satırı) ve AC-2'yi sabitleyen iki test bu spec'in
  kriterleriyle yerine konur — supersede, zayıflatma değil (Out of scope notu).
- **Split:** tek yetenek, 9 kriter — bölünmez.

## Verification (VERIFY, 2026-11-17, HEAD `a9aecd1`)
CB-1…CB-5 ve PB-1…PB-4 Pass; full `CHECK GREEN (full, 3 steps, 73 s)` (813 passed, 5 skipped,
`3297755`; sonrası yalnız spec/plan). Repo dışı kopyada (`git archive`) `domain/leave_service.py`'ye
7 mutant: yıl dönümü günü sayılmaz 8, 29 Şubat düzeltmesi yok 1, artık yıl işe giriş yılına göre 1,
29 Şubat → 1 Mart 1, eksi kıdem 2, tam 15 yıl yine 20 5, yıl farkı 8 test kırmızı; `main` kodu
HEAD testleriyle 14 kırmızı. Üretim diff'i yalnız `domain/leave_service.py`; `tests/`'te silinen
satırlar yalnız supersede edilen T1/T2. Review round 1 temiz, F-1 (Low, plan haritasında CB-1 test
adı) real — kanıt tablosunda doğru adla kapatıldı, kod değişmedi. UI düzeni değişmedi, açılış
verisinde sayı değişmez; ekran görüntüsü gerekmez. Ayrıntı: `specs/plans/0038-plan.md` "Triage" ve
"Verify".

## Definition of Done
- [x] `scripts/check` green
- [x] Independent review done; real findings fixed, noise rejected with written rationale
- [x] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots)
- [x] Spec moved to `specs/done/` (immutable there)
