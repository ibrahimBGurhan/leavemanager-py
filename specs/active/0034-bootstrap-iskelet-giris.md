# Spec 0034 — bootstrap-iskelet-giris

- Status: Approved
- Mode: lite
- Plan: `specs/plans/0034-plan.md`

## Intent
İK kullanıcıları ve personel ekranları sade, tutarsız ve telefonda kullanışsız buluyor.
ADR-0003'ün ikinci adımı ekranlara projeye konmuş Bootstrap 5.3 ile tutarlı ve mobilde de
kullanılabilir bir görünüm vermek; ilk adım (HTML'in şablonlara taşınması) 0032 ve 0033 ile bitti.
İş iki spec'e bölündü (clarify, İbrahim Gürhan, 2026-11-16): **bu spec** Bootstrap dosyalarını
projeye ekler ve her ekranın ortak çerçevesini (sayfa iskeleti, menü, çıkış) ile giriş ekranını
yeni görünüme taşır; **0035** Ana Sayfa, Talepler, Yeni Talep ve Yeni Personel ekranlarının
gövdesini taşır. Başarı: bu iki yüzey masaüstünde ve 360 px genişlikte telefonda okunur ve
kullanılır, iletiler tek bir görsel dille gösterilir, JavaScript kapalıyken de her şey çalışır.
Bilerek yapılmayanlar: akış, yetki, ileti metinleri, URL'ler değişmez; sayfa yenilemeden
etkileşim, marka teması ve Sass derlemesi yok.

### Gözlem (ANALYZE, 2026-11-16, HEAD `5ea2fb9`)
- `web/templates/base.html`: satır içi `<style>` (Arial, tablo kenarlıkları, `.kutu`); menü tek bir
  `<p>` içinde `|` ile ayrılmış bağlantılar, e-posta ve `form="cikis-formu"` ile sayfa sonundaki
  formu gönderen "Çıkış" düğmesi. `web/templates/login.html`: kendi `<html>` iskeleti, satır içi
  `<style>`, hata iletisi `style='color:red'`, etiketli iki alan ve "Giriş Yap" düğmesi.
- `web/static/` yok; `app.py` yalnız `template_folder` ayarlıyor. JavaScript hiç yok.
- İşaretlemeye harfiyen bakan assert'ler (bu spec'in yüzeyinde): `tests/test_login.py:149-150`
  (çıkış düğmesi ve formu), `:190`, `:332`, `:347-352` (giriş ekranı başlığı, düğme, etiket,
  `autocomplete`); `tests/test_add_employee.py:199` (menüdeki "Yeni Personel" bağlantısı);
  `tests/test_staff_screens.py:46-48` (çıkış formu sayfa formu sayılmaz). Diğer ekranların
  assert'leri 0035'e kalır.

## Requirements
- R-1 **Bootstrap projede:** Bootstrap 5.3'ün küçültülmüş CSS'i ve JS paketi uygulamanın kendi
  sunucusundan verilir; sayfalar başka bir sunucudan dosya, yazı tipi ya da betik istemez
  (ADR-0003 ilke 2; iç ağ, KVKK). Tam sürüm ve dosyaların SHA-256 özeti planda sabitlenir ve repoda
  bir test bu özetleri doğrular (dosya kazara ya da sessizce değişemez).
- R-2 **Ortak çerçeve:** Giriş yapmış her ekranın üstünde bir gezinme çubuğu vardır: uygulama adı,
  "Ana Sayfa", "Talepler", "Yeni Talep", yalnız personel ekleyebilen hesapta "Yeni Personel",
  giriş yapan hesabın e-postası ve "Çıkış" düğmesi. Bağlantıların hedefleri, sırası, görünürlük
  kuralı ve çıkışın davranışı (POST, CSRF, sonra giriş ekranı) bugünküyle aynıdır. Bulunulan
  ekranın bağlantısı işaretlenir.
- R-3 **Mobil:** Dar ekranda menü bir aç/kapa düğmesine dönüşür. JavaScript kapalıyken de bütün
  menü bağlantıları ve "Çıkış" erişilebilir kalır (ADR-0003 ilke 4).
- R-4 **Giriş ekranı:** Ortalanmış tek bir form: başlık "Giriş", etiketli "E-posta" ve "Şifre"
  alanları (tarayıcı otomatik doldurması bugünkü gibi), "Giriş Yap" düğmesi ve kilit notu. Menü
  yoktur. İleti durumları aynı metinlerle gösterilir: hatalı giriş ve CSRF hatası **hata**, oturum
  süresi doldu ve çıkış yapıldı **bilgi** olarak; hatalı girişte e-posta geri basılır, şifre basılmaz.
- R-5 **İleti dili:** İletiler renkten bağımsız da ayırt edilir: hata iletisi ekran okuyucuya
  hemen duyurulur, bilgi iletisi duyurulmaz ama okunur; ikisi de görünür bir kutu içindedir.
- R-6 **CSP'ye hazırlık:** Bu spec'in dokunduğu şablonlarda (`base.html`, `login.html`) satır içi
  `<style>`, `style=` özniteliği, satır içi `<script>` ve `on…=` olay öznitelikleri yoktur;
  özelleştirme `web/static/app.css`'te, Bootstrap'ın CSS değişkenleriyle yapılır (ADR-0003 ilke 3).
- R-7 **Davranış aynı:** Rotalar, durum kodları, yönlendirmeler, ileti metinleri, log satırları,
  CSRF ve yetki davranışı değişmez. Diğer ekranların gövdesi (0035'e kadar) içerik olarak aynen
  görünür.
- R-8 **Testler davranışa bakar:** İşaretlemeye harfiyen bakan ve bu işte kırılan her assert, aynı
  davranışı işaretlemeden bağımsız soran bir assert'e çevrilir; her değişiklik planda eski satır →
  yeni satır olarak listelenir, review'da "zayıflatma mı" ayrıca sorulur (AGENTS.md kural 5).

## User experience
- **Flow:** (1) Kullanıcı `/giris`'i açar → ortalanmış giriş formu. (2) Hatalı giriş → aynı form,
  hata iletisi, e-posta dolu. (3) Doğru giriş → Ana Sayfa, üstte gezinme çubuğu. (4) Menüden
  ekranlar arasında geçer; bulunduğu ekran işaretli. (5) "Çıkış" → giriş ekranı, "Çıkış yapıldı"
  bilgi iletisi. Telefonda (3)–(5) aç/kapa menü düğmesiyle.
- **States — giriş:** boş form; hatalı giriş (hata); CSRF hatası (hata); oturum süresi doldu (bilgi);
  çıkış yapıldı (bilgi); bilinmeyen `?durum=` (ileti yok).
- **States — çerçeve:** İK (Yeni Personel bağlantısı var); Yönetici ve Personel (yok); geniş ekran
  (menü açık); dar ekran (menü kapalı, düğmeyle açılır); JavaScript kapalı (bağlantılar erişilebilir).
- **Design reference:** none — tasarım dosyası yok (clarify 2); Bootstrap 5.3'ün varsayılan
  bileşenleri (navbar, form, alert, button) kullanılır, kanıt önce/sonra ekran görüntüleridir.
- **Accessibility:** Klavyeyle sıra: menü bağlantıları → Çıkış → ekran içeriği; giriş ekranında
  E-posta → Şifre → Giriş Yap, Enter formu gönderir. Her alanın görünür etiketi var. Menü düğmesinin
  erişilebilir bir adı var ve açık/kapalı durumunu bildirir. Bulunulan menü öğesi ekran okuyucuya da
  bildirilir. Metin kontrastı Bootstrap varsayılanlarının altına düşmez.

## Constraints & out of scope
- **Yeni bağımlılık:** Bootstrap 5.3 (MIT). Spec onayı bu bağımlılığın onayıdır
  (`docs/security.md`, Dependencies); tam sürüm planda önerilir, dosyalar BUILD'de resmi
  dağıtımdan indirilir ve SHA-256 yayımlanan değerle karşılaştırılır — indirme anında insandan
  ayrıca onay alınır (clarify 4).
- **Out of scope:** Ana Sayfa, Talepler, Yeni Talep, Yeni Personel gövdeleri ve onların testleri
  (0035); durum değerlerinin Türkçe yazımı (`Onaylandi` … — domain verisi, ayrı iş; clarify 6);
  güvenlik başlıkları / CSP'nin kendisi (clarify 7); marka teması, Sass, yazı tipi dosyası; yeni
  JavaScript (Bootstrap'ın kendi paketi dışında); `__` (dunder) şablon yasağı (0033 F-1 takip işi).
- **Ara durum:** 0035 bitene kadar diğer ekranların gövdesi eski satır içi stilleriyle yeni çerçevenin
  içinde görünür; kabul edilen geçici durum (clarify 1).
- **Split:** proposed 0034 (bu) → 0035 (ekran gövdeleri); kabul — İbrahim Gürhan, 2026-11-16.

## Acceptance criteria
- [ ] AC-1 — Her ekran (giriş dahil) Bootstrap CSS'ini, JS paketini ve `app.css`'i uygulamanın kendi
  adresinden yükler ve dosyalar 200 ile döner; hiçbir sayfa başka bir sunucuya (`http://`,
  `https://`, `//` ile başlayan) kaynak bağlantısı içermez.
- [ ] AC-2 — Projedeki Bootstrap dosyalarının SHA-256 özeti planda sabitlenen değerlerle aynıdır; bir
  bayt değişirse test kırmızıya düşer.
- [ ] AC-3 — Gezinme çubuğu: İK hesabında Ana Sayfa, Talepler, Yeni Talep, Yeni Personel bağlantıları,
  e-posta ve Çıkış; Yönetici ve Personelde Yeni Personel yok. Hedefler ve sıra bugünküyle aynı;
  bulunulan ekranın bağlantısı "geçerli sayfa" olarak işaretli (ekran okuyucu dahil).
- [ ] AC-4 — Çıkış: menüdeki düğme `/cikis`'e CSRF token'lı bir POST gönderir, oturum kapanır, giriş
  ekranına "Çıkış yapıldı" bilgi iletisiyle dönülür; token'sız istek bugünkü gibi reddedilir.
- [ ] AC-5 — Dar ekran: 360 px genişlikte çerçeve ve giriş ekranı yatay kaydırma gerektirmez; menü
  aç/kapa düğmesine dönüşür, düğmenin erişilebilir adı ve açık/kapalı durumu vardır.
- [ ] AC-6 — JavaScript kapalı: dar ve geniş ekranda bütün menü bağlantıları ve Çıkış görünür ve
  çalışır; giriş formu Enter ile ve düğmeyle gönderilir.
- [ ] AC-7 — Giriş ekranı durumları: boş form; hatalı giriş (401, hata, e-posta geri basılı, şifre boş);
  CSRF hatası (400, hata); süre doldu ve çıkış yapıldı (bilgi); bilinmeyen `?durum=` (ileti yok);
  menü yok. Metinler bugünküyle aynı.
- [ ] AC-8 — İleti dili: hata iletileri hemen duyurulan bir uyarı kutusunda, bilgi iletileri
  duyurulmayan bir bilgi kutusunda; ayrım renge bağlı değildir.
- [ ] AC-9 — `base.html` ve `login.html`'de satır içi `<style>`, `style=`, satır içi `<script>` ve
  `on…=` öznitelikleri yok; bir mimari testi bunu sabitler.
- [ ] AC-10 — Davranış aynı: tüm suite yeşil; işaretlemeye bakan ve değişen her assert planda eski →
  yeni listelenmiş, aynı davranışı soruyor (zayıflatma yok); diğer ekranların görünen metni ve
  durum kodları bugünküyle aynı.

## Decisions (ANALYZE; clarify 1–7 ve G-1…G-6 önerildiği gibi — onay: İbrahim Gürhan, 2026-11-16)
- **C-1 Bölme:** 0034 (dosyalar + çerçeve + giriş) → 0035 (ekran gövdeleri).
- **C-2 Tasarım:** Bootstrap varsayılanları; kanıt önce/sonra ekran görüntüleri.
- **C-3 Testler:** kırılan assert davranışa bakan eşdeğere çevrilir, planda listelenir.
- **C-4 Sürüm:** planda en güncel 5.3.x yaması önerilir; BUILD'de resmi dağıtımdan indirilip özet
  doğrulanır, indirme onayı ayrıca.
- **C-5 Erişilebilirlik / mobil:** 360 px, aç/kapa menü, JS kapalıyken erişilebilir, renkten bağımsız
  iletiler, etiketli alanlar.
- **C-6 Metinler:** ekran başlıkları ve sütun adları düzeltilir (0035 yüzeyi; bu spec'in
  şablonlarında Türkçe karakteri eksik metin yok); durum değerleri değişmez.
- **C-7 CSP:** bu işte değil; şablonlar satır içi stil/betik içermez.

## Self-critique (ANALYZE)
- **G-1 JS kapalıyken dar ekran menüsü:** Bootstrap'ın aç/kapa menüsü JS olmadan kapalı kalır
  (bağlantılar gizlenir); AC-6 bunu yasaklıyor. Çözüm planın işi (ör. JS yokken menüyü açık
  gösteren, satır içi stil gerektirmeyen bir yöntem). *Öneri:* plan bunu Risk olarak ele alsın ve
  VERIFY'da JS kapalı tarayıcıyla ekran görüntüsü alınsın.
- **G-2 Statik dosya yolu:** `app.py` bugün statik klasör ayarlamıyor; bir ayar satırı gerekecek
  (0032 S-2 "`static_folder` bu işte değişmez" demişti — bu spec onu açıkça değiştirir). *Öneri:*
  kabul; giriş yapmamış kullanıcı giriş ekranının CSS'ini alabilmeli — statik dosyalar oturum
  kapısından muaf olmalı, ama yalnız onlar.
- **G-3 Kapı ve statik dosyalar:** Statik yolun oturumsuz açık olması yeni bir açık uç demek;
  yalnız `web/static/` altındaki dosyaları vermeli. *Öneri:* AC-1'in testine "oturumsuz statik
  dosya 200, oturumsuz ekran yine girişe yönlenir" eklensin.
- **G-4 "Geçerli sayfa" işareti:** Hata yollarında (ör. `/requests/9/approve` 403 ekranı) hangi
  bağlantının işaretleneceği belirsiz. *Öneri:* Talepler ekranını çizen her yol "Talepler"i,
  `/new` yolları "Yeni Talep"i, `/personel/yeni` yolları "Yeni Personel"i, `/` "Ana Sayfa"yı işaretler.
- **G-5 Test kanıtı:** AC-5, AC-6 (görsel/tarayıcı davranışı) birim testle tam kanıtlanamaz.
  *Öneri:* VERIFY'da ekran görüntüleri (360 px ve geniş; JS açık ve kapalı) PR'a eklenir; test
  tarafı yalnız işaretlemenin gerekli parçalarını (düğmenin adı, `noscript` yolu vb.) sınar.
- **G-6 Boyut:** 10 kriter — sınırda ama tek yetenek (ortak çerçeve); bölmeye gerek yok.

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
