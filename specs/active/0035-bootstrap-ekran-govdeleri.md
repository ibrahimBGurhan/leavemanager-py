# Spec 0035 — bootstrap-ekran-govdeleri

- Status: In progress
- Mode: lite
- Plan: `specs/plans/0035-plan.md`

## Intent
İK kullanıcıları, yöneticiler ve personel her gün Ana Sayfa, Talepler, Yeni Talep ve Yeni Personel
ekranlarını kullanıyor; bu ekranlar 0034'ün yeni çerçevesi içinde hâlâ eski, sade düzende duruyor
ve telefonda tablolar sayfayı yana taşırıyor. ADR-0003'ün son dilimi bu dört ekranın gövdesini
aynı görsel dile taşır: düzenli tablolar, okunur durum rozetleri, tek tip ileti kutuları ve
etiketli formlar. Başarı: dört ekran masaüstünde ve 360 px telefonda sayfa yana kaymadan okunur
ve kullanılır; onay/red ve form gönderimi JavaScript kapalıyken de çalışır; Türkçe karakteri eksik
başlıklar düzelir. Bilerek yapılmayanlar: akış, yetki, URL'ler ve ileti metinleri değişmez; durum
değerleri (`Onaylandi` …) domain verisi olarak aynı kalır; alan düzeyinde hata gösterimi, sayfa
yenilemeden etkileşim ve marka teması yok. Clarify 1–7 önerildiği gibi kabul (İbrahim Gürhan,
2026-11-16).

### Gözlem (ANALYZE, 2026-11-16, HEAD `7c8c682`)
- `web/templates/_macros.html`: `status_badge` (`<b style='color:…'>`), `message_line`
  (`<p style='color:…'>`) ve onay/red formları (`style='display:inline'`) satır içi stil taşıyor;
  `web/static/app.css`'te 0034'ün ara kuralları (`main table`, `main td, main th`, `.kutu`) duruyor.
- Durum rengi Python'da CSS rengi olarak seçiliyor (`web/routes.py:58` `status_color` → `green`,
  `orange`, `red`, `#999`; "Beklemede" harfe duyarsız, 0012 PB-4). İleti rengi de Python'dan
  (`message_color="green"|"red"`).
- Yeni Talep formunda `<label>` yok ("Personel:", "Baslangic:" … düz metin). Yeni Personel'de
  etiketler var. Yeni Talep başarıda `/requests`'e iletisiz yönlenir.
- İşaretlemeye bağlı assert'ler 14 test dosyasında ~45 satır (satır içi `color`, `<td>`, `<h3>`,
  `value='Onayla'`, `.kutu` …) ve `tests/conftest.py::status_cell_html`.

## Requirements
- R-1 **Ana Sayfa:** Üç sayaç (Bekleyen, Onaylanan, Reddedilen — talep sayısı) yan yana kutular
  olarak, dar ekranda alt alta; altında "Personel Bakiyeleri" tablosu (Ad, Birim, Hak, Kullanılan,
  Kalan, Bekleyen). Satırlar, değerler ve kim neyi görür kuralı bugünküyle aynıdır.
- R-2 **Talepler:** "İzin Talepleri" tablosu (Personel, Başlangıç, Bitiş, Gün, Neden, Durum).
  Satırlar ve görünürlük bugünküyle aynıdır. Onay/red düğmeleri yalnız bugün gösterildiği
  satırlarda (talebi sonuçlandırabilen hesap) görünür.
- R-3 **Yeni Talep:** Her alanın görünür ve alana bağlı bir etiketi vardır (Personel, Başlangıç,
  Bitiş, Neden). İK personeli listeden seçer; Personel ve Yönetici hesabında personel adı
  değiştirilemez düz metin olarak görünür. Gönder düğmesi birincil düğmedir, metni "Kaydet".
  Geri basılan değerler bugünkü gibi; hesabı personel kaydına bağlı değilse form yerine bilgi
  iletisi.
- R-4 **Yeni Personel:** Etiketli alanlar (Ad, Birim — mevcut birimler öneri olarak, İşe giriş
  tarihi), birincil "Kaydet" düğmesi. Geri basılan değerler ve bozuk tarihin geri basılmaması
  bugünkü gibi; yetkisiz hesaba form yerine hata iletisi.
- R-5 **Dar ekranda tablolar:** Tablo kendi kutusu içinde yana kaydırılabilir; sayfanın kendisi
  360 px genişlikte yana kaymaz. Tablo yapısı (başlık hücreleri, satırlar) korunur; kart düzenine
  geçilmez.
- R-6 **Durum rozeti:** Durum, metniyle birlikte bir rozet olarak gösterilir; durum metni bugünkü
  değerdir. Tür eşlemesi: onaylandı → başarı, beklemede (harfe duyarsız) → uyarı, reddedildi →
  tehlike, diğer her değer → nötr. Uygulama kodu CSS rengi değil yalnız bu türü seçer; görünüm
  şablon ve Bootstrap'tan gelir. Anlam renge bağlı değildir (metin her zaman yazılı).
- R-7 **İleti dili (0034 R-5'in devamı):** Hata iletisi kırmızı kutuda ve ekran okuyucuya hemen
  duyurulur; başarı iletisi ("Talep #N onaylandı/reddedildi", "Personel #N eklendi") yeşil kutuda
  ve sessizce duyurulur; "hesabınız bir personel kaydına bağlı değil" bilgi kutusunda; "Bu işlem
  için yetkiniz yok" hata kutusunda. İleti metinleri değişmez.
- R-8 **Onayla / Reddet:** Küçük düğmeler — Onayla yeşil çerçeveli, Reddet kırmızı çerçeveli. Her
  biri bugünkü gibi ayrı bir POST formudur, CSRF token'ı taşır, JavaScript gerektirmez. Görünen
  etiket "Onayla" / "Reddet" kalır; ekran okuyucunun okuduğu ad talebi tanımlar: personel adı ve
  tarihler (ör. "Ayşe Yılmaz, 2026-11-02 – 2026-11-04 talebini onayla").
- R-9 **Metinler:** Görünen başlık ve etiketler düzelir: "Izin Talepleri" → "İzin Talepleri",
  "Baslangic" → "Başlangıç", "Bitis" → "Bitiş", "Gun" → "Gün", "Kullanilan" → "Kullanılan" —
  tablo başlıklarında ve Yeni Talep etiketlerinde. İleti metinleri ve durum değerleri değişmez.
- R-10 **CSP'ye hazırlık (0034 R-6'nın genişlemesi):** **Tüm** şablonlarda satır içi `<style>`,
  `style=` özniteliği, satır içi `<script>` ve `on…=` olay öznitelikleri yoktur; bir mimari testi
  bunu sabitler. `app.css`'teki 0034 ara kuralları kalkar; özelleştirme yalnız Bootstrap
  sınıfları ve `--bs-*` değişkenleriyle.
- R-11 **Davranış aynı:** Rotalar, durum kodları, yönlendirmeler, ileti metinleri, log satırları,
  CSRF ve yetki davranışı değişmez. Görünen metindeki tek farklar R-9 düzeltmeleri ve R-8'in
  ekran okuyucu adlarıdır.
- R-12 **Testler davranışa bakar (0034 R-8):** İşaretlemeye harfiyen bakan ve bu işte kırılan her
  assert, aynı davranışı işaretlemeden bağımsız soran bir assert'e çevrilir; her değişiklik planda
  eski satır → yeni satır olarak listelenir, review'da "zayıflatma mı" ayrıca sorulur (AGENTS.md
  kural 5). R-9 metin düzeltmeleri bekleneni değiştirir; bunlar da tabloda ayrı işaretlenir.

## User experience
- **Flow:** (1) Ana Sayfa'da sayaçlar ve bakiye tablosu. (2) Talepler'de tablo; sonuçlandırabildiği
  talepte "Onayla"/"Reddet" → aynı ekran, başarı ya da hata iletisiyle. (3) Yeni Talep'te formu
  doldurur, "Kaydet" → başarıda Talepler, hatada aynı form, hata iletisi, girilen değerler
  geri basılı. (4) İK, Yeni Personel'de formu doldurur, "Kaydet" → aynı ekran, başarı iletisi;
  hatada hata iletisi. Telefonda tablolar kendi içinde yana kaydırılır.
- **States — Ana Sayfa:** veri var; personel yok (yalnız başlık satırı, bugünkü gibi); rol başına
  görünen satırlar (İK hepsi, Yönetici kendi birimi, Personel kendisi — bugünkü kural).
- **States — Talepler:** talep yok (yalnız başlık satırı); düğmeli ve düğmesiz satırlar; dört durum
  türü (onaylandı, beklemede, reddedildi, bilinmeyen); başarı iletisi (`?sonuc=` geçerli);
  geçersiz `?sonuc=` (ileti yok); hata iletileri (bakiye yetersiz, zaten sonuçlanmış, bulunamadı
  404, yetkisiz 403, beklenmeyen hata 500, CSRF 400).
- **States — Yeni Talep:** İK (personel listesi); Personel/Yönetici (adı düz metin); hesap personel
  kaydına bağlı değil (bilgi, form yok); doğrulama hataları (eksik/bozuk girdi, ters tarih
  aralığı, bulunamayan personel, iş günü yok, bakiye yetersiz, beklenmeyen hata, CSRF), değerler
  geri basılı.
- **States — Yeni Personel:** form (birim önerileriyle); başarı (`?eklendi=`); doğrulama hataları
  (boş ad, boş birim, bozuk/boş/gelecek tarih, beklenmeyen hata, CSRF); yetkisiz hesap (hata, form
  yok).
- **Design reference:** none — tasarım dosyası yok; Bootstrap 5.3'ün varsayılan bileşenleri (tablo,
  rozet, uyarı, form, düğme, kart). Kanıt önce/sonra ekran görüntüleridir (360 px ve geniş; JS
  açık ve kapalı).
- **Accessibility:** Formlarda her alanın görünür, alana bağlı etiketi var; klavye sırası bugünkü
  gibi (alanlar → Kaydet; tablo satırlarında Onayla → Reddet), Enter formu gönderir. Onay/red
  düğmelerinin ekran okuyucu adı talebi tanımlar (R-8). Hata hemen, başarı sessizce duyurulur.
  Durum renkten bağımsız (metin). Kontrast Bootstrap varsayılanlarının altına düşmez.

## Constraints & out of scope
- **Yeni bağımlılık yok:** 0034'te projeye konan Bootstrap 5.3.8 kullanılır; yeni JavaScript yok.
- **Out of scope:** durum değerlerinin Türkçe yazımı (`Onaylandi`, `Reddedildi` — domain verisi);
  alan düzeyinde hata işaretleme (sunucunun hangi alanın hatalı olduğunu bildirmesini ister);
  boş tablolar için yeni "kayıt yok" metni; sıralama, filtre, sayfalama; CSP başlığının kendisi;
  marka teması, Sass; `__` (dunder) şablon yasağı (0033 F-1 takip işi); giriş ekranı ve çerçeve
  (0034'te bitti).
- **Split:** clarify 1 — tek spec (ortak makrolar dört ekranda birden kullanılıyor; bölmek aynı
  makroya iki kez dokunmak ve ara durum demek); kabul — İbrahim Gürhan, 2026-11-16. Kriter sayısı
  12 (sınır).

## Acceptance criteria
- [ ] AC-1 — Ana Sayfa: üç sayaç aynı metin ve sayılarla, ayrı kutularda; bakiye tablosu başlıkları
  "Ad, Birim, Hak, Kullanılan, Kalan, Bekleyen"; her rol için satırlar ve değerler bugünküyle aynı;
  personel yokken yalnız başlık satırı.
- [ ] AC-2 — Talepler: tablo başlığı "İzin Talepleri", sütunlar "Personel, Başlangıç, Bitiş, Gün,
  Neden, Durum"; her rol için satırlar bugünküyle aynı; onay/red düğmeleri tam olarak bugün
  gösterildiği satırlarda; talep yokken yalnız başlık satırı.
- [ ] AC-3 — Durum rozeti: her satırda durum metni bugünkü değer; tür onaylandı → başarı,
  beklemede (harfe duyarsız) → uyarı, reddedildi → tehlike, bilinmeyen → nötr; hiçbir şablonda ve
  uygulama kodunda durum için CSS rengi yok.
- [ ] AC-4 — Onayla/Reddet: her düğme ayrı bir POST formu, CSRF token'ı var, görünen etiket
  "Onayla"/"Reddet"; ekran okuyucu adı personel adını ve iki tarihi içerir; düğmeye basınca sonuç
  (durum, ileti, yönlendirme, log) bugünküyle aynı; token'sız istek bugünkü gibi reddedilir.
- [ ] AC-5 — İletiler: başarı iletileri yeşil, sessizce duyurulan kutuda; hata iletileri (Talepler,
  Yeni Talep, Yeni Personel'in tüm hata durumları, CSRF, 403/404/500) kırmızı, hemen duyurulan
  kutuda; "personel kaydına bağlı değil" bilgi kutusunda; geçersiz `?sonuc=` ve `?eklendi=`
  bilinmeyen kayıt → ileti yok. Metinler bugünküyle aynı.
- [ ] AC-6 — Yeni Talep: Personel, Başlangıç, Bitiş, Neden alanlarının her birinin görünür ve
  alana bağlı etiketi var; İK'da personel listesi (seçili değer geri basılı), Personel/Yönetici'de
  adı düz metin; hata sonrası değerler bugünkü gibi geri basılı; "Kaydet" birincil düğme; bağlı
  personel yokken form yok, bilgi iletisi var.
- [ ] AC-7 — Yeni Personel: Ad, Birim, İşe giriş tarihi etiketli; birim önerileri mevcut
  birimlerden; değerler bugünkü gibi geri basılı, bozuk tarih basılmaz; "Kaydet" birincil düğme;
  yetkisiz hesapta form yok, hata kutusu var; başarıda başarı kutusu.
- [ ] AC-8 — Dar ekran: 360 px genişlikte dört ekranın hiçbiri sayfa düzeyinde yana kaymaz; geniş
  tablolar kendi kutusu içinde kayar; sayaç kutuları alt alta dizilir.
- [ ] AC-9 — JavaScript kapalı: onay, red, Yeni Talep ve Yeni Personel gönderimi çalışır (düğmeyle
  ve Enter ile).
- [ ] AC-10 — Metinler: R-9 düzeltmeleri görünür, eski yazımlar ("Izin", "Baslangic", "Bitis",
  "Gun", "Kullanilan") dört ekranın görünen metninde yok; ileti metinleri ve durum değerleri
  değişmemiş.
- [ ] AC-11 — Satır içi stil/betik yok: `web/templates/` altındaki **her** şablonda `<style>`,
  `style=`, satır içi `<script>` ve `on…=` yok, bir mimari testi bunu sabitler; `app.css`'te 0034
  ara kuralları yok.
- [ ] AC-12 — Davranış aynı: tüm suite yeşil; her ekran × rol × durum için durum kodu,
  yönlendirme ve log satırları `main` ile aynı; görünen metin R-9 ve R-8 farkları dışında aynı;
  işaretlemeye bakan ve değişen her assert planda eski → yeni listelenmiş, aynı davranışı soruyor
  (zayıflatma yok).

## Self-critique (ANALYZE; G-1…G-7 önerildiği gibi — onay: İbrahim Gürhan, 2026-11-16)
- **G-1 Ekran okuyucu adı ve metin karşılaştırması:** R-8'in adı görünmeyen metinle verilirse
  AC-12'nin görünen metin karşılaştırmasında fark çıkar; öznitelikle verilirse çıkmaz. *Öneri:*
  yöntem planın işi; AC-12 iki yolu da kabul eder (fark yalnız bu adlar).
- **G-2 Tarih biçimi:** Ekran okuyucu adındaki tarihler tabloda görünen biçimde (bugün
  `2026-11-02`) okunur; ayrı bir biçimlendirme bu işte yok. *Öneri:* kabul.
- **G-3 Boş tablolar:** "Kayıt yok" gibi yeni bir metin eklemek R-11'i (görünen metin aynı) bozar.
  *Öneri:* boş tabloda yalnız başlık satırı kalsın (bugünkü gibi); yeni metin ayrı iş.
- **G-4 Başarı iletisinin duyurulması:** Başarı iletisi bir yönlendirmeden sonra sayfa açılırken
  gelir; "sessizce duyurulur" bazı ekran okuyucularda ilk yüklemede okunmayabilir (0034'teki
  `role="alert"` notunun aynısı). *Öneri:* kabul; VERIFY'da gözlem notu.
- **G-5 Uyarı rozetinin kontrastı:** "Beklemede" rozeti sarı zeminde; Bootstrap'ın uyarı rozeti koyu
  metin kullanır. *Öneri:* Bootstrap'ın renkli-zemin-metin eşleşmesi kullanılsın, renk elle
  verilmesin; kontrast AC'si Accessibility'deki genel kural.
- **G-6 `status_color`'ın anlamı değişiyor:** Python artık renk değil tür döndürür; adı ve
  davranışı değişen bir fonksiyon. *Öneri:* kabul — AC-3 "uygulama kodunda durum için CSS rengi
  yok" bunu bağlar; adlandırma planın işi.
- **G-7 Boyut:** 12 kriter, tek yetenek (ekran gövdeleri); clarify 1'de tek spec kararı. *Öneri:*
  bölme yok.

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
