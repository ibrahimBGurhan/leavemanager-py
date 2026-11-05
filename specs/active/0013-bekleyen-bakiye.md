# Spec 0013 — bekleyen-bakiye (mini)

- Status: In progress
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
- [ ] CB-1 — **Yeni talep bekleyenleri sayar (K-1, K-2):** Zeynep Kaya (Kalan 14, Bekleyen 1:
  #3) için 12 ve 13 günlük talep kaydedilir, 14 günlük talep kaydedilmez. Ekran ve servis aynı
  kararı verir. Bekleyeni olmayan personelde sınır değişmez (Mehmet Demir #2 reddedildikten sonra:
  Kalan 20 → 20 günlük talep kaydedilir, 21 kaydedilmez).
- [ ] CB-2 — **Mesaj (K-3):** Zeynep'in 14 günlük talebi reddedilince formun üstünde "Kalan izin
  bakiyeniz yetersiz (kalan 14 gün, bekleyen 1 gün, talep 14 gün)." görünür, kayıt oluşmaz, yanıt
  400. Elif Sahin 1 gün → "(kalan 0 gün, bekleyen 0 gün, talep 1 gün)". Mesajda iç kod yok.
  Kalan − Bekleyen sıfırın altındaysa (kural öncesi veri) özel durum yok: her talep reddedilir,
  mesaj kalan ve bekleyeni olduğu gibi verir; negatif bir "kullanılabilir" sayı gösterilmez (S-1).
- [ ] CB-3 — **Bakiye tablosu (K-5):** ana sayfa tablosu başlığı Ad, Birim, Hak, Kullanilan, Kalan,
  Bekleyen; açılış verisinde Bekleyen sırasıyla Ayse 3, Mehmet 3, Zeynep 1, Ahmet 5, Elif 0;
  Hak / Kullanilan / Kalan değerleri bugünküyle aynı.
- [ ] CB-4 — **Durum geçişleri sayıları taşır (K-1, K-4):** #2 onaylanınca Mehmet Kullanilan 3,
  Kalan 17, Bekleyen 0; #4 reddedilince Ahmet Kalan 20, Bekleyen 0; Zeynep'e 2 günlük talep
  kaydedilince Bekleyen 1 → 3. Onaylanan bir talebin günleri hiçbir anda iki kez sayılmaz.
- [ ] CB-5 — **Belgeler:** `docs/domain.md` BR-5 yeni kuralı yazar, BR-6 karşılaştırmayı
  (Kalan − Bekleyen) yazar, OD-3 kapanır (karar ve tarih).

## Preserved behavior
- [ ] PB-1 — **Onay kontrolü (0010/AC-4):** Kalan K iken K − 1, K, K + 1 günlük bekleyen talep
  için onay sonucu onaylandı / onaylandı / yetersiz; mesaj "Personelin kalan izin bakiyesi
  yetersiz (kalan K gün, talep N gün)." değişmez. Diğer bekleyen talepler onayı engellemez.
- [ ] PB-2 — **Araya giren onay (0010/AC-3, AC-5; kurulum K-6):** Ayse için bekleyen 12 günlük
  talep onaylanınca Kalan 2; bekleyen #5 (3 gün) onaylanamaz, `Beklemede` kalır, aynı mesaj;
  #5 reddedilebilir.
- [ ] PB-3 — **Kalan ve diğer kurallar:** Kalan = Hak − Kullanılan (BR-5'in hesabı); ihlal sırası
  bozuk girdi → personel → tarih aralığı → bakiye (0008); geçmiş tarihli talep kabul (BR-8);
  red bakiyeye bakmaz (BR-10); sayaçlar Bekleyen 4 / Onaylanan 1 / Reddedilen 3.
- [ ] PB-4 — **Ekranlar:** Talepler ve Yeni Talep ekranları ile CSRF davranışı (0011) değişmez;
  ana sayfada yalnız yeni sütun eklenir.
- [ ] PB-5 — **Testler:** yalnız K-6'da sayılan eski-kural testleri değişir (her biri plan
  haritasında adıyla); diğer test dosyaları blob-identical; `scripts/check` full yeşil.

## Out of scope
- "Kullanılabilir" (Kalan − Bekleyen) için ayrı sütun ya da Kalan'ın anlamını değiştirmek.
- Onayda diğer bekleyen talepleri saymak (yorum 1; reddedildi).
- Açılış verisinde kuralı zaten aşan bekleyen talepleri temizlemek (açılış verisinde yok).
- İş günü hesabı (OD-4), yetkilendirme, Talepler ekranında bakiye göstermek.

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
