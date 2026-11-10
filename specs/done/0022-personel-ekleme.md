# Spec 0022 — personel-ekleme

- Status: Shipped
- Mode: lite
- Plan: `specs/plans/0022-plan.md`
- Source: spec 0017 K-1 ("personel ekleme ekranı … ayrı spec") ve spec 0018 G-1 ("Bilinen sınır:
  üretim veritabanı boş başlar ve personel ekleme ekranı henüz yoktur"); ANALYZE kararları
  S-1…S-7 ve self-critique G-1…G-7 (İbrahim Gürhan, 2026-11-10)
- Supersedes: 0020/R-9 "Menü her rolde aynıdır" (menüde "Yeni Personel" yalnız İK'ya görünür)
- Design: — (none — the flow below is the design)

## Intent
Uygulama canlıda boş bir veritabanıyla başlıyor ve bugün personel kaydı açmanın hiçbir yolu yok;
bu yüzden İK izin takibine başlayamıyor, Personel ve Yönetici hesapları da açılamıyor (hesap bir
personel kaydına bağlanır). Bu iş, İK'ya uygulama içinden yeni personel kaydı açma imkânı verir:
ad, birim ve işe giriş tarihi. Başarı: İK birkaç alanla bir personel ekler; eklenen personel hemen
Ana Sayfa'da ve Yeni Talep'te görünür; İK o personele hesap açmak için gereken numarayı görür;
İK dışında kimse personel ekleyemez. Bilinçli olarak yapılmayanlar: personeli düzenleme, silme ya
da işten ayrılma kaydı, toplu içe aktarma, hesap yönetimi ekranı.

## Requirements
- **R-1 Yeni Personel ekranı (S-1):** İK, menüdeki "Yeni Personel" bağlantısından bir form açar:
  Ad, Birim, İşe giriş tarihi ve "Kaydet". Birim alanı serbest metindir; form, kayıtlı
  personelin birimlerini öneri listesi olarak sunar (S-3): her birim bir kez, yazıldığı gibi,
  alfabetik sırayla; boş veritabanında liste boştur (G-4).
- **R-2 Kayıt:** Geçerli gönderimde yeni personel kaydı oluşur. Numarayı sistem sırayla verir
  (kayıtlı en büyük numaradan bir fazla; boş veritabanında 1). Numaralar her zaman tekildir:
  aynı anda gelen iki ekleme ayrı numaralar alır, hiçbiri kaybolmaz (G-5). Gönderimden sonra
  kullanıcı aynı forma, alanlar boş olarak yönlendirilir (sayfa yenilemesi kaydı tekrarlamaz;
  G-3) ve "Personel #<N> eklendi: <ad> (<birim>)." iletisini görür (S-5). Yeni personel hemen Ana
  Sayfa'nın bakiye tablosunda (Hak, Kullanılan, Kalan, Bekleyen bugünkü kurallarla, BR-1…BR-5)
  ve Yeni Talep'in personel listesinde yer alır; hesap aracı (`hesap-ac --personel <N>`) onu
  bulur.
- **R-3 Ad ve birim (S-3):** İkisi de zorunludur; baştaki ve sondaki boşluk atılır ve kayıt
  kırpılmış değerle yapılır. Kırpıldıktan sonra boş olan değer eksik sayılır. Ad en fazla 100,
  birim en fazla 50 karakterdir. Birimin harf büyüklüğü değiştirilmez (spec 0021 birimleri tam
  eşleşmeyle karşılaştırır).
- **R-4 İşe giriş tarihi (S-4):** Zorunludur ve geçerli bir tarih olmalıdır. Gelecek tarih kabul
  edilir (henüz başlamamış personel; hak kıdem kuralıyla hesaplanır). 1950-01-01'den önceki tarih
  reddedilir.
- **R-5 Aynı ad (S-5):** Aynı adla (ve birimle) ikinci bir personel eklenebilir; kayıtlar
  numarayla ayrılır.
- **R-6 Hata davranışı:** Geçersiz gönderimde kayıt oluşmaz; kullanıcı formu, neyin yanlış
  olduğunu söyleyen bir iletiyle ve girdiği değerler geri basılmış olarak görür (spec 0015
  kalıbı); durum kodu 400. Birden çok hata varsa tek ileti gösterilir, sıra: ad → birim → tarih
  (G-1). İletiler (G-2): "Ad girin." · "Birim girin." · "Ad en fazla 100 karakter olabilir." ·
  "Birim en fazla 50 karakter olabilir." · "Geçerli bir işe giriş tarihi girin." · "İşe giriş
  tarihi 1950-01-01'den önce olamaz." Ad ve birim metni olduğu gibi saklanır, her ekranda
  kaçışlanarak gösterilir; HTML olarak çalışmaz (G-6).
- **R-7 Yetki (S-2):** Yalnız İK personel ekler. "Yeni Personel" bağlantısı yalnız İK'nın
  menüsünde görünür; diğer menü öğeleri her rolde aynıdır. Personel, Yönetici ya da başka bir
  rolün ekranı açması veya form göndermesi spec 0020 R-6'daki gibi reddedilir: 403, "Bu işlem
  için yetkiniz yok.", hiçbir kayıt oluşmaz, log'a WARNING. Yetki, girdinin doğruluğundan önce
  denetlenir. Yetki yalnız role bakar: İK hesabının bir personel kaydına bağlı olması gerekmez;
  Yönetici, birimi ne olursa olsun ekleyemez (G-7).
- **R-8 Log (S-7):** Her ekleme log'a INFO olarak tek satır yazılır:
  `personel eklendi: #<N> (<birim>), ekleyen: <e-posta> (<rol>)`. Personelin adı ve işe giriş
  tarihi yazılmaz (KVKK).
- **R-9 Form koruması:** Form CSRF token taşır; token'sız ya da bozuk token'lı gönderim spec 0011
  iletisini alır ve kayıt oluşmaz.
- **R-10 Değişmeyenler:** Ana Sayfa, Talepler, Yeni Talep, giriş, rol kapsamları (spec 0019, 0020,
  0021) ve hesap aracı bugünkü gibidir; yalnız yeni eklenen personel listelerde görünür.
- **R-11 Belgeler:** `README.md` (personel ekleme, ilk kurulum sırası: İK hesabı → personel →
  hesaplar), `docs/security.md` (roller), `docs/domain.md` (personel kaydının kuralları) güncellenir.

## User experience
- **Flow (İK):** menü → "Yeni Personel" → Ad, Birim (öneri listesinden seçer ya da yazar), İşe
  giriş tarihi → "Kaydet" → "Personel #N eklendi: <ad> (<birim>)." → (isterse) bir sonraki
  personeli ekler ya da Ana Sayfa'da yeni satırı görür.
- **States — Yeni Personel ekranı (İK):**
  - *İlk açılış:* boş alanlar; Birim alanında kayıtlı birimler öneri olarak; "Kaydet".
  - *Boş veritabanı:* aynı form; öneri listesi boş.
  - *Başarı:* "Personel #N eklendi: <ad> (<birim>)." iletisi.
  - *Hata:* ilgili ileti (kırmızı, düz metin), girilen değerler formda; 400.
  - *Form süresi dolmuş:* spec 0011 iletisi.
- **States — diğer roller:** menüde "Yeni Personel" yok; adres elle açılırsa "Bu işlem için
  yetkiniz yok." (403).
- **Design reference:** none — the flow above is the design.
- **Accessibility:** her alanın görünür ve alana bağlı bir etiketi var; tarih alanı Yeni Talep'teki
  gibi; yalnız klavyeyle doldurulup gönderilir; iletiler düz metin, yalnız renge dayanmaz.

## Constraints & out of scope
- **Kısıtlar:** Yeni çalışma zamanı bağımlılığı yok. Personel kuralları domain'de; yetki spec
  0020'deki tek yerde (`docs/security.md` AuthZ); web depoya doğrudan erişmez (mimari kurallar).
  Veritabanı şeması değişmez (personel tablosu zaten var).
- **Mevcut testler:** değişmeden geçer; menünün her rolde aynı olduğunu sabitleyen bir test varsa
  (Supersedes 0020/R-9) planda R-07 onayına gelir.
- **Kapsam dışı (S-6):** personeli düzenleme, silme, işten ayrılma / pasife alma; toplu içe aktarma
  (CSV vb.); hesap yönetimi ekranı; birim listesinin ayrı yönetimi; personelin numarasını elle
  seçme.

## Acceptance criteria
- [x] AC-1 — İK menüde "Yeni Personel"i görür; form Ad, Birim (kayıtlı birimler öneri listesinde),
  İşe giriş tarihi ve "Kaydet" içerir. Geçerli gönderim, kayıtlı en büyük numaradan bir fazla
  numarayla kayıt oluşturur ve "Personel #N eklendi: <ad> (<birim>)." gösterir; yeni personel Ana
  Sayfa'nın bakiye tablosunda doğru Hak / Kullanılan / Kalan / Bekleyen ile ve Yeni Talep'in
  personel listesinde görünür.
- [x] AC-2 — " Ayşe Yılmaz " ve " IT " olarak girilen değerler "Ayşe Yılmaz" ve "IT" olarak
  kaydedilir; bu personel IT Yöneticisinin (spec 0021) ekranında görünür.
- [x] AC-3 — Boş ad, yalnız boşluk ad, boş birim, 101 karakterlik ad, 51 karakterlik birim, eksik
  tarih, bozuk tarih ve 1949-12-31 tarihi 400 ve G-2'deki ilgili iletiyi alır; birden çok hatada
  ad → birim → tarih sırasındaki ilk ileti görünür; kayıt oluşmaz; girilen değerler geri basılır.
  100 karakterlik ad, 50 karakterlik birim ve 1950-01-01 kabul edilir. `<script>` içeren bir ad
  kaydedilir ve Ana Sayfa'da metin olarak görünür, çalışmaz (G-6).
- [x] AC-4 — Gelecek tarihli işe giriş kabul edilir; personel Ana Sayfa'da Hak 0 ile görünür.
- [x] AC-5 — Aynı ad ve birimle ikinci bir personel eklenir; iki ayrı numara alırlar. Aynı anda
  gelen iki ekleme ayrı numaralar alır (G-5). Başarıdan sonra form boş açılır ve sayfa yenilemesi
  ikinci bir kayıt oluşturmaz (G-3); öneri listesi kayıtlı birimleri tekil ve alfabetik gösterir
  (G-4).
- [x] AC-6 — Personel, Yönetici ve personel kaydına bağlı olmayan bir Personel hesabı menüde
  "Yeni Personel"i görmez; personel kaydına bağlı olmayan İK hesabı görür ve ekler (G-7). Bu
  üç hesabın ekranı açması ve form göndermesi 403 ve "Bu işlem için yetkiniz yok." alır; kayıt
  oluşmaz; log'da WARNING vardır. Geçersiz girdili yetkisiz gönderim de 403 alır (yetki önce).
- [x] AC-7 — Her ekleme için log'da `personel eklendi: #<N> (<birim>), ekleyen: <e-posta> (<rol>)`
  biçiminde bir INFO satırı vardır; personelin adı ve işe giriş tarihi log'da yoktur.
- [x] AC-8 — Boş bir veritabanında (demo verisi yok) İK ilk personeli ekler: numarası 1'dir;
  ardından `hesap-ac --rol Personel --personel 1` bu personele hesap açar.
- [x] AC-9 — Token'sız ya da bozuk token'lı gönderim spec 0011 iletisini alır; kayıt oluşmaz.
- [x] AC-10 — Mevcut testler değişmeden geçer (Supersedes 0020/R-9 için planda onaylı satırlar
  dışında); `README.md`, `docs/security.md` ve `docs/domain.md` bugünkü durumu anlatır.

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
| Fix rounds | 1 (fix-1: review round 1 F-1 — birimdeki kontrol karakterleri log satırında kaçışlanır) |
| Review findings: real / noise | 1 / 1 (round 1: F-1 düşük real, F-2 bilgi noise — CSRF yetkiden önce, gerekçe planda). VERIFY: 10/10 Pass, 34/36 mutant kırmızı; G-1, G-2 bilinen sınır (kabul), G-3, G-4 aksiyon yok, G-5 ekran görüntüleri PR'da |
| Regressions introduced | 0 |
| Bugs escaped to production | 0 (henüz yayında değil) |
