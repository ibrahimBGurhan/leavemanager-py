# Spec 0021 — yonetici-rolu

- Status: Approved
- Mode: lite
- Plan: `specs/plans/0021-plan.md`
- Source: ADR-0002 (`docs/decisions/0002-kimlik-dogrulama-uygulama-ici-sifre.md`) rol hedefi
  "Yönetici (biriminin talepleri)"; spec 0020 S-1 ve Constraints "spec 0021"; issue #43; ANALYZE
  kararları S-1…S-7 ve self-critique G-1…G-7 (İbrahim Gürhan, 2026-11-09)
- Supersedes: 0020/AC-7 ve 0020/R-1'in Yonetici kısmı (Yönetici artık Personel gibi değil, birim
  kapsamıyla çalışır); 0020/R-5 "Talepleri yalnız İK onaylar ya da reddeder" (Yönetici de birimi
  için sonuçlandırır)
- Design: — (none — the flow below is the design)

## Intent
Yöneticiler bugün yalnız kendi izinlerini görebiliyor; birimlerindeki çalışanların izinlerini görmek
ve karara bağlamak için İK'ya bağımlılar. Bu iş, Yönetici hesabına kendi biriminin personelini,
bakiyelerini ve taleplerini görme ve birimindeki bekleyen talepleri onaylama ya da reddetme yetkisi
verir. Onay tek aşamalıdır: Yönetici'nin ya da İK'nın kararı talebi sonuçlandırır (S-1). İK bugünkü
gibi her şeyi görür ve her talebi sonuçlandırır; Personel için hiçbir şey değişmez. Başarı: bir
yönetici başka birimin hiçbir verisini görmez ve hiçbir talebini sonuçlandıramaz, adres elle
yazılsa bile; kendi talebini de sonuçlandıramaz; onaylanan talep bugünkü bakiye kuralıyla
`Onaylandi` olur; log kararı kimin verdiğini söyler. Bilinçli olarak yapılmayanlar: iki aşamalı
onay, birim ve yönetici yönetim ekranları, Yönetici'nin başkası adına talep açması, talep geri
çekme.

## Requirements
- **R-1 Birim (S-3):** Yönetici'nin birimi, hesabının bağlı olduğu personel kaydının "Birim"
  değeridir. "Birimindeki personel", Birim değeri bununla tam olarak aynı olan tüm personel
  kayıtlarıdır (yöneticinin kendisi dahil). Karşılaştırma tam eşleşmedir: büyük / küçük harf
  ve baştaki / sondaki boşluk dahil; veri tahminle düzeltilmez (G-3). Birim değeri boş ya da
  yalnız boşluk olan Yönetici birim kapsamı almaz, Personel gibi yalnız kendi verisini görür
  (G-2). Bir birimde birden çok yönetici olabilir. Kural her istekte güncel kayıtlarla uygulanır.
- **R-2 Görünürlük:** Yönetici yalnız birimindeki personelin adını, birimini, bakiyesini ve
  taleplerini görür. Başka birimin hiçbir verisi hiçbir ekranda ve hiçbir iletide görünmez (spec
  0020 R-1, R-3, R-8 kalıbı; hata ve CSRF ekranları dahil).
- **R-3 Ana Sayfa (S-4, G-5):** Yönetici için üç kutu (Bekleyen, Onaylanan, Reddedilen) birimin
  taleplerinin sayısıdır (talep sayısı, gün değil); "Personel Bakiyeleri" tablosunda birimindeki her personelin satırı
  vardır (Hak, Kullanılan, Kalan, Bekleyen bugünkü hesapla). Ekranın düzeni değişmez.
- **R-4 Talepler:** Yönetici birimindeki tüm talepleri görür. Birimindeki **başka** bir personelin
  `Beklemede` talebinde Onayla / Reddet düğmeleri vardır; kendi talebinde ve sonuçlanmış taleplerde
  yoktur.
- **R-5 Sonuçlandırma (S-1, S-2):** Yönetici birimindeki başka bir personelin bekleyen talebini
  onaylar ya da reddeder; kurallar ve iletiler bugünkü gibidir (BR-10: onayda bakiye kontrolü,
  yetersizse talep `Beklemede` kalır ve bugünkü ileti; sonuçlanmış talep geri alınmaz). Kendi
  talebini sonuçlandıramaz. İK her talebi sonuçlandırır (yöneticinin talebi dahil). Karar tek
  aşamalıdır; ikinci bir onay beklenmez. Birimdeki başka bir yöneticinin talebi de "başka bir
  personelin talebi"dir ve sonuçlandırılabilir (G-1). Onayda bakiye yetersizliği iletisi bugünkü
  gibi personelin kalan gününü gösterir; yönetici bu bakiyeyi Ana Sayfa'da zaten görür (G-7).
- **R-6 Yetkisiz işlem (S-6):** Yönetici'nin kendi talebine, başka birimdeki bir talebe, olmayan ya
  da sonuçlanmış bir talebe ve geçersiz numaraya onay / red denemesi spec 0020 R-6'daki gibi
  reddedilir: 403, "Bu işlem için yetkiniz yok.", hiçbir kayıt değişmez, log'a WARNING. Yetki,
  talebin varlığından ve durumundan önce denetlenir; başka birimin talepleri hakkında hiçbir bilgi
  sızmaz. Talepler ekranının başarı iletisi parametreleri başka birimin bir talebini gösteriyorsa
  hiçbir ileti gösterilmez (spec 0020 AC-9 kalıbı; G-6).
- **R-7 Yeni Talep (S-5):** Yönetici yalnız kendi adına talep açar; formda personel seçimi yoktur,
  kendi adı sabit görünür (spec 0020 R-4). Birimindeki başka bir personel ya da başka bir birim
  adına gönderim R-6'daki gibi reddedilir.
- **R-8 Bağlı personel kaydı olmayan Yönetici:** spec 0020 R-7 aynen: hiçbir veri görmez, talep
  açamaz, hiçbir talebi sonuçlandıramaz.
- **R-9 Karar log'u (S-7):** Her onay ve red log'a INFO olarak yazılır: talep numarası, yeni durum,
  kararı veren hesabın e-postası ve rolü, tek satırda:
  `izin talebi #<N>: <durum>, karar: <e-posta> (<rol>)` (G-4). Talebin nedeni, tarihleri ve
  personelin adı yazılmaz (KVKK). Bu İK kararları için de geçerlidir. Talep kaydına "onaylayan" bilgisi eklenmez.
- **R-10 Değişmeyenler:** İK'nın ve Personel'in ekranları, iletileri ve yetkileri spec 0020'deki
  gibidir. Giriş, oturum ve kilit (spec 0019) değişmez.
- **R-11 Belgeler:** `docs/security.md` (roller), `docs/domain.md` (BR-10, OD-7), `README.md`
  (rollerin ne gördüğü ve yaptığı) bugünkü duruma güncellenir.

## User experience
- **Flow (Yönetici):** giriş → Ana Sayfa (birimin sayıları ve satırları) → Talepler (birimin
  talepleri; başkalarının bekleyen taleplerinde Onayla / Reddet) → Onayla → Talepler'de "Talep #N
  onaylandı." ve durum `Onaylandi`.
- **States — Yönetici:**
  - *Ana Sayfa:* birimin sayıları, birimindeki her personelin satırı.
  - *Talepler:* birimin talepleri; başkasının bekleyen talebinde düğmeler; kendi talebinde ve
    sonuçlanmışlarda düğme yok.
  - *Onaylandı / Reddedildi:* bugünkü başarı iletisi ("Talep #N onaylandı." / "… reddedildi.").
  - *Onayda bakiye yetersiz:* bugünkü ileti, talep `Beklemede`.
  - *Yetkisiz işlem:* "Bu işlem için yetkiniz yok." (403), birime süzülmüş ekranla.
  - *Yeni Talep:* kendi adı sabit (spec 0020 gibi).
  - *Bağlı personel kaydı yok:* spec 0020'deki boş ekranlar.
  - *Form süresi dolmuş:* spec 0011 iletisi, birime süzülmüş ekranla.
- **States — İK, Personel:** spec 0020'deki gibi, değişiklik yok.
- **Design reference:** none — the flow above is the design.
- **Accessibility:** düğmeler bugünkü Onayla / Reddet form düğmeleri; iletiler düz metin, yalnız
  renge dayanmaz.

## Constraints & out of scope
- **Kısıtlar:** Yeni çalışma zamanı bağımlılığı yok; veritabanı şeması değişmez (S-7). Yetki kuralı
  spec 0020'deki tek yerde kalır (`docs/security.md` AuthZ). Domain durum değerleri değişmez
  (`Beklemede`, `Onaylandi`, `Reddedildi`; S-1).
- **Mevcut testler:** spec 0020'nin Yönetici davranışını sabitleyen test(ler) bu spec'le
  değişir (Supersedes 0020/AC-7); hangi satırların değiştiği planda R-07 onayına gelir. Başka
  mevcut test değişmez.
- **Kapsam dışı:** iki aşamalı onay ve yeni durum değerleri (S-1); talep kaydına "onaylayan"
  alanı (S-7); birim ve yönetici yönetim ekranları; Yönetici'nin başkası adına talep açması (S-5);
  talep geri çekme; İK'nın kendi talebine kısıt (spec 0020 S-2 aynen).

## Acceptance criteria
<!-- Test verisi: IT biriminden iki personel (A, M) ve Muhasebe'den B; M'ye bağlı Yonetici hesabı;
     her birinin Beklemede / Onaylandi / Reddedildi talepleri; İK ve A'ya bağlı Personel hesabı. -->
- [ ] AC-1 — İK hesabı spec 0020 AC-1'deki gibi her şeyi görür ve Yönetici'nin (M'nin) bekleyen
  talebi dahil her talebi sonuçlandırır; A'ya bağlı Personel hesabı spec 0020 AC-2…AC-6'daki gibi
  yalnız kendi verisini görür ve hiçbir talebi sonuçlandıramaz.
- [ ] AC-2 — Yönetici Ana Sayfa'da IT taleplerinin sayılarını ve IT'deki her personelin satırını
  (doğru Hak, Kullanılan, Kalan, Bekleyen) görür; B'nin adı ve Muhasebe sayfada yoktur.
- [ ] AC-3 — Yönetici Talepler'de IT'nin tüm taleplerini görür; A'nın bekleyen talebinde Onayla /
  Reddet vardır; M'nin kendi talebinde ve sonuçlanmış taleplerde yoktur; B'nin adı ve nedenleri
  sayfada yoktur.
- [ ] AC-4 — Yönetici A'nın bekleyen talebini onaylar (durum `Onaylandi`, "Talep #N onaylandı.")
  ve başka bir bekleyen talebini reddeder; bakiyesi yetmeyen bir talepte onay bugünkü iletiyi verir
  ve talep `Beklemede` kalır.
- [ ] AC-5 — Yönetici'nin onay ve red istekleri — M'nin kendi bekleyen talebi, B'nin bekleyen
  talebi, IT'de sonuçlanmış bir talep, olmayan bir talep ve sayısal olmayan numara — 403 ve
  "Bu işlem için yetkiniz yok." alır; hiçbir talep değişmez; yanıtta B'ye ait veri yoktur; her
  deneme için log'da bir WARNING vardır. Başarı iletisi parametreleriyle B'nin bir talebini
  gösteren adres hiçbir ileti göstermez (G-6).
- [ ] AC-6 — Yönetici Yeni Talep'te kendi adını sabit görür ve kendi adına talep açar; A adına ve
  B adına gönderim 403 alır, hiçbir talep oluşmaz.
- [ ] AC-7 — Birim kuralı: IT'ye bağlı ikinci bir Yönetici A'nın ve M'nin bekleyen talebini
  sonuçlandırabilir (G-1); Birim değeri farklı yazılmış ("It", " IT") bir personel IT yöneticisinin
  ekranında görünmez ve talebi sonuçlandırılamaz (G-3); Birim değeri boş bir personele bağlı
  Yönetici yalnız kendi verisini görür ve hiçbir talebi sonuçlandıramaz (G-2).
- [ ] AC-8 — Bağlı personel kaydı olmayan Yönetici hesabı spec 0020 AC-8'deki gibi boş ekran görür,
  talep açamaz ve bir onay isteği 403 alır.
- [ ] AC-9 — Yönetici'nin ve İK'nın her onay ve red kararı için log'da
  `izin talebi #<N>: <durum>, karar: <e-posta> (<rol>)` biçiminde bir INFO satırı vardır (G-4); talebin nedeni, tarihleri ve personelin adı log'da yoktur.
- [ ] AC-10 — Mevcut testler değişmeden geçer (spec 0020 Yönetici testleri planda onaylı
  satırlarla); `docs/security.md`, `docs/domain.md` (BR-10, OD-7) ve `README.md` bugünkü durumu
  anlatır.

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
