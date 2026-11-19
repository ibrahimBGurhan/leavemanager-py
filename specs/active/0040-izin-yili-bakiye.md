# Spec 0040 — izin-yili-bakiye

- Status: In progress
- Mode: lite
- Plan: `specs/plans/0040-plan.md`
- Source: `docs/domain.md` OD-11, OD-6 (karar: İbrahim Gürhan, IK adına, 2026-11-19)
- Supersedes: BR-5 "Kalan = Hak − Kullanılan" ve "Kullanılan = tüm zamanların onaylı talepleri"
  (BR-4); bakiye tablosunun "Hak · Kullanılan · Kalan · Bekleyen" sütunları (spec 0013); OD-6
  taslağı ("en fazla 5 gün devreder")
- Split: 0040 (bu spec, hesap + tablo) → 0041 acilis-bakiyesi (IK'nın açılış bakiyesini girdiği
  akış). **0041 ship edilmeden üretime alınmaz** (aşağıda Constraints).

## Intent
IK, yıllık izin hakkının her personelin işe giriş yıl dönümünde yeniden doğmasını ve
kullanılmayan iznin süresiz devretmesini istiyor. Bugün hak tek bir sayı ve hiç yenilenmiyor;
Kullanılan ise tüm zamanların toplamı, bu yüzden ikinci yılından itibaren her personelin kalanı
olduğundan az görünüyor. Başarı: bakiye tablosu her personel için Devreden, Bu yılın hakkı,
Kullanılan, Bekleyen, Kalan ve sonraki hak tarihini doğru gösterir; yeni talep ve onaydaki bakiye
kontrolü bu Kalan'la yapılır; IK'nın girdiği açılış bakiyesi (0041) varsa hesap ondan başlar.
Yapılmayan: avans izin, ayrılışta izin ücreti (md. 59), yarım gün (OD-9), açılış bakiyesinin
girişi (0041).

## Kararlar (clarify)
IK kararları (İbrahim Gürhan, IK adına, 2026-11-19; öneriler aynen kabul):
- **K-1 İzin yılı:** her personelin işe giriş yıl dönümünden bir sonrakine kadar. Yıl dönümü
  BR-2 ile aynıdır (29 Şubat'ta işe girenin yıl dönümü artık olmayan yıllarda 28 Şubat).
- **K-2 Hakkın doğması:** her yıl dönümünde, o gün tamamlanan kıdemin BR-1 kademesi kadar hak
  doğar ve aynı gün kullanılabilir. İlk yıl dolmadan hak yoktur.
- **K-3 Devir:** kullanılmayan izin sınırsız devreder, yanmaz. OD-6 kapanır; "en fazla 5 gün"
  taslağı geçersizdir. Hukuki teyit önerildi (K-2/K-3: md. 53, md. 59); IK kararı geçerlidir,
  teyit farklı çıkarsa spec değişikliğidir (R-08).
- **K-4 Düşüm sırası:** önce en eski haktan. İzin yanmadığı için toplamı değiştirmez; ileride bir
  yanma kuralı gelirse anlam kazanır (ilke olarak kayıtlı).
- **K-5 Talebin izin yılı:** talep, başlangıç tarihinin düştüğü izin yılına tek parça yazılır;
  yıl dönümünü kapsasa da bölünmez.
- **K-6 Avans yok:** yeni talep ve onay kontrolü **bugüne kadar doğmuş** haklarla yapılır;
  gelecek bir yıl dönümünden sonra başlayan talep henüz doğmamış hakkı kullanamaz (S-1 (a)).
  BR-6 ve BR-10'un kuralı ve mesajı aynen kalır, yalnız Kalan'ın tanımı değişir.
- **K-7 Kademe:** yeni kademe yalnız o yıl dönümünde doğan hakka uygulanır; önceki yıllarda
  doğmuş haklar değişmez.
- **K-8 Tablo sütunları** (S-2): Devreden · Bu yılın hakkı · Kullanılan · Bekleyen · Kalan ·
  Sonraki hak tarihi.
  - **Bu yılın hakkı:** son yıl dönümünde doğan hak; ilk yıl dolmadıysa 0.
  - **Kullanılan:** başlangıcı son yıl dönümü ya da sonrasında olan onaylı taleplerin izin günü
    (ileri tarihli onaylı talepler dahil; K-6 gereği bugünkü bakiyeden düşer).
  - **Kalan:** bugüne kadar doğmuş bütün haklar − bütün onaylı talepler.
  - **Devreden:** Kalan + Kullanılan − Bu yılın hakkı (önceki izin yıllarından kalan; tablonun
    her satırı Devreden + Bu yılın hakkı − Kullanılan = Kalan eşitliğini sağlar).
  - **Bekleyen:** BR-5 gibi (tarihe bakılmaz).
  - **Sonraki hak tarihi:** bir sonraki yıl dönümü (bugün yıl dönümüyse bir sonraki yılınki).
- **K-9 Açılış bakiyesi** (S-3, S-4): personelin bir açılış bakiyesi (tarih D, gün V) varsa:
  Kalan = V + D'den **sonraki** yıl dönümlerinde doğan haklar − başlangıcı D ya da sonrasında
  olan onaylı talepler. D'den önce başlayan onaylı talepler hesaba girmez (V'nin içindedir).
  Son yıl dönümü D ya da öncesindeyse Bu yılın hakkı 0'dır (V'nin içindedir) ve Kullanılan
  yalnız başlangıcı D ya da sonrasında olan onaylı talepleri sayar. Açılış bakiyesi yoksa hesap
  işe girişten başlar. Açılış bakiyesinin girişi, sınırları (S-5) ve ekranı (S-6) 0041'dedir.
  Bekleyen açılış tarihinden etkilenmez: D'den önce başlayan bekleyen talep de Bekleyen'de sayılır
  (BR-5, G-1); böyle bir talep sonradan onaylanırsa K-9 gereği bakiyeden düşmez (G-2).
- **K-10 Eksi Kalan** (S-7): olduğu gibi gösterilir (ör. −3); yeni talep BR-6 gereği reddedilir,
  özel durum yok.

## Self-critique (onaylı, 2026-11-19)
- **G-1** Açılış tarihinden önce başlayan bekleyen talep Bekleyen'de sayılır (BR-5 aynen) → K-9.
- **G-2** Böyle bir talep onaylanırsa bakiyeden düşmez (K-9 tutarlılığı); 0041'de giriş sırasında
  uyarı → Constraints.
- **G-3** 8 sütun dar ekranda bugünkü yatay kaydırmayla gösterilir; tasarım değişmez → User experience.
- **G-4** Sonraki hak tarihi YYYY-AA-GG → User experience.
- **G-5** Eski davranışı sabitleyen testler supersede edilir → Constraints.

## Requirements
- R-1 Hak her personelin işe giriş yıl dönümünde, o gün tamamlanan kıdemin kademesine göre doğar
  (K-1, K-2, K-7); doğmuş hak yanmaz (K-3).
- R-2 Kalan, Kullanılan, Devreden ve Bu yılın hakkı K-8 ve K-9'daki tanımlarla tek bir yerde
  hesaplanır; bakiye tablosu, yeni talep kontrolü ve onay kontrolü aynı değeri kullanır.
- R-3 Bir talep başlangıç tarihinin izin yılına tek parça yazılır (K-5).
- R-4 Yeni talep ve onay, bugüne kadar doğmuş haklarla kontrol edilir; ret mesajları bugünkü
  metinle, yeni Kalan değeriyle gösterilir (K-6).
- R-5 Bakiye tablosu K-8'deki altı değeri gösterir; kim hangi satırı görür bugünkü gibidir
  (IK tümü, Yönetici birimi, Personel kendisi).
- R-6 `docs/domain.md`: sözlük (Hak, Kullanılan, Kalan, Devreden, yeni: İzin yılı, Açılış
  bakiyesi), BR-1, BR-4, BR-5 güncellenir; OD-11 ve OD-6 kapanır.

## User experience
- **Flow:** kullanıcı Ana Sayfa'yı açar → "Personel Bakiyeleri" tablosunda görebildiği her
  personel için Ad, Birim, Devreden, Bu yılın hakkı, Kullanılan, Bekleyen, Kalan, Sonraki hak
  tarihi sütunlarını görür. Başka ekran değişmez.
- **States:** dolu tablo (IK, Yönetici, Personel — bugünkü satır kapsamıyla); ilk yılındaki
  personel (sayılar 0, sonraki hak tarihi ilk yıl dönümü); eksi Kalan (eksi işaretiyle). Boş
  tablo, yetkisiz erişim ve hata durumları bugünkü gibi kalır.
- **Design reference:** none — the flow above is the design (mevcut tablo düzeni, yalnız
  sütunlar). Dar ekranda tablo bugünkü gibi yatay kayar.
- **Accessibility:** sütun başlıkları metinle (`th`); sayı sütunları yalnız rakam ve eksi işareti;
  tarih YYYY-AA-GG (diğer ekranlar gibi).

## Constraints & out of scope
- **Üretim kapısı:** 0041 ship edilmeden üretime alınmaz; açılış bakiyesi girilmemiş eski
  personelin bakiyesi işe girişten bu yana bütün haklarla hesaplanır ve şişkin görünür (açılış
  verisinde Ayse Yilmaz: Kalan 345).
- Out of scope: açılış bakiyesinin girişi ve düzeltilmesi (0041); avans izin; ayrılışta izin
  ücreti (md. 59, bordro); yarım gün (OD-9); 18 yaş altı / 50 yaş üstü kuralı (OD-5); izin yanması.
- **0041'e devredilen (G-2):** IK açılış bakiyesi girerken personelin açılış tarihinden önce
  başlayan bekleyen talebi varsa uyarı görür (0041'de kriter olur).
- **Supersede edilen testler (G-5):** "Hak" sütununu ve eski Kalan'ı sabitleyen açılış verisi,
  ekran ve servis testleri bu spec'in kriterleriyle değiştirilir (supersede, zayıflatma değil;
  0014/0038 emsali); hangi testler olduğu planda tek tek listelenir.
- Yorum satırındaki OD-6 taslağı (`recalculate_year_end`) karar gereği geçersizdir.
- **Split:** proposed 0040 (hesap + tablo) and 0041 (açılış bakiyesi girişi); kabul edildi
  (İbrahim Gürhan, 2026-11-19). 0040'ta 12 kriter: tek yetenek (bakiye hesabı), K-9'un hesap
  kuralı burada, girişi 0041'de.

## Acceptance criteria
Bugün = 2026-10-23 (aksi yazılmadıkça). "P" = işe giriş 2023-06-01, açılış bakiyesi yok, talep yok.
- [ ] AC-1 — **Yıl dönümünde hak doğar:** P için Devreden 28, Bu yılın hakkı 14, Kullanılan 0,
  Kalan 42, Sonraki hak tarihi 2027-06-01. Bugün 2026-05-31 iken Devreden 14, Bu yılın hakkı 14,
  Kalan 28, Sonraki 2026-06-01; bugün 2026-06-01 iken Kalan 42, Sonraki 2027-06-01.
- [ ] AC-2 — **İlk yıl ve henüz başlamamış personel:** işe giriş 2026-06-01 → dört sayı 0,
  Sonraki 2027-06-01. İşe giriş 2027-02-01 (gelecek) → dört sayı 0, Sonraki 2028-02-01.
- [ ] AC-3 — **Kademe yalnız yeni hakka:** işe giriş 2020-11-01 → Devreden 56, Bu yılın hakkı 14,
  Kalan 70. Bugün 2026-11-01 iken (6. yıl) Bu yılın hakkı 20, Devreden 70, Kalan 90.
- [ ] AC-4 — **29 Şubat:** işe giriş 2020-02-29 → Bu yılın hakkı 20, Devreden 70, Sonraki
  2027-02-28; bugün 2028-02-28 iken Sonraki 2028-02-29.
- [ ] AC-5 — **Yıl dönümünü kapsayan talep tek parça:** P'nin onaylı 2026-05-25–2026-06-05 talebi
  (7 iş günü, Kurban Bayramı düşülür) önceki izin yılına yazılır: Kullanılan 0, Devreden 21,
  Kalan 35. Ayrıca onaylı 2026-06-08–2026-06-12 (5 gün) → Kullanılan 5, Kalan 30.
- [ ] AC-6 — **İleri tarihli onaylı talep bugünden düşer:** P'nin onaylı 2027-07-05–2027-07-09
  talebi (5 gün) → Kullanılan 5, Kalan 37, Devreden 28.
- [ ] AC-7 — **Yeni talep kontrolü (avans yok):** işe giriş 2025-06-01 (Kalan 14, Bekleyen 0):
  14 iş günlük talep kaydedilir; 2027-06-07–2027-06-25 talebi (15 iş günü, ikinci yıl dönümünden
  sonra) "Kalan izin bakiyeniz yetersiz (kalan 14 gün, bekleyen 0 gün, talep 15 gün)." ile
  reddedilir, kayıt oluşmaz. Ekran ve servis aynı sonucu verir.
- [ ] AC-8 — **Onay kontrolü:** P'nin Kalan'ı 42 iken 42 iş günlük bekleyen talep onaylanır,
  Kalan 0; 43 iş günlük bekleyen talep onaylanmaz, `Beklemede` kalır (BR-10 mesajı).
- [ ] AC-9 — **Açılış bakiyesi yıl dönümünden önce:** P'ye açılış (2026-01-01, 10): 2025-12-01
  başlangıçlı onaylı 5 günlük talep hesaba girmez; Bu yılın hakkı 14 (2026-06-01), Devreden 10,
  Kalan 24.
- [ ] AC-10 — **Açılış bakiyesi yıl dönümünden sonra:** P'ye açılış (2026-07-01, 10): Bu yılın
  hakkı 0, Devreden 10, Kalan 10; 2026-06-15 başlangıçlı onaylı talep hesaba girmez,
  2026-08-03–2026-08-07 onaylı talep (5 gün) → Kullanılan 5, Kalan 5. Bugün 2027-06-01 iken
  Bu yılın hakkı 14.
- [ ] AC-11 — **Eksi Kalan:** P'ye açılış (2026-07-01, 2) ve onaylı 2026-08-03–2026-08-07 (5 gün)
  → Kalan −3, Devreden 2, Kullanılan 5; tabloda "-3"; 1 günlük yeni talep "kalan -3 gün" mesajıyla
  reddedilir.
- [ ] AC-12 — **Ekran (açılış verisi, IK):** başlıklar sırasıyla Ad, Birim, Devreden, Bu yılın
  hakkı, Kullanılan, Bekleyen, Kalan, Sonraki hak tarihi; satırlar:
  Ayse Yilmaz IT 328 26 9 3 345 2027-03-15 · Mehmet Demir Muhasebe 90 20 0 3 110 2027-06-01 ·
  Zeynep Kaya IK 0 14 0 1 14 2026-11-10 · Ahmet Celik IT 70 20 0 5 90 2027-02-28 ·
  Elif Sahin Satis 0 0 0 0 0 2027-06-01. Yönetici yalnız biriminin, Personel yalnız kendi
  satırını aynı sütunlarla görür.

## Definition of Done
- [ ] Every acceptance criterion mapped to proof (test or reproducible observation)
- [ ] `scripts/check` green
- [ ] Independent review done; real findings fixed, noise rejected with written rationale
- [ ] Docs / ADRs updated if behavior or architecture changed (R-6)
- [ ] Spec moved to `specs/done/` (it becomes immutable there)

## Scorecard (fill at ship — honest numbers make the process improvable)
| Metric | Value |
|---|---|
| Spec revisions | |
| Fix rounds | |
| Review findings: real / noise | |
| Regressions introduced | |
| Bugs escaped to production | |
