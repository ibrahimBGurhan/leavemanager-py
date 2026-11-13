# ADR 0003 — Ön yüz: Jinja şablonları, projeye konmuş Bootstrap 5.3, build adımı yok, JS yalnız iyileştirme

- Status: Accepted
- Date: 2026-11-13

## Context
LeaveManager'ın ekranları bugün Python kodunun içinde string olarak üretiliyor: sayfa iskeleti
`web/routes.py` içindeki `PAGE` sabiti, giriş ekranı `web/auth.py` içindeki `LOGIN_PAGE`; gövde
`%` ile birleştirilip `{{ body|safe }}` ile basılıyor. Stil sayfaya gömülü birkaç satır CSS ve
satır içi `style=` öznitelikleri; JavaScript hiç yok, `templates/` ve `static/` klasörü yok.

Bu durum iki sorun yaratıyor:
- **Güvenlik kuralı ihlali:** `docs/security.md` (Input & output) HTML'in yalnız Jinja
  şablonlarında, otomatik kaçış açıkken üretilmesini; kullanıcı verisi içeren HTML'de string
  birleştirme ve `|safe` kullanılmamasını şart koşuyor. Bugünkü kod her değeri elle `escape`
  ederek bu riski taşıyor; tek bir unutulan `escape` stored XSS demek.
- **Görünüm ve kullanılabilirlik:** ekranlar mobilde kullanışsız, tutarsız ve sade; görünümü
  iyileştirmek istendiğinde (sıradaki iş) stil ve HTML Python string'lerine dağılmış durumda.

Kısıtlar ve bağlam:
- İç ağda çalışan bir İK uygulaması; birkaç İK kullanıcısı ve personel. İnternet erişimi garanti
  değil; kişisel veri (KVKK) işleniyor.
- Küçük ekip, Python'dan ibaret araç zinciri; Node/npm yok.
- Her yeni bağımlılık insan onayı ister; lisans MIT/BSD/Apache-2.0 uyumlu, aktif bakımda, sürümü
  sabit olmalı (`docs/security.md`, Dependencies). Bootstrap bir pip paketi değil, ama bu kural
  ona da aynen uygulanır.
- UX ayrıntıları (akış, durumlar, erişilebilirlik) her ekran işinin spec'inde yazılır
  ([ANEW-0008](anew/ANEW-0008-ux-lives-in-the-spec.md)); bu ADR yalnız teknik yaklaşımı belirler.

## Decision
Ön yüz dört ilkeyle kurulur:
1. **Şablonlar:** HTML `web/templates/` altındaki Jinja dosyalarında üretilir — bir `base.html`
   iskeleti ve her ekran için bir şablon; otomatik kaçış açık. Python kodu HTML string'i
   kurmaz, şablona veri verir. Statik dosyalar `web/static/` altındadır.
2. **CSS çatısı: Bootstrap 5.3**, projeye konmuş (vendored) olarak:
   `web/static/vendor/bootstrap-<sürüm>/` altında `bootstrap.min.css` ve
   `bootstrap.bundle.min.js`. CDN kullanılmaz. Tam sürüm ve dosyaların SHA-256 özeti, dosyaları
   ekleyen planda sabitlenir; güncelleme ayrı ve dar bir commit'le yapılır.
3. **Build adımı yok:** Bootstrap'ın hazır `.min` dosyaları olduğu gibi kullanılır; Sass ile tema
   derlenmez. Gereken özelleştirme küçük bir `web/static/app.css` dosyasında, Bootstrap'ın CSS
   değişkenleriyle (`--bs-*`) yapılır.
4. **JavaScript yalnız iyileştirme (progressive enhancement):** her ekran ve form JS kapalıyken de
   çalışır; doğrulama ve yetki her zaman sunucuda kalır. Satır içi `<script>` ve `onclick=` gibi
   olay öznitelikleri kullanılmaz (ileride CSP'ye hazırlık). SPA, htmx ya da başka bir JS
   kütüphanesi eklenmez; Bootstrap'ın JS paketi yalnız kendi bileşenleri (ör. mobilde menünün
   açılıp kapanması) için yüklenir.

Uygulama ayrı spec'lerle yapılır (bu ADR kod içermez): önce davranışı değiştirmeyen şablona
taşıma (refactor), sonra Bootstrap ile görünüm.

## Consequences
Kazandıklarımız:
- `docs/security.md`'deki çıktı kuralı ilk kez uygulanabilir hale gelir: otomatik kaçış varsayılan
  olur, elle `escape` ve `|safe` kaynaklı XSS riski yapısal olarak azalır.
- Görünüm ile kod ayrılır: ekran değişiklikleri şablon ve CSS'te yapılır, `routes.py` küçülür ve
  okunur hale gelir.
- Hazır, erişilebilirlik varsayılanları iyi bileşenler (navbar, tablo, form, rozet, uyarı) ve mobil
  uyum; elle CSS yazma yükü düşer. Bootstrap MIT lisanslı, yaygın ve aktif bakımda; jQuery
  gerektirmez.
- İnternetsiz iç ağda çalışır; dışarıya istek, dolayısıyla kullanıcı izi gitmez (KVKK). Sürüm
  repoda sabittir; CDN kesintisi sayfayı stilsiz bırakamaz.
- Sıkı bir CSP (`default-src 'self'`) eklemek sonradan kolaydır.
- Node/npm araç zinciri eklenmez; kurulum ve CI değişmez.

Ödediklerimiz:
- **Repo büyür:** yaklaşık 300 KB küçültülmüş üçüncü taraf dosyası repoda durur.
- **Güncelleme elle yapılır:** pip-audit Bootstrap'ı görmez; güvenlik duyurularını ve yeni
  sürümleri takip etmek, dosyayı indirip özetini doğrulamak bizim işimiz.
- **Ağırlık:** sayfa başına yaklaşık 230 KB CSS ve 80 KB JS (ilk yüklemeden sonra önbellekte);
  kullandığımız bileşenlerin çok ötesinde kod gelir, çünkü Sass ile ayıklamıyoruz.
- **Tipik "Bootstrap görünümü":** derin marka özelleştirmesi Sass gerektirir; CSS değişkenleriyle
  yapılabilenle sınırlıyız.
- **HTML class'larla dolar:** şablonlar Bootstrap'ın class adlarına bağlanır; çatıyı değiştirmek
  tüm şablonlara dokunmak demektir.
- **Testler etkilenir:** HTML'e (satır içi `color`, `<td>` vb.) bakan testler şablona taşıma ve
  görünüm değişikliğinde güncellenmeli; testler görünüme değil davranışa (metin, durum, bağlantı)
  bakacak şekilde yazılmalı.
- **JS'siz çalışma şartı** bazı etkileşimleri (sayfa yenilemeden onay, anlık filtre) bugünlük
  dışarıda bırakır.

## Alternatives considered
- **Class'sız hafif CSS (Pico.css vb.):** Yaklaşık 10 KB, HTML'e neredeyse hiç class eklemeden en
  hızlı geçiş. Kaybetti çünkü bileşen yelpazesi dar (navbar, rozet, uyarı elle yazılır), topluluğu
  küçük ve özelleştirme ihtiyacı büyüdükçe elle CSS'e geri dönülür.
- **Elle yazılmış CSS:** Bağımlılık yok, tam kontrol. Kaybetti çünkü mobil uyum, form durumları ve
  erişilebilirlik sıfırdan yazılıp bakımı yapılmalı; küçük ekip için maliyeti yüksek.
- **Tailwind CSS:** Esnek, modern. Kaybetti çünkü pratikte bir build adımı (Node/npm, içerik
  taraması) gerektiriyor; Python'dan ibaret projeye yeni bir araç zinciri ve CI adımı ekliyor.
- **Bootstrap'ı CDN'den (SRI ile) yüklemek:** Repo küçük kalır, tarayıcı önbelleği paylaşılır.
  Kaybetti çünkü internet bağımlılığı getirir, her sayfa açılışında üçüncü tarafa istek (ve
  kullanıcı izi) gider, CDN erişilemezse uygulama stilsiz kalır; iç ağ ve KVKK bağlamına uymuyor.
- **Sass ile Bootstrap derlemek:** Yalnız kullanılan bileşenler, marka renkleri. Kaybetti çünkü
  build adımı ve araç zinciri gerektiriyor; bugün marka rehberi yok, CSS değişkenleri yetiyor.
- **htmx / bir JS çatısı (SPA):** Sayfa yenilemeden etkileşim. Kaybetti çünkü bugünkü ekranlar
  form + liste düzeyinde; yeni bağımlılık ve JS'e dayalı davranış, test ve güvenlik yüzeyini
  büyütür. İhtiyaç doğarsa ayrı bir ADR'yle ele alınır.

## Revisit triggers
- Kurumun bir tasarım sistemi ya da marka rehberi çıkar ve Bootstrap'ı özelleştirmek Sass/build
  gerektirir hale gelirse.
- Ekranlarda canlı etkileşim ihtiyacı artarsa (anlık filtreleme, sayfa yenilemeden onay/red) →
  htmx ya da bir JS çatısı ayrı bir ADR'yle değerlendirilir.
- Bootstrap'ın bakımı durursa ya da kapatılmayan bir güvenlik açığı çıkarsa.
- Uygulama internete açılırsa ya da birden çok uygulama ortak bir CDN/varlık sunucusu kullanmaya
  başlarsa (dağıtım şekli yeniden değerlendirilir).
