# Spec 0013 — bekleyen-bakiye (mini)

- Status: Shipped
- Mode: lite
- Plan: `specs/plans/0013-plan.md`
- Source: `docs/domain.md` OD-3
- Design: — (yeni sütun mevcut tablo düzeninde; ayrı tasarım yok, önce/sonra ekran görüntüsü kanıttır)
- Supersedes: 0008/CB-1 (bakiye sınırı ve mesaj örnekleri), 0001/AC-7 (bakiye tablosu sütunları),
  0010/AC-3 ve 0010/AC-5 (araya giren onay senaryosunun kurulumu)

## Intent
Bugün bir personel, kalan bakiyesini toplamda aşan birden çok talep bekletebilir: her talep
yalnızca onaylanmış izinlere göre kontrol edilir, aşım ancak onayda yakalanır ve IK reddetmek
zorunda kalır. IK kararıyla (İbrahim Gürhan, IK adına, 2026-11-05) yeni talep, bekleyen talepler
de hesaba katılarak kontrol edilir ve bakiye tablosu bekleyen günleri ayrı gösterir. "Kalan"
anlamını korur (Hak − Kullanılan); onay kontrolü bugünkü gibi kalır.

## Kararlar (clarify)
- **K-1 Bekleyen:** personelin `Beklemede` durumundaki tüm taleplerinin izin günleri toplamı;
  tarihe bakılmaz (geçmiş tarihli bekleyen talep de sayılır, BR-8). `Onaylandi` Kullanılan'a,
  `Reddedildi` hiçbir hesaba girmez.
- **K-2 Yeni talep kontrolü:** Kalan − Bekleyen ≥ talebin izin günü ise talep oluşur; tam
  kullanan talep kabul edilir (BR-6 sınırı korunur, yalnız karşılaştırılan değer değişir).
- **K-3 Mesaj:** red mesajı üç sayıyı da her zaman verir:
  "Kalan izin bakiyeniz yetersiz (kalan K gün, bekleyen B gün, talep N gün)." Bekleyen 0 olsa da
  aynı biçim (tek biçim, öngörülebilir).
- **K-4 Onay (yorum 2):** onay kontrolü değişmez: Kalan ≥ talebin izin günü (0010/AC-4). Onaylanan
  talep Bekleyen'den çıkar, Kullanılan'a girer; iki kez sayılmaz. Onay mesajı değişmez.
- **K-5 Sütun:** bakiye tablosunun en sağına "Bekleyen" sütunu: Ad, Birim, Hak, Kullanilan,
  Kalan, Bekleyen. Kalan = Hak − Kullanilan yan yana okunmaya devam eder.
- **K-6 Testler:** eski kuralı sabitleyen mevcut testler (14 test kimliği, 8 düzenleme noktası:
  plan 0013 T1–T8; revizyon 1 plan onayında, revizyon 2 BUILD'de R-07 ile) yeni kurala göre güncellenir; bu bir test zayıflatması değil, Supersedes satırındaki
  kriterlerin yerine geçmesidir. Her sınır testi yeni sınırla (K − B − 1 / K − B / K − B + 1) aynı
  sıkılıkta kalır. Araya giren onay senaryosu (0010/AC-3, AC-5) yeni kuralla yeni talep üzerinden
  kurulamaz; kurulumu bekleyen talebi doğrudan depoya ekleyerek yapılır (kural öncesinden kalan
  veri durumu).

Spec onayı: İbrahim Gürhan, 2026-11-05 (K-1…K-6, S-1 önerildiği gibi).

## Changed behavior
- [x] CB-1 — **Yeni talep bekleyenleri sayar (K-1, K-2):** Zeynep Kaya (Kalan 14, Bekleyen 1:
  #3) için 12 ve 13 günlük talep kaydedilir, 14 günlük talep kaydedilmez. Ekran ve servis aynı
  kararı verir. Bekleyeni olmayan personelde sınır değişmez (Mehmet Demir #2 reddedildikten sonra:
  Kalan 20 → 20 günlük talep kaydedilir, 21 kaydedilmez).
- [x] CB-2 — **Mesaj (K-3):** Zeynep'in 14 günlük talebi reddedilince formun üstünde "Kalan izin
  bakiyeniz yetersiz (kalan 14 gün, bekleyen 1 gün, talep 14 gün)." görünür, kayıt oluşmaz, yanıt
  400. Elif Sahin 1 gün → "(kalan 0 gün, bekleyen 0 gün, talep 1 gün)". Mesajda iç kod yok.
  Kalan − Bekleyen sıfırın altındaysa (kural öncesi veri) özel durum yok: her talep reddedilir,
  mesaj kalan ve bekleyeni olduğu gibi verir; negatif bir "kullanılabilir" sayı gösterilmez (S-1).
- [x] CB-3 — **Bakiye tablosu (K-5):** ana sayfa tablosu başlığı Ad, Birim, Hak, Kullanilan, Kalan,
  Bekleyen; açılış verisinde Bekleyen sırasıyla Ayse 3, Mehmet 3, Zeynep 1, Ahmet 5, Elif 0;
  Hak / Kullanilan / Kalan değerleri bugünküyle aynı.
- [x] CB-4 — **Durum geçişleri sayıları taşır (K-1, K-4):** #2 onaylanınca Mehmet Kullanilan 3,
  Kalan 17, Bekleyen 0; #4 reddedilince Ahmet Kalan 20, Bekleyen 0; Zeynep'e 2 günlük talep
  kaydedilince Bekleyen 1 → 3. Onaylanan bir talebin günleri hiçbir anda iki kez sayılmaz.
- [x] CB-5 — **Belgeler:** `docs/domain.md` BR-5 yeni kuralı yazar, BR-6 karşılaştırmayı
  (Kalan − Bekleyen) yazar, OD-3 kapanır (karar ve tarih).

## Preserved behavior
- [x] PB-1 — **Onay kontrolü (0010/AC-4):** Kalan K iken K − 1, K, K + 1 günlük bekleyen talep
  için onay sonucu onaylandı / onaylandı / yetersiz; mesaj "Personelin kalan izin bakiyesi
  yetersiz (kalan K gün, talep N gün)." değişmez. Diğer bekleyen talepler onayı engellemez.
- [x] PB-2 — **Araya giren onay (0010/AC-3, AC-5; kurulum K-6):** Ayse için bekleyen 12 günlük
  talep onaylanınca Kalan 2; bekleyen #5 (3 gün) onaylanamaz, `Beklemede` kalır, aynı mesaj;
  #5 reddedilebilir.
- [x] PB-3 — **Kalan ve diğer kurallar:** Kalan = Hak − Kullanılan (BR-5'in hesabı); ihlal sırası
  bozuk girdi → personel → tarih aralığı → bakiye (0008); geçmiş tarihli talep kabul (BR-8);
  red bakiyeye bakmaz (BR-10); sayaçlar Bekleyen 4 / Onaylanan 1 / Reddedilen 3.
- [x] PB-4 — **Ekranlar:** Talepler ve Yeni Talep ekranları ile CSRF davranışı (0011) değişmez;
  ana sayfada yalnız yeni sütun eklenir.
- [x] PB-5 — **Testler:** yalnız K-6'da sayılan eski-kural testleri değişir (her biri plan
  haritasında adıyla); diğer test dosyaları blob-identical; `scripts/check` full yeşil.

## Out of scope
- "Kullanılabilir" (Kalan − Bekleyen) için ayrı sütun ya da Kalan'ın anlamını değiştirmek.
- Onayda diğer bekleyen talepleri saymak (yorum 1; reddedildi).
- Açılış verisinde kuralı zaten aşan bekleyen talepleri temizlemek (açılış verisinde yok).
- İş günü hesabı (OD-4), yetkilendirme, Talepler ekranında bakiye göstermek.

## Review (2026-11-05, HEAD `67e7f5a`, bağımsız reviewer subagent)
Round 1: **clean** — engelleyici / yüksek / orta / düşük bulgu yok; 14/14 mutant kırmızı (onayda
bekleyen sayma M1/M1b dahil); T1–T8 eşit ya da daha sıkı; plan dışı dosya yok. Repo dışında
`git archive` kopyasında: `203 passed, 5 skipped`, ruff temiz.

### Triage (İbrahim Gürhan, 2026-11-05)
- **I-1 — noise:** Mehmet sınır testi (`test_no_pending_boundary_unchanged`) yalnız ekranı sınar.
  Karar tek fonksiyonda (`_check_balance`); ekran + servis uyumu Zeynep testinde, "bekleyen 0 gün"
  biçimi T4'te sınanıyor.
- **I-2 — noise:** `"-1" not in text` dar; asıl koruma aynı testteki tam mesaj eşleşmesi, negatif
  sayı hangi biçimde yazılsa bozulur.
- **I-3 — noise:** T7 (`row[1:5]`) üç onay ekranı testinde fazladan sütun kontrolünü bırakır; tam
  satır ve başlık T2 ile `test_balance_table_shows_pending`'de, sütun yer değişimi (M6) T7'nin üç
  testini de kırdı.

## Verification (VERIFY, 2026-11-05, HEAD `e23289b`, bağımsız QA subagent)
Deneyler, gerçek süreç ve ekran görüntüleri repo dışında, scratch'teki `git archive` kopyalarında
(`main` `ac60e7b` ve HEAD) üretildi; hiçbiri commit'lenmedi. Suite: HEAD `203 passed, 5 skipped`,
`CHECK GREEN (full)`; `main` `190 passed, 5 skipped`. Ters kontrol: HEAD'in
`tests/test_pending_balance.py` testleri `main`'in kodunda `8 failed, 5 passed` (yeşil kalan 5,
eski kuralda da doğru olan davranış). Onayda bekleyen sayan mutant: 9 test kırmızı.

| Kriter | Kanıt | Durum |
|---|---|---|
| CB-1 | `test_new_request_counts_pending[×3]` (ekran + servis), `test_no_pending_boundary_unchanged[20/21]`, T3/T5/T6, `test_past_dated_pending_counts`; ters kontrolde `[available+1]` kırmızı. Gerçek süreç: Zeynep 14 gün HEAD 400 / `main` 302; 13 gün ikisinde 302 | Pass |
| CB-2 | `test_balance_message_names_pending`, T4 (Elif "bekleyen 0 gün"), `test_negative_available_has_no_special_case` (S-1). Gerçek süreç: Zeynep 14 ve Elif 1 mesajları birebir, formun üstünde | Pass |
| CB-3 | `test_balance_table_shows_pending` (`main`'de kırmızı), T2. Gerçek süreç: başlık + 3/3/1/5/0; Hak/Kullanilan/Kalan `main` ile aynı. Önce/sonra ana sayfa ekran görüntüsü | Pass |
| CB-4 | `test_transitions_move_days[approve/reject/new]` (`main`'de kırmızı). Gerçek süreç: #2 onay → Mehmet 3/17/0, #4 red → Ahmet 20/0; onaylarda Kullanilan + Bekleyen hep 14, çift sayım yok | Pass |
| CB-5 | `docs/domain.md` diff: BR-5, BR-6 (+ S-1), BR-10 (K-4), OD-3 kapandı | Pass |
| PB-1 | `test_approve_balance_boundary` (değişmedi), `test_other_pending_do_not_block_approval`; onay mutantında ikisi de kırmızı. Gerçek süreç: onay mesajı aynı; Zeynep #3, 13 günlük bekleyen varken onaylandı | Pass |
| PB-2 | Araya giren onay testleri yeşil; T1 yalnız kurulum (diff okundu) | Pass |
| PB-3 | Baseline, ihlal sırası, sayaç testleri yeşil; gerçek süreçte sayaçlar iki sürümde 4/1/3 | Pass |
| PB-4 | `test_csrf.py` ve ekran testleri yeşil; `/requests` ve `/new` HTML ve PNG `main` ↔ HEAD bayt bayt aynı; CSRF'siz POST iki sürümde aynı 400 | Pass |
| PB-5 | `tests/` diff'i: 5 dosyada yalnız T1–T8 hunk'ları + yeni dosya; diğer test dosyaları ve `conftest.py` blob-identical; silme yok | Pass |

Ekran görüntüleri (repoda değiller, PR'a eklenir): ana sayfa önce/sonra, HEAD hata ekranı (Zeynep
14 gün), mesaj biçimi önce/sonra (Zeynep 15, Elif 1), korunan ekranlar (Talepler, Yeni Talep).

### VERIFY triage (İbrahim Gürhan, 2026-11-05)
- **G-1 — kabul:** `main`'de Zeynep 14 gün kaydedildiği için "önce" hata ekranı yok — farkın
  kendisi davranış değişikliği. Mesaj biçimi, iki sürümde de hata veren Zeynep 15 ve Elif 1 ile
  karşılaştırıldı.
- **G-2 — kabul:** QA kopyası git ağacı olmadığından exec-bits adımı orada atlandı; repoda ship
  commit'inden sonra `scripts/check` full ve CI çalışır. `scripts/` ve `tools/` değişmedi.
- **G-3 — kapsam dışı, ayrı issue:** bakiye hatasında form yeniden çizilince personel seçimi
  Ayse'ye döner, tarihler boşalır (kullanıcı yanlış personele talep girebilir). `main`'de de aynı;
  0013'ün regresyonu değil.

## Definition of Done
- [x] `scripts/check` green
- [x] Independent review done; real findings fixed, noise rejected with written rationale
- [x] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots)
- [x] Spec moved to `specs/done/` (immutable there)

## Scorecard (fill at ship — honest numbers make the process improvable)
| Metric | Value |
|---|---|
| Spec revisions | 2 (R-10 plan aşamasında: K-6 test sayısı; R-07 BUILD'de: T7/T8) |
| Fix rounds | 0 |
| Review findings: real / noise | 0 / 3 (round 1 clean; I-1…I-3 noise). VERIFY: G-1/G-2 kabul, G-3 ayrı issue |
| Regressions introduced | 0 |
| Bugs escaped to production | 0 (henüz yayında değil) |
