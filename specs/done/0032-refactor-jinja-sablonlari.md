# Spec 0032 — refactor-jinja-sablonlari (mini)

- Status: Shipped
- Mode: lite
- Plan: `specs/plans/0032-plan.md`
- Source: [ADR-0003](../../docs/decisions/0003-on-yuz-bootstrap.md) ilke 1 (Jinja şablonları) ve
  `docs/security.md` (Input & output) — istek: İbrahim Gürhan, 2026-11-13 ("/refactor ile spec'i
  yaz": PAGE / LOGIN_PAGE ve `%` / `escape` ile kurulan gövdeler `web/templates/` altına;
  `{{ body|safe }}` ve `render_template_string` kalkar; görünüm birebir aynı; mimari testine kural)
- Design: — (görünüm değişmez; Bootstrap ayrı spec)
- Supersedes: —

## Intent
Ekranların HTML'i bugün Python kodunun içinde string olarak kuruluyor ve her kullanıcı değeri elle
kaçışlanıyor; tek bir unutulan `escape` stored XSS demek (`docs/security.md` bunu zaten yasaklıyor).
İş, HTML'i Jinja şablon dosyalarına taşır: kaçış otomatik olur, Python kodu yalnız veri hazırlar.
Kullanıcı hiçbir fark görmez — bu bir refactor (`workflows/refactor.md`); sıradaki Bootstrap işinin
zemini (ADR-0003).

### Gözlem (2026-11-13, HEAD `cec6160`)
- `web/routes.py`: sayfa iskeleti `PAGE` (menü, çıkış formu) ve beş ekranın gövdesi (Ana Sayfa,
  Talepler, Yeni Talep, Yeni Personel, CSRF hata yolları) `%` ile kuruluyor, elle `escape`
  ediliyor ve `{{ body|safe }}` ile basılıyor; yardımcılar `status_badge`, `csrf_field`,
  `decision_buttons` HTML string döndürüyor.
- `web/auth.py`: giriş ekranı `LOGIN_PAGE` zaten Jinja ve otomatik kaçışlı, ama
  `render_template_string` ile koddan.
- Durum rozeti (`status_badge`) durum metnini **kaçışsız** basıyor; durum yalnız domain sabitlerinden
  gelir (bkz. S-5).
- Testler ekranlara yalnız HTTP ile bakıyor; `web` içinden fonksiyon ya da sabit içe aktaran test
  yok (yalnız logger adı `web.routes`). HTML'e bakan assert'ler (ör. `value='Onayla'`,
  `<select name="employee_id">`, `color:red`, `<button type="submit" form="cikis-formu">Çıkış</button>`)
  bugünkü işaretlemeyi harfiyen bekliyor → çıktı bayt bayt korunmalı.

## Changed behavior
none — no observable behavior change. Kanıtı aşağıdaki Preserved behavior kriterleri taşır.

## Preserved behavior
- [x] PB-1 — **Her ekranın HTML'i bayt bayt aynı** (CSRF token değeri hariç): Ana Sayfa; Talepler
  (iletisiz, onay/red başarı iletisi, 403 / 404 / 400 / 500 hata iletileri, CSRF hatası);
  Yeni Talep (İK: personel seçimli; Personel/Yönetici: kendi adı sabit; bağlı personel kaydı yok;
  hata ekranında geri basılan değerler; CSRF hatası); Yeni Personel (boş form, birim önerileri,
  başarı iletisi, hata iletisi ve geri basılan değerler, yetkisiz, CSRF hatası); Giriş (boş,
  hatalı giriş, süre doldu, çıkış yapıldı, CSRF hatası) — İK, Yönetici ve Personel hesaplarıyla.
- [x] PB-2 — **Kaçış aynı:** kullanıcı verisi (personel adı, birim, neden, e-posta, form değerleri)
  her ekranda bugünkü gibi kaçışlı basılır; HTML/script enjeksiyonu testleri aynı sonucu verir.
- [x] PB-3 — **HTTP davranışı aynı:** durum kodları, yönlendirmeler, log satırları, CSRF ve yetki
  davranışı değişmez.
- [x] PB-4 — **Yapı hedefi:** `web/` altındaki Python dosyaları HTML içermez (HTML etiketi içeren
  string sabiti yok) ve `render_template_string` kullanmaz; HTML yalnız `web/templates/` altındaki
  şablonlarda, otomatik kaçış açık; şablonlarda `|safe`, `Markup` ve `autoescape false` yok. Yeni
  bir mimari testi bunu sabitler (S-4).
- [x] PB-5 — **Mevcut testler dokunulmaz:** `tests/` altında var olan hiçbir satır değişmez,
  silinmez, zayıflatılmaz; tek fark `tests/test_architecture.py`'ye eklenen yeni test (yalnız ekleme
  satırları). `scripts/check` full yeşil.

## Out of scope
- Bootstrap, CSS, `web/static/` ve her türlü görünüm değişikliği (ADR-0003, ayrı spec).
- Metin değişiklikleri — Türkçe karakteri eksik başlıklar dahil ("Izin Talepleri", "Baslangic",
  "Kullanilan"): bayt bayt aynılık için olduğu gibi kalır; görünüm spec'inde ele alınır.
- Rotalar, URL'ler, durum kodları, iletiler, log biçimi.
- Güvenlik başlıkları / CSP (ADR-0003 yalnız zemin hazırlar).
- Domain ve storage katmanları.

## Decisions (ANALYZE; onay: İbrahim Gürhan, 2026-11-13 — S-1…S-6 önerildiği gibi)
- **S-1 Şablon düzeni:** `web/templates/` altında `base.html` (bugünkü `PAGE`: başlık, menü, çıkış
  formu), ekran başına bir şablon (`dashboard.html`, `requests.html`, `new_request.html`,
  `new_employee.html`, `login.html`) ve ortak parçalar için `_macros.html` (CSRF alanı, durum
  rozeti, karar düğmeleri, ileti satırı). Python yalnız düz veri hazırlar (sayılar, satırlar,
  bayraklar); şablon domain metodu çağırmaz — yetki kararı (ör. "bu talepte düğme var mı") Python'da
  verilip satıra bayrak olarak konur. *Öneri: kabul* — yetki tek yerde kalır (`docs/security.md`),
  şablon sunumla sınırlı.
- **S-2 Şablon klasörü:** `app.py`'de `Flask(__name__, template_folder="web/templates")`.
  `static_folder` bu işte değişmez (statik dosya yok; Bootstrap spec'i ekler). *Öneri: kabul* —
  Blueprint'e geçmek endpoint adlarını (`login`, `OPEN_ENDPOINTS`) değiştirirdi.
- **S-3 "Birebir aynı"nın kanıtı:** Mevcut testlere ek olarak, VERIFY'da repo dışında (scratchpad)
  bir anlık görüntü karşılaştırması: PB-1'deki her ekran × rol × durum için HTML `main`'de ve dalda
  üretilir, CSRF token değeri sabit bir metinle değiştirilip **bayt bayt** karşılaştırılır. İzin
  verilen fark: yok. Bir fark kaçınılmaz çıkarsa (ör. boşluk) BUILD durur ve insana sorulur.
  *Öneri: kabul* — işaretlemeyi sabitleyen kalıcı testler yazmak, sıradaki görünüm işinde test
  düzenlemesi gerektirirdi; anlık görüntü yalnız bu refactor'ın kanıtı.
- **S-4 Mimari testi bu işte:** `tests/test_architecture.py`'ye bir test eklenir: `web/*.py` HTML
  etiketi içeren string sabiti barındırmaz ve `render_template_string` kullanmaz; `web/templates/`
  altındaki şablonlar `|safe`, `Markup`, `autoescape false` içermez. Test, refactor'dan önce
  kırmızı, sonra yeşil. *Öneri: kabul* — istekte açıkça var ve borcun geri dönmesini engeller;
  yalnız ekleme olduğundan mevcut testlere dokunmaz (PB-5). Alternatif: 0030/0031 kalıbıyla ayrı
  bir `test:` spec'i — daha saf ama aynı satırlar için ikinci bir döngü.
- **S-5 Durum rozetinde kaçış:** Bugün durum metni kaçışsız basılıyor; şablonda otomatik
  kaçışlanır. Domain'in yazdığı ve testlerin kullandığı her durum değeri (`Beklemede`, `Onaylandi`,
  `Reddedildi`, `BEKLEMEDE`, `Iptal` …) özel karakter içermediğinden çıktı bayt bayt aynı; fark
  yalnız `<`, `&`, `"` gibi karakter içeren bir durumda olur ve hiçbir kod yolu böyle bir durum
  yazamaz. *Öneri: kabul — gözlemlenebilir davranış değişikliği değil,* güvenlik yönünde düzeltme;
  PR'da not edilir.
- **S-6 Dal:** `refactor/0032-html-jinja-sablonlari` (`docs/git.md`, Branching). *Öneri: kabul.*

## Self-critique (ANALYZE)
- **G-1 Boşluk tuzağı:** Jinja'nın `{%-` ve satır sonu davranışı küçük boşluk farkları üretebilir;
  bazı testler (`<button …>Çıkış</button>`, `Personel: <ad>`) harfiyen eşleşiyor. S-3'teki bayt
  karşılaştırması bunu yakalar. *Öneri: her ekran ayrı adımda taşınır, her adımda karşılaştırma.*
- **G-2 Çapraz ekran hata yolları:** CSRF hatası `/new`, `/personel/yeni`, `/giris` ve diğer yollar
  için farklı ekranlar çizer; anlık görüntü listesi her yolu içermeli.
- **G-3 Test edilebilirlik:** PB-1 anlık görüntü + mevcut ekran testleri; PB-2 mevcut enjeksiyon
  testleri (`test_security.py`, `test_login.py`, `test_add_employee.py`); PB-3 tüm suite; PB-4 yeni
  mimari testi + mutant (bir `|safe` ya da HTML string geri eklenince kırmızı); PB-5 `git diff`.
- **G-4 Boyut:** Tek yetenek, 5 kriter; dosya sayısı yüksek (2 Python + `app.py` + 7 şablon + 1 test)
  ama her adım bağımsız commit — bölme gerekmez.

## Verification (VERIFY, 2026-11-16, HEAD `2bfde87`)
PB-1…PB-5 Pass; full `CHECK GREEN (full, 3 steps, 57 s)` (715 passed, 5 skipped). Anlık görüntü
(S-3) repo dışı kopyalarda: `main` (`cec6160`) ↔ dal, 261 dosya (ekran × rol × durum, CSRF yolları,
giriş akışları; durum kodu, `Location` ve log satırları dahil) → `diff -r` boş; tek boşluk mutantı
10/10 farkı yakaladı. Yeni mimari testi `main` kopyasında kırmızı (37 ihlal), dalda yeşil; 11/11
mutant doğru nedenle kırmızı; `|safe` mutantlarında `test_security` / `test_add_employee` kaçış
testleri kırmızı. `tests/` diff'i yalnız ekleme (41/0); 719 → 720 test. Review round 1 F-1 real
(fixed `b766697`), F-2 noise; round 2 I-1 noise. Önce/sonra ekran görüntüleri (Talepler): PR #57.
Ayrıntı: `specs/plans/0032-plan.md` "Triage" ve "Verify".

## Definition of Done
- [x] `scripts/check` green
- [x] Independent review done; real findings fixed, noise rejected with written rationale
- [x] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots)
- [x] Spec moved to `specs/done/` (immutable there)
