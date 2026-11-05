# Spec 0014 — is-gunu (mini)

- Status: Shipped
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
- [x] CB-1 — **İş günü hesabı (K-1, K-2):** Pzt–Cum bir hafta → 5; 13–16 Kasım 2026 (Cum–Pzt) → 2;
  26–30 Ekim 2026 (29 Ekim dahil) → 4; 28 Aralık 2026–1 Ocak 2027 → 4; 8–12 Mart 2027 (arife +
  bayram) → 2 (K-3: arife 1 gün); başlangıç = bitiş = iş günü → 1.
- [x] CB-2 — **İş günü yok (K-5):** 14–15 Kasım 2026 (Cmt–Pzr) ya da 29 Ekim 2026 için talep
  kaydedilmez, mesaj formun üstünde, yanıt 400, iç kod yok. Servis tipli bir istisna verir. Ters
  tarih ve olmayan personel bu kontrolden önce gelir.
- [x] CB-3 — **Ekranlar (K-6):** Talepler ekranında #1 "Gun" 9, #7 "Gun" 10, diğerleri aynı; ana
  sayfada Ayse Hak 26, Kullanilan 9, Kalan 17, Bekleyen 3; diğer personelin satırları aynı.
- [x] CB-4 — **Bakiye iş günüyle (0013 kuralı aynı):** Zeynep (Kalan 14, Bekleyen 1) için 1–17
  Aralık 2026 (13 iş günü) kaydedilir, 1–18 Aralık (14 iş günü) kaydedilmez, mesaj "(kalan 14 gün,
  bekleyen 1 gün, talep 14 gün)"; ekran ve servis aynı kararı verir. Onay da iş günüyle
  kontrol edilir.
- [x] CB-5 — **Belgeler:** `docs/domain.md` BR-3 kararı (iş günü, liste, arife, liste dışı yıllar),
  BR-9'a iş günü yok kuralı, OD-4 kapanır; yeni açık kararlar: arife yarım günü, tatil listesinin
  bakımı / 2028.

## Preserved behavior
- [x] PB-1 — **Bakiye ve onay kuralları:** 0013 (Kalan − Bekleyen ≥ gün; onay Kalan ≥ gün, diğer
  bekleyenler sayılmaz), BR-6 tam kullanım kabul, BR-10 geçişleri ve mesaj metinleri aynı.
- [x] PB-2 — **Hafta içi aralıklar:** hafta sonu ve tatil içermeyen aralıklarda gün sayısı
  bugünküyle aynı (ör. #2, #3, #4, #5, #6, #8; 16–18 Kasım 2026 → 3).
- [x] PB-3 — **Diğer kurallar:** ters tarih (BR-9) mesajı, olmayan personel, bozuk girdi, geçmiş
  tarihli talep (BR-8), sayaçlar 4 / 1 / 3, CSRF (0011) aynı.
- [x] PB-4 — **Ekran düzeni:** üç ekranın düzeni, başlıkları ve Yeni Talep formu değişmez.
- [x] PB-5 — **Testler:** yalnız plan haritasında adıyla sayılan testler değişir; diğer test
  dosyaları blob-identical; `scripts/check` full yeşil.

## Out of scope
- IK'nın tatil girdiği ekran, tatillerin kalıcı saklanması (OD-8 sonrası).
- Yarım gün izin ve kesirli bakiye; arife öğleden sonrası (yeni açık karar).
- Kıdem ve hak kuralları (OD-1, OD-2), devreden izin (OD-6).
- Açılış verisinin tarihlerini değiştirmek.
- Hafta sonu çalışan birimler için farklı hafta tatili.

## Review (2026-11-05, bağımsız reviewer subagent)
- **Round 1** (HEAD `f19d10d`): üretim kodunda bulgu yok; `count_workdays` rastgele 20.000 aralıkta
  gün gün sayan referansla 0 uyuşmazlık; 26 mutantın 24'ü kırmızı. Bulgular F-1…F-4 (yalnız testler).
- **Round 2** (HEAD `706a18a`, fix diff'i): **clean**; F-1…F-4 düzeldi, hayatta kalan iki mutant
  artık kırmızı.

### Triage (İbrahim Gürhan, 2026-11-05)
- **F-1 — real → fix-1 (`a302abb`):** "iş günü yok → bakiye" sırası Elif ile (0 − 0 < 0 yanlış)
  kanıtlanmıyordu; test negatif kullanılabilir bakiyeyle (Zeynep, Kalan 14, Bekleyen 15) servis +
  ekran olarak kuruldu. Mutant `nwd_after_balance` kırmızı.
- **F-2 — real → fix-1 (`ff932c7`):** ters aralık yalnız tek günle sınanıyordu; çok günlük ters
  aralık (20 → 2 Kasım = 0) eklendi. Mutant `reverse_neg` kırmızı.
- **F-3 — real → fix-1 (`a926bab`):** `end_after_workdays` n ≤ 0'da sonsuz döngü; `assert n >= 1`.
- **F-4 — real → fix-1 (`706a18a`):** `intervening_approval` docstring'i 15 iş günü / 14 gün.

## Verification (VERIFY, 2026-11-05, HEAD `0690a01`, bağımsız QA subagent)
Deneyler, gerçek süreç ve ekran görüntüleri repo dışında, scratch'teki `git archive` kopyalarında
(`main` `c9556d3` ve HEAD) üretildi; hiçbiri commit'lenmedi. Suite: HEAD `229 passed, 5 skipped`
(ruff temiz), `main` `203 passed, 5 skipped`; builder repo içinde `CHECK GREEN (full, 3 steps)`.
Ters kontrol: HEAD'in `tests/test_workdays.py` testleri `main`'in kodunda 19 kırmızı / 7 yeşil
(yeşiller eski kuralda da doğru olan hafta içi aralıklar ve sıra korumaları). Bağımsız referansla
20.000 rastgele aralıkta 0 uyuşmazlık; `HOLIDAYS` K-2 ile eşit (27 tarih).

| Kriter | Kanıt | Durum |
|---|---|---|
| CB-1 | `test_count_workdays[×13]`, `test_holidays_list_matches_k2`, `test_arife_days_count_as_full_days`, T4; ters kontrolde 9 parametre kırmızı; bağımsız script CB-1 örnekleri 5/2/4/4/2/1 | Pass |
| CB-2 | `test_no_working_days_refused[weekend/holiday]` (400, mesaj formun üstünde, kayıt yok, sızıntı yok; servis `NoWorkingDays`), sıra testleri; sıra ve 200 mutantları kırmızı. Gerçek süreç: 14–15 Kas ve 29 Eki → 400 + mesaj; ters tarih ve olmayan personel önce yakalanır | Pass |
| CB-3 | `test_screens_show_working_days`, T1, T2. Gerçek süreç: Talepler #1 = 9, #7 = 10, diğerleri aynı; ana sayfa Ayse 26/9/17/3. Önce/sonra ana sayfa ve Talepler ekran görüntüleri | Pass |
| CB-4 | `test_balance_counts_working_days[13/14]`, `test_approval_counts_working_days`, T3, T5–T7. Gerçek süreç: Zeynep 1–17 Ara kaydedildi (13), 1–18 Ara reddedildi "(kalan 14 gün, bekleyen 1 gün, talep 14 gün)" (`main`: "talep 18 gün") | Pass |
| CB-5 | `docs/domain.md` diff: BR-3, BR-9 (ihlal sırası, ters aralık 0), sözlük, OD-4 kapandı, OD-9, OD-10 | Pass |
| PB-1 | `test_pending_balance.py`, `test_approval.py`: T5/T6 yalnız sayıları ve tarih yardımcılarını değiştirir; assert yapısı ve mesajlar aynı | Pass |
| PB-2 | #2, #3, #4, #5, #6, #8 `main` ve HEAD'de aynı; 16–18 Kas → 3 | Pass |
| PB-3 | Ters tarih ve personel mesajları `main` ile birebir; CSRF, sayaçlar 4/1/3, geçmiş tarihli talep kabul | Pass |
| PB-4 | Önce/sonra ekran görüntülerinde başlıklar, sütunlar, form ve menü aynı; değişen yalnız sayılar ve yeni hata satırı | Pass |
| PB-5 | `tests/` diff'i: conftest yardımcısı, T1–T7 ve fix-1 hunk'ları, yeni `test_workdays.py`; `test_architecture`, `test_csrf`, `test_exec_bits`, `test_logging_config`, `test_security` blob-identical | Pass |

Ekran görüntüleri (repoda değiller, PR'a eklenir): ana sayfa ve Talepler önce/sonra; hafta sonu
talebi `main`'de kaydedilir, HEAD'de "iş günü yok" hatası; 29 Ekim hatası; Zeynep 1–18 Aralık
bakiye mesajı.

### VERIFY triage (İbrahim Gürhan, 2026-11-05)
- **G-1 — kabul:** QA kopyası git ağacı olmadığından exec-bits adımı orada çalışmadı; repoda ship
  commit'inden sonra `scripts/check` full ve CI çalışır. `scripts/` ve `tools/` değişmedi.
- **G-2 — kapsam dışı, zaten #31:** hata ekranında form sıfırlanıyor; `main`'de de aynı.
- **G-3 — kabul:** onayın iş günüyle kontrolü gerçek süreçte denenmedi; `test_approval_counts_working_days`
  ve T5 kanıtlar, onay `calc_days`'i kullanır (tek hesap, review round 1'de doğrulandı).

## Definition of Done
- [x] `scripts/check` green
- [x] Independent review done; real findings fixed, noise rejected with written rationale
- [x] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots)
- [x] Spec moved to `specs/done/` (immutable there)

## Scorecard (fill at ship — honest numbers make the process improvable)
| Metric | Value |
|---|---|
| Spec revisions | 0 |
| Fix rounds | 1 (fix-1: review F-1…F-4, yalnız testler) |
| Review findings: real / noise | 4 / 0 (F-1 orta, F-2…F-4 düşük; round 2 clean). VERIFY: G-1/G-3 kabul, G-2 → #31 |
| Regressions introduced | 0 |
| Bugs escaped to production | 0 (henüz yayında değil) |
