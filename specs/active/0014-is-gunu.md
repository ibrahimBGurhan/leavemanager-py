# Spec 0014 — is-gunu (mini)

- Status: In progress
- Mode: lite
- Plan: `specs/plans/0014-plan.md`
- Source: `docs/domain.md` OD-4
- Design: — (ekran düzeni değişmez; yalnız sayılar ve yeni bir hata mesajı. Önce/sonra ekran görüntüsü kanıttır)
- Supersedes: 0001/AC-3 (takvim günü), 0001/AC-4, AC-7, AC-8 ve 0013/CB-3 (açılış verisinden
  hesaplanan sayılar: Ayse Kullanilan 12 → 9, Kalan 14 → 17; #1 ve #7 "Gun"), 0008/CB-1, 0010/AC-3,
  AC-4 ve 0013/CB-1'in hafta sonuna denk gelen tarih örnekleri

## Intent
Bugün izin günü takvim günü olarak sayılıyor: hafta sonunu kapsayan bir haftalık izin 7 gün
düşülüyor. Kanun (İş Kanunu md. 56) hafta tatili ve genel tatil günlerinin izinden sayılmamasını
istiyor. IK kararıyla (İbrahim Gürhan, IK adına, 2026-11-05) izin günü iş günü olarak sayılır:
Cumartesi ve Pazar hafta tatilidir, 2026–2027 resmî tatilleri kodda sabit bir listededir. IK'nın
tatil girebileceği ekran ayrı iştir (kalıcılık, OD-8, sonrası).

## Kararlar (clarify)
- **K-1 Hafta tatili:** Cumartesi ve Pazar. İzin günü = aralıktaki (başlangıç ve bitiş dahil)
  Pazartesi–Cuma günlerinden resmî tatil olmayanların sayısı. Tek hesap; bakiye, Kullanılan,
  Bekleyen, onay ve Talepler ekranının "Gun" sütunu aynı sayıyı kullanır.
- **K-2 Resmî tatil listesi (2026–2027, 2429 sayılı Kanun; dini bayramlar Diyanet takvimi):**
  1 Ocak, 23 Nisan, 1 Mayıs, 19 Mayıs, 15 Temmuz, 30 Ağustos, 29 Ekim (her iki yıl);
  Ramazan Bayramı 20–22 Mart 2026 ve 9–11 Mart 2027; Kurban Bayramı 27–30 Mayıs 2026 ve
  16–19 Mayıs 2027. IK, PLAN öncesi tarihleri Resmî Gazete'den teyit eder; bir tarih değişirse
  spec değişikliğidir (R-08).
- **K-3 Arife yarım günleri** (19 Mart 2026, 26 Mayıs 2026, 28 Ekim 2026 ve 2027, 8 Mart 2027,
  15 Mayıs 2027): **tam iş günü sayılır.** Bakiye tam gün birimiyle çalışıyor (Hak, mesajlar,
  tablo); yarım gün kesirli bakiye ister. Yarım gün kuralı yeni açık karar olarak kaydedilir.
- **K-4 Listenin dışındaki yıllar** (2026 öncesi, 2028 ve sonrası): yalnız hafta sonu düşülür,
  uyarı ya da red yok. Sınır `docs/domain.md`'ye yazılır; listenin bakımı yeni açık karar.
- **K-5 İş günü içermeyen talep** (yalnız hafta sonu ya da tatil, ör. 14–15 Kasım 2026 ya da
  29 Ekim 2026): kaydedilmez; formun üstünde "Seçilen tarihler arasında iş günü yok." mesajı,
  400. İhlal sırası: bozuk girdi → personel → tarih aralığı → **iş günü yok** → bakiye.
- **K-6 Kayıtlar değişmez:** açılış verisindeki talep kayıtları (tarihler, durumlar) aynı kalır;
  yalnız hesaplanan sayılar değişir.
- **K-7 Testler:** eski sayıları ya da hafta sonuna denk gelen sınır örneklerini sabitleyen mevcut
  testler (BUILD öncesi deneme, yalnız domain değiştirilerek: 26 test kimliği) yeni sayılara aynı
  sıkılıkta taşınır; 0013'ün dersiyle plan, web dahil tam denemeyle listeyi adıyla verir.

### Hasım okur taraması (onaylı)
- **S-1 Uzun aralıklar:** tarih girdisinin üst sınırı yok; hesap aralık uzunluğundan bağımsız
  sürede yapılır (plan). Spec'e yeni sınır eklenmez.
- **S-2 Eski veride 0 günlük bekleyen talep:** onayı her zaman geçer (Kalan ≥ 0); özel kural yok.
- **S-3 Boyut:** tek yetenek, 5 CB; bölme yok.

Spec onayı: İbrahim Gürhan, IK adına, 2026-11-05 (K-1…K-7, S-1…S-3 önerildiği gibi; K-2 tarihleri
teyitli).

## Changed behavior
- [ ] CB-1 — **İş günü hesabı (K-1, K-2):** Pzt–Cum bir hafta → 5; 13–16 Kasım 2026 (Cum–Pzt) → 2;
  26–30 Ekim 2026 (29 Ekim dahil) → 4; 28 Aralık 2026–1 Ocak 2027 → 4; 8–12 Mart 2027 (arife +
  bayram) → 2 (K-3: arife 1 gün); başlangıç = bitiş = iş günü → 1.
- [ ] CB-2 — **İş günü yok (K-5):** 14–15 Kasım 2026 (Cmt–Pzr) ya da 29 Ekim 2026 için talep
  kaydedilmez, mesaj formun üstünde, yanıt 400, iç kod yok. Servis tipli bir istisna verir. Ters
  tarih ve olmayan personel bu kontrolden önce gelir.
- [ ] CB-3 — **Ekranlar (K-6):** Talepler ekranında #1 "Gun" 9, #7 "Gun" 10, diğerleri aynı; ana
  sayfada Ayse Hak 26, Kullanilan 9, Kalan 17, Bekleyen 3; diğer personelin satırları aynı.
- [ ] CB-4 — **Bakiye iş günüyle (0013 kuralı aynı):** Zeynep (Kalan 14, Bekleyen 1) için 1–17
  Aralık 2026 (13 iş günü) kaydedilir, 1–18 Aralık (14 iş günü) kaydedilmez, mesaj "(kalan 14 gün,
  bekleyen 1 gün, talep 14 gün)"; ekran ve servis aynı kararı verir. Onay da iş günüyle
  kontrol edilir.
- [ ] CB-5 — **Belgeler:** `docs/domain.md` BR-3 kararı (iş günü, liste, arife, liste dışı yıllar),
  BR-9'a iş günü yok kuralı, OD-4 kapanır; yeni açık kararlar: arife yarım günü, tatil listesinin
  bakımı / 2028.

## Preserved behavior
- [ ] PB-1 — **Bakiye ve onay kuralları:** 0013 (Kalan − Bekleyen ≥ gün; onay Kalan ≥ gün, diğer
  bekleyenler sayılmaz), BR-6 tam kullanım kabul, BR-10 geçişleri ve mesaj metinleri aynı.
- [ ] PB-2 — **Hafta içi aralıklar:** hafta sonu ve tatil içermeyen aralıklarda gün sayısı
  bugünküyle aynı (ör. #2, #3, #4, #5, #6, #8; 16–18 Kasım 2026 → 3).
- [ ] PB-3 — **Diğer kurallar:** ters tarih (BR-9) mesajı, olmayan personel, bozuk girdi, geçmiş
  tarihli talep (BR-8), sayaçlar 4 / 1 / 3, CSRF (0011) aynı.
- [ ] PB-4 — **Ekran düzeni:** üç ekranın düzeni, başlıkları ve Yeni Talep formu değişmez.
- [ ] PB-5 — **Testler:** yalnız plan haritasında adıyla sayılan testler değişir; diğer test
  dosyaları blob-identical; `scripts/check` full yeşil.

## Out of scope
- IK'nın tatil girdiği ekran, tatillerin kalıcı saklanması (OD-8 sonrası).
- Yarım gün izin ve kesirli bakiye; arife öğleden sonrası (yeni açık karar).
- Kıdem ve hak kuralları (OD-1, OD-2), devreden izin (OD-6).
- Açılış verisinin tarihlerini değiştirmek.
- Hafta sonu çalışan birimler için farklı hafta tatili.

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
