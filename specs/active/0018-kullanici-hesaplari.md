# Spec 0018 — kullanici-hesaplari

- Status: In progress
- Mode: lite
- Plan: `specs/plans/0018-plan.md`
- Source: ADR-0002 (`docs/decisions/0002-kimlik-dogrulama-uygulama-ici-sifre.md`) D-1…D-3;
  ANALYZE kararları S-1…S-7 (İbrahim Gürhan, 2026-11-05)
- Design: — (ekran yok; komut satırı aracı)

## Intent
Giriş sistemi (ADR-0002) kullanıcı hesaplarına ihtiyaç duyuyor ve ilk hesabın varsayılan bir
şifre olmadan kurulması gerekiyor. Bu iş hesapları kalıcı olarak saklar ve İK'nın (ya da sunucu
operatörünün) komut satırından hesap açmasını sağlar: e-posta, rol, gerektiğinde bağlı olduğu
personel ve ekranda görünmeden girilen bir şifre. Başarı: bir İK hesabı ve bir personel hesabı
açılabilir, yeniden başlatmada korunur, şifre hiçbir yerde açık metin olarak durmaz. Bilinçli
olarak yapılmayanlar: giriş / çıkış ekranı ve sayfaların kapatılması (spec 0019), rol bazlı
yetki, hesap yönetim ekranı, şifre değiştirme ve sıfırlama. Bu spec ile uygulamanın ekranları ve
davranışı değişmez.

## Requirements
- **R-1 Hesap açma aracı (D-2, S-2):** Bir komut satırı aracı yeni bir kullanıcı hesabı açar.
  Girdiler: e-posta, rol (Personel / Yönetici / IK) ve bağlı personel. Personel ve Yönetici
  hesabı var olan bir personel kaydına bağlanmak zorundadır; IK hesabında bağlantı isteğe
  bağlıdır, verilirse var olan bir personel olmalıdır. Rol harf büyüklüğüne bakılmadan
  `Personel`, `Yonetici`, `IK` olarak kabul edilir ve bu yazımla saklanır (G-3). Bir personele en
  fazla bir hesap bağlanır; ikinci hesap reddedilir (G-2).
- **R-2 Şifre girişi (D-2):** Şifre araç tarafından sorulur, yazılırken ekranda görünmez ve
  doğrulama için ikinci kez sorulur; iki giriş aynı olmalıdır. Şifre komut satırı argümanı ya da
  ortam değişkeni olarak alınmaz: argüman kabuk geçmişinde ve süreç listesinde görünür (G-4);
  testler şifreyi aracın girdisinden verir. Kodda, yapılandırmada ya da demo verisinde varsayılan şifre ya
  da varsayılan hesap yoktur.
- **R-3 Şifre kuralı (D-3):** Şifre en az 12 karakterdir; karmaşıklık kuralı yoktur. Şifre
  olduğu gibi kullanılır (baştaki / sondaki boşluk atılmaz).
- **R-4 Şifrenin saklanması (ADR-0002):** Şifre yalnız tek yönlü bir özet olarak saklanır; açık
  metni ya da geri çevrilebilir bir biçimi hiçbir yerde (veritabanı, log, ekran çıktısı) durmaz.
  Aynı şifreyi kullanan iki hesabın saklanan özetleri farklıdır.
- **R-5 E-posta (D-1, S-3):** E-posta baştaki / sondaki boşlukları atılıp küçük harfe çevrilerek
  saklanır ve karşılaştırılır. Tek bir `@` içermeli, iki yanı boş olmamalı, boşluk
  içermemeli (G-6; daha sıkı doğrulama yok). Aynı e-postayla
  (büyük / küçük harf farkı dahil) ikinci bir hesap açılamaz.
- **R-6 Yeni hesabın durumu:** Yeni hesap aktiftir ve başarısız giriş sayacı sıfır, kilidi
  yoktur. Hesap; e-postayı, şifre özetini, rolü, bağlı personeli, aktif / pasif durumunu, art
  arda başarısız deneme sayısını ve kilidin bitiş zamanını yeniden başlatmada korur (son ikisi
  spec 0019'da kullanılır, S-5).
- **R-7 Hata davranışı:** Geçersiz girdide (biçimsiz e-posta, var olan e-posta, bilinmeyen rol,
  eksik ya da olmayan personel, kısa şifre, eşleşmeyen şifreler) araç neyin yanlış olduğunu
  söyleyen Türkçe bir ileti yazar, başarısız çıkış koduyla biter ve **hiçbir hesap oluşmaz**.
  Veritabanı açılamıyorsa uygulamanın açılışındaki aynı kural geçerlidir (spec 0017 R-3).
- **R-8 Başarı çıktısı ve log:** Başarıda araç oluşan hesabın e-postasını ve rolünü yazar, başarılı
  çıkış koduyla biter. Log'a hesap açıldığına dair bir INFO yazılır (e-posta ve rol); şifre ya da
  özeti hiçbir iletide yer almaz.
- **R-9 Veritabanı:** Araç, uygulamanın kullandığı veritabanını aynı ayarla (`DATABASE_PATH`)
  kullanır. Bellek deposu modunda (`LEAVEMANAGER_STORAGE=memory`) hesap kalıcı olmayacağı için
  araç çalışmaz, bunu söyleyen bir iletiyle başarısız biter.
- **R-10 Depo sözleşmesi (ADR-0001, spec 0016):** Hesap kayıtları depo sözleşmesine eklenir;
  bellek ve SQLite deposu aynı sözleşme testlerinden geçer. Var olan bir veritabanı (spec 0017
  şeması) ilk açılışta kendiliğinden ve veri kaybı olmadan yeni şema sürümüne geçer; geçiş tek
  bir işlemdir, yarıda kalırsa veritabanı eski haliyle kalır. Bu sürümden yeni bir şemada spec
  0017 R-3 geçerlidir (G-5).
- **R-11 Değişmeyenler:** Uygulamanın ekranları, mesajları ve testleri değişmez; mevcut testler
  değişmeden geçer.
- **R-12 Belgeler:** Hesap açma aracının kullanımı (ilk İK hesabı dahil) `README.md` ya da
  `docs/` altında; `docs/architecture.md` ve `docs/security.md` bugünkü durum.

## User experience
- **Flow (operatör, sunucuda):** aracı e-posta, rol ve gerekiyorsa personel numarasıyla çalıştırır
  → şifreyi iki kez girer (ekranda görünmez) → "hesap oluşturuldu: <e-posta> (<rol>)" iletisini
  görür.
- **States:**
  - *Başarı:* e-posta ve rol yazılır, çıkış kodu 0.
  - *Geçersiz girdi:* R-7'deki her durum için ayrı Türkçe ileti, çıkış kodu ≠ 0, hesap yok.
  - *Veritabanı açılamıyor / bellek modu:* açıklayan ileti, çıkış kodu ≠ 0.
  - *Web ekranları:* değişmez.
- **Design reference:** none — the flow above is the design.
- **Accessibility:** komut satırı; iletiler düz metin, renk ya da simgeye dayanmaz.

## Constraints & out of scope
- **Kısıtlar:** Yeni çalışma zamanı bağımlılığı yok (Werkzeug şifre özeti, standart kütüphane;
  ADR-0002). SQL yalnız `storage` içinde (mimari kural 4). Tek sunucu varsayımı (ADR-0001).
- **Kapsam dışı:** giriş / çıkış ekranı, sayfaların girişe kapatılması, kilit ve oturum süresi
  (spec 0019); rol bazlı yetki; hesap listeleme, pasifleştirme, silme ve yönetim ekranı; şifre
  değiştirme ve sıfırlama; e-postaya doğrulama iletisi göndermek.
- **Bilinen sınır (G-1):** üretim veritabanı boş başlar ve personel ekleme ekranı henüz yoktur
  (0017 K-1); bu yüzden canlıda ilk aşamada yalnız IK hesabı açılabilir. Personel ekleme 0019'dan
  sonra ayrı iştir; o zamana kadar giriş yapan herkes her şeyi gördüğünden personel hesapları
  gerekmez.
- **Split:** S-1 ile önerildi ve onaylandı: 0018 hesaplar + araç (bu spec), 0019 giriş / çıkış.

## Hasım okur taraması (onaylı)
- **G-1 Üretimde personel yok:** kabul; Constraints'te "Bilinen sınır".
- **G-2 Personel başına hesap:** en fazla bir; R-1, AC-6.
- **G-3 Rol yazımı:** `Personel` / `Yonetici` / `IK`, harf büyüklüğüne duyarsız; R-1, AC-6.
- **G-4 Şifre argümanı:** gerekçe R-2'de; testler girdiden verir.
- **G-5 Şema geçişi:** kendiliğinden, tek işlem, veri kaybı yok; R-10, AC-8.
- **G-6 E-posta biçimi:** tek `@`, iki yan dolu, boşluk yok; R-5, AC-5.

Spec onayı: İbrahim Gürhan, 2026-11-05 (S-1…S-7 ve G-1…G-6 önerildiği gibi).

## Acceptance criteria
- [ ] AC-1 — Araç geçerli girdiyle bir IK hesabı (personel bağlantısız) ve bir Personel hesabı
  (var olan personele bağlı) açar; ikisi de yeniden başlatmadan sonra aynı e-posta, rol, personel,
  aktif durum, sıfır sayaç ve kilitsiz olarak okunur.
- [ ] AC-2 — Şifre ekranda görünmeden ve iki kez sorulur; eşleşmeyen iki girişte "şifreler
  eşleşmiyor" anlamında ileti, çıkış ≠ 0, hesap yok. Araç şifreyi argüman ya da ortam değişkeni
  olarak kabul etmez.
- [ ] AC-3 — 11 karakterlik şifre reddedilir (ileti en az 12 karakteri söyler, hesap yok); tam 12
  karakterlik, yalnız küçük harfli şifre kabul edilir; baştaki / sondaki boşluk şifrenin parçası
  sayılır.
- [ ] AC-4 — Saklanan veride, araç çıktısında ve log'da şifrenin açık metni geçmez; saklanan özet
  doğru şifreyle doğrulanır, yanlış şifreyle doğrulanmaz; aynı şifreli iki hesabın özetleri
  farklıdır.
- [ ] AC-5 — `"  Ali.Veli@Firma.com "` `ali.veli@firma.com` olarak saklanır; ardından
  `ali.veli@FIRMA.com` ile ikinci hesap reddedilir (hesap sayısı değişmez). `@` içermeyen, iki
  `@` içeren, bir yanı boş ya da içinde boşluk olan e-posta reddedilir.
- [ ] AC-6 — Bilinmeyen rol; personel bağlantısı olmayan Personel / Yönetici; olmayan personel
  numarası (her rolde); zaten bir hesaba bağlı personel → her biri ayrı Türkçe ileti, çıkış ≠ 0,
  hesap yok. `ik`, `YONETICI` gibi yazımlar kabul edilir ve `IK`, `Yonetici` olarak saklanır.
- [ ] AC-7 — Başarıda çıktı e-postayı ve rolü söyler, çıkış 0; log'da tek bir INFO (e-posta, rol),
  şifre ya da özet yok. Bellek modunda ve açılamayan veritabanında araç açıklayan iletiyle ≠ 0
  biter.
- [ ] AC-8 — Hesap kayıtları için sözleşme testleri bellek ve SQLite deposunda geçer; spec 0017
  şemasıyla oluşturulmuş, personel ve talep içeren bir veritabanı açıldığında kayıtlar aynen
  korunur, şema sürümü yükselir ve hesap açılabilir; geçiş yarıda kesildiğinde (zorla hata)
  veritabanı eski sürüm ve verisiyle kalır.
- [ ] AC-9 — Kodda, yapılandırmada ve demo verisinde varsayılan hesap ya da şifre yok; `SEED_DEMO_DATA=1`
  hesap oluşturmaz. Uygulamanın ekranları değişmez; mevcut testler değişmeden geçer.
- [ ] AC-10 — Belgeler: aracın kullanımı (ilk IK hesabı), `docs/architecture.md`,
  `docs/security.md`.

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
