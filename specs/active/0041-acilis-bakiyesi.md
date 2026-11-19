# Spec 0041 — acilis-bakiyesi

- Status: In progress
- Mode: lite
- Plan: `specs/plans/0041-plan.md`
- Source: `docs/domain.md` OD-11; spec 0040 K-9, G-2, review F-3 (karar: İbrahim Gürhan, IK adına,
  2026-11-19)
- Depends on: spec 0040 (açılış bakiyesi kaydı ve hesabı). **Bu spec ship edilince 0040'ın üretim
  kapısı kalkar.**

## Intent
Sistem öncesi izin kayıtları eksik olduğu için IK, her personel için belirli bir tarih itibarıyla
kalan izin gününü (açılış bakiyesi) girmek istiyor; 0040'ın hesabı işe girişten değil bu bilinen
noktadan başlar ve eski personelin bakiyesi şişkin görünmez. Başarı: IK yalnız kendisinin gördüğü
bir ekranda bütün personeli ve kimde açılış bakiyesi eksik olduğunu görür, açılış bakiyesini
girip düzeltebilir; ana sayfadaki bakiyeler hemen buna göre değişir; açılış bakiyesinden önceki
dönem için bedava izin ya da çift sayım oluşmaz. Yapılmayan: açılış bakiyesini silme, toplu içe
aktarma, geçmişini tutma.

## Kararlar (clarify)
0040'tan (İbrahim Gürhan, IK adına, 2026-11-19):
- **K-1 Sınırlar:** gün 0–365 arası tam sayı; açılış tarihi işe giriş tarihinden önce ve bugünden
  sonra olamaz (işe giriş günü ve bugün kabul); personel başına tek kayıt, IK düzeltir, son girilen
  geçerlidir.
- **K-2 Yetki:** ekranı ve işlemi yalnız IK kullanır.

Bu spec'in netleştirmesi (İbrahim Gürhan, IK adına, 2026-11-19; öneriler aynen kabul):
- **K-3 Ekran** (S-1): tek sayfa — üstte form (Personel, Açılış tarihi, Gün), altta bütün
  personelin listesi: Ad, Birim, İşe giriş, Açılış tarihi, Gün; açılış bakiyesi olmayanda son iki
  hücre boş.
- **K-4 G-2 uyarısı** (S-2): kayıt yapılır; başarı iletisinin altında uyarı, personelin açılış
  tarihinden önce başlayan bekleyen taleplerinin numaralarıyla.
- **K-5 Onay istisnası** (S-3, F-3): başlangıcı personelin açılış tarihinden önce olan bekleyen
  talep, onaylanırken bakiye kontrolüne girmez (onaylansa da bakiyeden düşmez, 0040 K-9).
  Diğer talepler için BR-10 aynen.
- **K-6 Açılış öncesi yeni talep** (S-4): başlangıcı personelin açılış tarihinden önce olan yeni
  talep oluşmaz; ileti: "Bu personelin açılış bakiyesi <YYYY-AA-GG> tarihli; daha önce başlayan
  izin açılış bakiyesine dahildir." Açılış bakiyesi olmayan personelde kural yok (BR-8 aynen).
- **K-7 Diğer roller** (S-5): Yönetici ve Personel açılış bakiyesini görmez; etkisi ana sayfa
  bakiyesindedir. Ana sayfa değişmez.
- **K-8 Log** (S-6): başarılı kayıt INFO: personel numarası ve giren hesap (e-posta, rol); ad,
  tarih ve gün yazılmaz. Yetkisiz deneme bugünkü "yetkisiz islem" WARNING düzeninde.
- **K-9 Hatalar** (S-7): Yeni Personel ekranının düzeni — ilk ihlal formun üstünde Türkçe ileti,
  girilen değerler formda kalır (bozuk tarih geri basılmaz, spec 0015 K-3), kayıt oluşmaz.
  İhlal sırası: personel → tarih → gün.

## Self-critique (onaylı, 2026-11-19)
- **G-1** Açılış tarihinden önce başlayan **onaylı** talepler hesaptan çıkar (açılış sayısının
  içindedir, 0040 K-9); bunun için ayrıca uyarı yok — uyarı yalnız bekleyen talepler için (K-4).
- **G-2** Formdaki personel listesi eklenme sırasıyla (Yeni Talep formu gibi).
- **G-3** Uyarı sayfa her açıldığında yeniden hesaplanır: yenilemede de görünür, ilgili talepler
  sonuçlandırılınca kaybolur.
- **G-4** Açılış tarihi alanı boş açılır (bugünle önceden doldurulmaz).
- **G-5** Form CSRF korumalı (mevcut düzen); geçersiz form mevcut CSRF iletisini alır, kayıt yok.
- **G-6** Onay istisnasına giren talebin onay iletisi bugünkü başarı iletisidir ("Talep #n
  onaylandı.").

## Requirements
- R-1 IK, bir personel için açılış tarihi ve gün girerek açılış bakiyesi kaydeder; aynı personelde
  yeni kayıt eskisinin yerine geçer (K-1). Kayıt sonrası sayfa yenilenince işlem tekrarlanmaz.
- R-2 Açılış bakiyesi sayfası bütün personeli listeler ve kayıtlı açılış bakiyelerini gösterir (K-3).
- R-3 Girdiler K-1 ve K-9'a göre doğrulanır; ihlalde kayıt oluşmaz.
- R-4 Kayıt sonrası, açılış tarihinden önce başlayan bekleyen talepler varsa IK uyarılır (K-4).
- R-5 Başlangıcı açılış tarihinden önce olan bekleyen talebin onayı bakiye kontrolü yapmaz (K-5).
- R-6 Başlangıcı açılış tarihinden önce olan yeni talep oluşmaz (K-6); ihlal sırası: bozuk girdi →
  personel → tarih aralığı → açılış öncesi → iş günü yok → bakiye.
- R-7 Ekran ve işlem yalnız IK'ya açıktır; menüde "Açılış Bakiyesi" yalnız IK'ya görünür (K-2, K-7).
- R-8 Kayıt ve yetkisiz deneme K-8'e göre loglanır.
- R-9 `docs/domain.md` (yeni BR: açılış bakiyesi; BR-9 ihlal sırası; BR-10 onay istisnası; OD-11
  üretim kapısı kalktı) ve `docs/security.md` (IK'ya özel işlemler) güncellenir.

## User experience
- **Flow:** IK menüde "Açılış Bakiyesi"ni açar → listede açılış bakiyesi olmayan personeli görür →
  formda personeli seçer, açılış tarihini ve günü girer, "Kaydet" → sayfa başarı iletisiyle (ve
  gerekirse uyarıyla) yeniden açılır, liste güncellenmiştir → Ana Sayfa'da bakiye yeni hesaptadır.
- **States:**
  - İlk açılış: boş form, liste (açılış bakiyesi olmayanlarda boş hücreler).
  - Başarı: "Personel #<n> açılış bakiyesi kaydedildi: <YYYY-AA-GG>, <gün> gün." + boş form.
  - Başarı + uyarı: başarı iletisinin altında "Açılış tarihinden önce başlayan bekleyen talepler:
    #<a>, #<b>. Bunlar onaylanırsa bakiyeden düşmez."
  - Hata: ilk ihlalin iletisi formun üstünde, değerler formda (K-9).
  - Yetkisiz (Yönetici, Personel): form ve liste çizilmez, "Bu işlem için yetkiniz yok." (403).
  - Personel yok: liste yalnız başlıktan oluşur; form personel listesi boş.
- **Design reference:** none — the flow above is the design (Yeni Personel ekranının düzeni ve
  bileşenleri, spec 0034/0035).
- **Accessibility:** her alanın görünür etiketi (Personel, Açılış tarihi, Gün); tarih alanı tarih
  girişi; klavyeyle Tab sırası form → Kaydet; iletiler metinle (renk tek başına anlam taşımaz).

## Constraints & out of scope
- Out of scope: açılış bakiyesini silme (açılış bakiyesiz hesaba dönüş), toplu içe aktarma, kayıt
  geçmişi, Yönetici/Personel'e gösterim, açılış bakiyesinin ana sayfada ayrı sütunu.
- Açılış tarihi gelecekte işe girecek personelde girilemez (tarih hem işe girişten sonra hem
  bugünden önce olmalı) — bu durumda tarih iletisi gösterilir.
- Kalıcılık 0040'ın depo kaydıdır (şema değişmez).
- **Split:** tek yetenek (açılış bakiyesi girişi ve etkileri); 12 kriter — bölünmez (K-5 ve K-6,
  girişin doğrudan sonucu; ayrı spec çift sayım/bedava izin açığı bırakır).

## Acceptance criteria
Bugün = 2026-10-23, açılış verisi; giriş yapan IK (aksi yazılmadıkça).
- [ ] AC-1 — **Yetki:** IK'nın menüsünde "Açılış Bakiyesi" var; Yönetici ve Personel'de yok.
  Yönetici ya da Personel sayfayı açarsa (GET) ya da form gönderirse (POST) 403, "Bu işlem için
  yetkiniz yok.", form ve liste yok, kayıt oluşmaz, WARNING log.
- [ ] AC-2 — **Liste:** başlıklar Ad, Birim, İşe giriş, Açılış tarihi, Gün; açılış verisinde 5
  personel sırayla, son iki hücre boş. Kayıttan sonra ilgili satırda tarih ve gün görünür.
- [ ] AC-3 — **Kayıt:** Mehmet Demir (#2) için 2026-01-01, 10 gün → yönlendirme, ileti
  "Personel #2 açılış bakiyesi kaydedildi: 2026-01-01, 10 gün.", boş form; Ana Sayfa'da Mehmet
  satırı Devreden 10, Bu yılın hakkı 20, Kullanılan 0, Bekleyen 3, Kalan 30, Sonraki 2027-06-01.
  Sayfa yenilenince ileti yine görünür, ikinci kayıt ya da log satırı oluşmaz.
- [ ] AC-4 — **Düzeltme:** Mehmet için ardından 2026-07-01, 5 gün → listede tek satır
  2026-07-01 / 5; Ana Sayfa'da Devreden 5, Bu yılın hakkı 0, Kalan 5.
- [ ] AC-5 — **Gün sınırları:** 0 ve 365 kaydedilir; -1, 366, 2.5, "abc" ve boş → "Gün 0 ile 365
  arasında bir tam sayı olmalı.", kayıt yok, personel ve tarih formda kalır.
- [ ] AC-6 — **Tarih sınırları:** Mehmet (işe giriş 2019-06-01) için 2019-06-01 ve 2026-10-23
  kaydedilir; 2019-05-31 → "Açılış tarihi işe giriş tarihinden (2019-06-01) önce olamaz.";
  2026-10-24 → "Açılış tarihi bugünden sonra olamaz."; boş ya da bozuk → "Geçerli bir açılış
  tarihi girin."; kayıt yok.
- [ ] AC-7 — **Personel ve ihlal sırası:** personel seçilmemiş → "Personel seçin."; olmayan numara
  (99) ya da sayı olmayan değer → "Personel bulunamadı."; personel, tarih ve gün birlikte bozuksa
  yalnız personel iletisi; tarih ve gün bozuksa yalnız tarih iletisi.
- [ ] AC-8 — **G-2 uyarısı:** Mehmet'in 2026-09-07 başlangıçlı bekleyen talebi (#9) varken
  2026-10-01 tarihli açılış bakiyesi kaydedilir ve başarı iletisinin altında "Açılış tarihinden önce
  başlayan bekleyen talepler: #9. Bunlar onaylanırsa bakiyeden düşmez." görünür; açılış verisinin
  #2'si (2026-11-02) listelenmez. Böyle talep yoksa uyarı görünmez.
- [ ] AC-9 — **Onay istisnası (F-3):** AC-8'deki #9, açılış bakiyesi 0 gün iken de onaylanır
  (`Onaylandi`), Kalan değişmez. Açılış tarihinden sonra başlayan bekleyen talep için BR-10 sınırı
  aynen (Kalan'ı aşan talep `Beklemede` kalır, ileti aynı).
- [ ] AC-10 — **Açılış öncesi yeni talep:** Mehmet'e 2026-10-01 tarihli açılış bakiyesi varken
  2026-09-28–2026-10-02 talebi "Bu personelin açılış bakiyesi 2026-10-01 tarihli; daha önce
  başlayan izin açılış bakiyesine dahildir." ile reddedilir (ekran ve servis), kayıt oluşmaz;
  2026-10-01 başlangıçlı talep bu kurala takılmaz. Ters tarih aralığı bu iletiden önce; yalnız hafta
  sonu olan açılış öncesi talep (2026-09-26–27) bu iletiyi alır (iş günü iletisinden önce).
  Açılış bakiyesi olmayan personelde geçmiş tarihli talep bugünkü gibi kabul (BR-8).
- [ ] AC-11 — **Log:** başarılı kayıtta tek INFO satırı: personel numarası ve giren hesap
  (e-posta, rol); ad, tarih ve gün sayısı satırda yok. Hatalı girişte INFO yok.
- [ ] AC-12 — **Docs:** `docs/domain.md` açılış bakiyesi kuralı (K-1, K-5, K-6), BR-9 ihlal sırası,
  OD-11'de üretim kapısının kalktığı; `docs/security.md` IK'ya özel işlemler listesinde açılış
  bakiyesi.

## Definition of Done
- [ ] Every acceptance criterion mapped to proof (test or reproducible observation)
- [ ] `scripts/check` green
- [ ] Independent review done; real findings fixed, noise rejected with written rationale
- [ ] Docs / ADRs updated if behavior or architecture changed
- [ ] Spec moved to `specs/done/` (it becomes immutable there)

## Scorecard (fill at ship — honest numbers make the process improvable)
| Metric | Value |
|---|---|
| Spec revisions | |
| Fix rounds | |
| Review findings: real / noise | |
| Regressions introduced | |
| Bugs escaped to production | |
