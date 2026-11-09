# Spec 0020 — rol-bazli-yetki

- Status: Shipped
- Mode: lite
- Plan: `specs/plans/0020-plan.md`
- Source: ADR-0002 (`docs/decisions/0002-kimlik-dogrulama-uygulama-ici-sifre.md`) Bağlam ve
  "ardından roller ve yetki"; spec 0019 Constraints "rol bazlı yetki (spec 0020+)"; `docs/domain.md`
  BR-10, OD-7; `docs/security.md` AuthN / AuthZ "Bugün yetki yok"; ANALYZE kararları S-1…S-7 ve
  self-critique G-1…G-7 (İbrahim Gürhan, 2026-11-09)
- Design: — (none — the flow below is the design)

## Intent
İK, yöneticiler ve personel uygulamaya kendi hesaplarıyla giriyor (spec 0019), ama giriş yapan
herkes hâlâ her şeyi görüyor ve yapabiliyor: bir personel tüm şirketin izin bakiyesini görür,
başkası adına talep açar, talepleri onaylayıp reddeder. Bu iş, her hesabın ne görüp ne
yapabileceğini rolüne göre sınırlar: İK bugünkü gibi her şeyi yapar; Personel yalnız kendi
bakiyesini ve kendi taleplerini görür, yalnız kendi adına talep açar, hiçbir talebi
sonuçlandıramaz. Yönetici bu sürümde Personel gibi davranır (S-1). Başarı: Personel hesabıyla
başkasına ait hiçbir bakiye ya da talep görünmez; yetkisiz bir işlem, adres elle yazılsa bile
hiçbir kaydı değiştirmez; İK için hiçbir şey değişmez. Bilinçli olarak yapılmayanlar: Yönetici'nin
birim görünümü ve onayı (spec 0021), hesap ve personel yönetim ekranları, şifre değiştirme,
personelin talebini geri çekmesi.

## Requirements
- **R-1 Roller ve görünürlük (S-1):** Bir hesabın gördüğü ve üzerinde işlem yapabildiği veri
  rolüne göre belirlenir:
  - **IK:** tüm personel ve tüm talepler (bugünkü gibi); personel kaydına bağlı olsun ya da
    olmasın aynıdır.
  - **Personel** ve **Yonetici:** yalnız hesabın bağlı olduğu personel kaydı ("kendi") ve o
    personelin talepleri. Başka personelin adı, birimi, bakiyesi, talepleri, tarihleri ve
    nedenleri hiçbir ekranda ve hiçbir iletide görünmez.
  Kural her istekte hesabın güncel rolü ve bağlantısıyla uygulanır (spec 0019 R-8'deki pasif
  hesap kuralıyla aynı yol; ayrı kriteri yok, G-4).
- **R-2 Ana Sayfa (S-3, G-5):** Personel için üç kutu (Bekleyen, Onaylanan, Reddedilen) bugünkü
  gibi talep sayısıdır (gün değil) ve yalnız kendi talepleri sayılır; "Personel Bakiyeleri" tablosunda yalnız kendi satırı vardır (Hak,
  Kullanılan, Kalan, Bekleyen bugünkü hesapla, BR-1…BR-5). Ekranın düzeni değişmez.
- **R-3 Talepler (S-6):** Personel yalnız kendi taleplerini görür. Hiçbir satırda Onayla /
  Reddet düğmesi yoktur; durum yalnız metin olarak gösterilir. Talepler ekranındaki hiçbir ileti
  başka personelin talebi hakkında bilgi vermez (var olup olmadığı ya da durumu dahil).
- **R-4 Yeni Talep (S-4):** Personel formunda personel seçimi yoktur; kendi adı sabit metin
  olarak görünür ve talep her zaman kendi adına açılır. Tarih, iş günü ve bakiye kuralları ile
  iletileri bugünkü gibidir (BR-6…BR-9, ihlal sırası aynı); hata sonrası form yine kendi adıyla
  gösterilir.
- **R-5 Sonuçlandırma (BR-10, S-2):** Talepleri yalnız İK onaylar ya da reddeder. İK kendi
  talebini de sonuçlandırabilir (bugünkü gibi, görev ayrılığı kapsam dışı).
- **R-6 Yetkisiz işlem (S-5):** Personel ya da Yönetici hesabıyla bir talebi onaylama / reddetme
  ve başka bir personel adına talep açma denemesi hiçbir kaydı değiştirmez; kullanıcı "Bu işlem
  için yetkiniz yok." iletisini 403 durum koduyla görür. Yetki, talebin ya da personelin var olup
  olmadığından ve talebin durumundan önce denetlenir: olmayan bir talep, sonuçlanmış bir talep ya
  da olmayan bir personel için de aynı ileti ve durum kodu verilir. İleti, ilgili ekranın (Talepler
  ya da Yeni Talep) R-1'e göre süzülmüş haliyle gösterilir (G-3). Başkası adına talep denemesinde
  form kendi adıyla gösterilir; girilen tarih ve neden geri basılır (spec 0015 gibi; G-2). Her
  deneme log'a WARNING olarak yazılır: hesabın e-postası, denenen işlem (onay, red ya da başkası
  adına talep) ve hedef talep ya da personel numarası; talebin nedeni ve tarihleri yazılmaz (G-6).
- **R-7 Personel kaydına bağlı olmayan hesap (S-7):** Personel ya da Yonetici hesabının bağlı
  olduğu personel kaydı yoksa hesap giriş yapabilir; Ana Sayfa'daki sayılar 0'dır ve bakiye
  tablosunda satır yoktur, Talepler listesi boştur. Yeni Talep ekranı form göstermez, yalnız
  "Hesabınız bir personel kaydına bağlı değil; talep açmak için İK ile görüşün." iletisini
  gösterir (200; G-1). Yine de gelen bir talep gönderimi R-6'daki gibi reddedilir.
- **R-8 Hata durumları da süzülür:** Form süresi dolmuş / token hatası (spec 0011) ve diğer hata
  durumlarında gösterilen ekranlar da R-1'e göre süzülür; Personel hiçbir hata yolunda başkasının
  verisini görmez.
- **R-9 Değişmeyenler:** İK hesabı Ana Sayfa, Talepler ve Yeni Talep ekranlarını, iletilerini ve
  davranışını bugünkü gibi görür. Giriş, çıkış, oturum ve kilit davranışı (spec 0019) değişmez.
  Menü her rolde aynıdır.
- **R-10 Belgeler:** `docs/security.md` AuthN / AuthZ ("Bugün yetki yok" yerine bugünkü durum),
  `docs/domain.md` BR-10 ve OD-7 ("yetki kısıtı henüz yok" yerine kural), `README.md` (rollerin
  ne görüp ne yapabildiği) güncellenir.

## User experience
- **Flow (Personel):** giriş → Ana Sayfa (kendi sayıları, kendi bakiye satırı) → Talepler (kendi
  talepleri, düğmesiz) → Yeni Talep (adı sabit; tarih ve neden girer) → Kaydet → Talepler'de yeni
  talebi `Beklemede` görür.
- **Flow (İK):** bugünkü gibi; değişiklik yok.
- **States — Personel:**
  - *Ana Sayfa:* kendi sayıları ve tek satırlık bakiye tablosu.
  - *Ana Sayfa, bağlı personel kaydı yok:* sayılar 0, tablo başlıkları var, satır yok.
  - *Talepler, talebi var:* yalnız kendi talepleri, durum metin, düğme yok.
  - *Talepler, talebi yok:* tablo başlıkları var, satır yok.
  - *Yeni Talep:* personel alanında kendi adı sabit; tarih ve neden alanları; "Kaydet".
  - *Yeni Talep, kural hatası:* bugünkü iletiler (bakiye, tarih, iş günü, bozuk girdi); ad sabit.
  - *Yeni Talep, bağlı personel kaydı yok:* form yok; "Hesabınız bir personel kaydına bağlı
    değil; talep açmak için İK ile görüşün." (G-1)
  - *Yetkisiz işlem:* "Bu işlem için yetkiniz yok." (403), süzülmüş ekranla.
  - *Form süresi dolmuş:* spec 0011 iletisi, süzülmüş ekranla.
- **States — İK:** bugünkü durumlar aynen.
- **Design reference:** none — the flow above is the design.
- **Accessibility:** sabit ad bir form alanı değil düz metindir, "Personel" etiketiyle okunur;
  iletiler düz metin, yalnız renge dayanmaz; klavye yolu bugünkü gibi (tarih → neden → Kaydet).

## Constraints & out of scope
- **Kısıtlar:** Yeni çalışma zamanı bağımlılığı yok. `docs/security.md` AuthZ kuralı geçerli:
  yetki sunucu tarafında denetlenir; bir düğmeyi ya da alanı gizlemek yetki sayılmaz. Mimari
  kurallar geçerli (`docs/architecture.md`). Roller spec 0018'deki yazımla: `Personel`,
  `Yonetici`, `IK`.
- **Mevcut testler:** bugünkü ekran ve kural testleri İK hesabıyla çalışır ve değişmeden geçer;
  bir testin değişmesi gerekirse planda R-07 onayına gelir.
- **Kapsam dışı:** Yönetici'nin birim görünümü ve onay yetkisi (spec 0021; bu sürümde Personel
  gibi, S-1); İK'nın kendi talebini onaylamasına kısıt / görev ayrılığı (S-2, ayrı karar); talebi
  geri çekme ya da iptal; hesap / personel yönetim ekranları; rol değiştirme aracı; şifre
  değiştirme ve sıfırlama; menüde rol gösterimi.
- **Split:** Yönetici ayrı spec'e alındı (S-1, İbrahim Gürhan, 2026-11-09); kalan tek yetenek
  (rol bazlı görünürlük ve işlem yetkisi).

## Acceptance criteria
<!-- Test verisi: iki personel A ve B; ikisinin de Beklemede, Onaylandi ve Reddedildi talepleri var;
     A'ya bağlı bir Personel hesabı, bir Yonetici hesabı, bir IK hesabı. -->
- [x] AC-1 — İK hesabı (personel bağlantılı ve bağlantısız) Ana Sayfa'da tüm personelin sayılarını
  ve satırlarını, Talepler'de tüm talepleri ve bekleyenlerde Onayla / Reddet düğmelerini, Yeni
  Talep'te personel seçimini bugünkü gibi görür; bekleyen bir talebi (kendi talebi dahil) onaylar
  ve reddeder.
- [x] AC-2 — A'nın Personel hesabı Ana Sayfa'da yalnız A'nın taleplerinin sayılarını ve yalnız
  A'nın bakiye satırını (doğru Hak, Kullanılan, Kalan, Bekleyen) görür; sayfada B'nin adı ve
  birimi yoktur.
- [x] AC-3 — A'nın Personel hesabı Talepler'de yalnız A'nın taleplerini görür, hiçbir satırda
  Onayla / Reddet düğmesi yoktur, durumlar metin olarak görünür; B'nin adı, tarihleri ve nedenleri
  sayfada yoktur.
- [x] AC-4 — A'nın Personel hesabı Yeni Talep'te personel seçimi görmez, A'nın adını görür; geçerli
  gönderim A adına `Beklemede` bir talep oluşturur. Bakiye, tarih aralığı, iş günü ve bozuk girdi
  hataları bugünkü iletileri verir ve form A'nın adıyla yeniden gösterilir.
- [x] AC-5 — A'nın Personel hesabıyla B adına ve olmayan bir personel adına talep gönderimi 403 ve
  "Bu işlem için yetkiniz yok." alır; hiçbir talep oluşmaz; form A'nın adıyla, girilen tarih ve
  neden geri basılarak gösterilir (G-2).
- [x] AC-6 — A'nın Personel hesabıyla onay ve red istekleri — A'nın bekleyen talebi, B'nin
  bekleyen talebi, sonuçlanmış bir talep ve olmayan bir talep için — 403 ve aynı iletiyi alır;
  hiçbir talep değişmez; yanıtta B'ye ait veri yoktur; her deneme için log'da e-posta, işlem ve
  hedef talep numarasıyla bir WARNING vardır, talebin nedeni ve tarihleri log'da yoktur (G-6).
- [x] AC-7 — Yonetici hesabı (A'ya bağlı), Personel ile aynı kuralı temsilen gösterir (G-7): Ana
  Sayfa'da yalnız A'nın satırı; Talepler'de düğme yok; bir onay isteği ve B adına bir talep
  gönderimi 403 alır ve hiçbir kayıt değişmez.
- [x] AC-8 — Bağlı personel kaydı olmayan bir Personel hesabı giriş yapar; Ana Sayfa'da sayılar 0
  ve bakiye satırı yok, Talepler boş; Yeni Talep form göstermez ve G-1 iletisini 200 ile verir;
  talep gönderimi 403 alır ve hiçbir talep oluşmaz.
- [x] AC-9 — Personel hesabıyla token'sız bir form gönderimi (spec 0011) ve Talepler ekranının
  başarı iletisi parametreleriyle B'nin bir talebini gösteren adres, B'ye ait hiçbir veri ya da
  talep bilgisi göstermez.
- [x] AC-10 — Mevcut testler değişmeden geçer (ya da planda onaylı satırlarla); `docs/security.md`,
  `docs/domain.md` (BR-10, OD-7) ve `README.md` bugünkü durumu anlatır.

## Definition of Done
- [x] Every acceptance criterion mapped to proof (test or reproducible observation)
- [x] `scripts/check` green
- [x] Independent review done; real findings fixed, noise rejected with written rationale
- [x] Docs / ADRs updated if behavior or architecture changed
- [x] Spec moved to `specs/done/` (it becomes immutable there)

## Scorecard (fill at ship — honest numbers make the process improvable)
| Metric | Value |
|---|---|
| Spec revisions | 0 |
| Fix rounds | 1 (fix-1: review round 1 F-1 kural tek yerde — `authorize_*`, F-2 belge, F-3 plan haritası, F-4 log assert'leri) |
| Review findings: real / noise | 4 / 1 (round 1: F-1…F-4 gerçek, hepsi düşük; round 2: F2-1 noise, seçenek b sonraki dokunuşa). VERIFY: 10/10 Pass, 15 mutant kırmızı; G-1, G-3, G-4 takip işi, G-2 ship'te kapandı, G-5 ekran görüntüleri PR'da. BUILD'de 3 R-07 (onaylı) |
| Regressions introduced | 0 |
| Bugs escaped to production | 0 (henüz yayında değil) |
