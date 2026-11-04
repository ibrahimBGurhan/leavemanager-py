# Spec 0008 — typed-domain-exceptions (mini)

- Status: Approved
- Mode: lite
- Plan: `specs/plans/0008-plan.md`
- Source: #19
- Design: — (yeni ekran yok; mevcut "Yeni Talep" sayfasında hata mesajı gösterilir)
- Supersedes: 0001/AC-5 (kalan = gün reddi; olmayan personelde "başarılı" dönüş), 0001/AC-10
  (`ERR-412` mesajı; kalan = gün sessiz kaybı; bozuk girdi ve olmayan personelde sessiz
  yönlendirme)

## Intent
Bugün izin talebi kaydedilemediğinde kullanıcı çoğu zaman bunu fark etmiyor. Talepler listesine
yönlendiriliyor ve talebinin kaydedildiğini sanıyor. Bakiye yetersiz olduğunda ise ekranda iç
hata kodu ve dahili telefon numarası görüyor.

Bu iş, talebin neden kaydedilemediğini kullanıcıya anlaşılır bir Türkçe mesajla söyler. Başarısız
bir talebi başarılı gibi göstermez. Bakiye kararı tek yerde verilir. İş kuralı ihlalleri domain'de
tipli istisnalar olarak ifade edilir (`docs/conventions.md`, Error handling).

## Changed behavior
Tüm örnekler bugün = 2026-10-23 ve açılış verisi içindir. "Mesaj gösterilir" şu anlama gelir:
- Yeni Talep sayfası, formun üstünde mesajla birlikte yeniden gösterilir.
- Kayıt oluşmaz.
- Kullanıcı talepler ekranına yönlendirilmez.
- HTTP durumu, iş kuralı ihlalinde ve bozuk girdide **400**, beklenmeyen hatada **500** olur (S-1).
- Birden çok ihlal varsa yalnızca ilkinin mesajı gösterilir. Sıra: bozuk girdi → olmayan personel
  → ters tarih → bakiye (S-4).

- [ ] CB-1 — **Bakiye (BR-6 kararı):**
  - Talep, Kalan ≥ izin günü ise kaydedilir. Bakiyeyi tam kullanan talep kabul edilir (ör. Zeynep
    Kaya, kalan 14, 14 günlük talep → kaydedilir).
  - Kalan < izin günü ise kalanı ve talep edilen günü söyleyen bir mesaj gösterilir (S-2). Örnek:
    Elif Sahin, kalan 0, 1 günlük talep → "Kalan izin bakiyeniz yetersiz (kalan 0 gün, talep
    1 gün)."
  - Mesajda iç kod (`ERR-…`), dahili telefon ya da "IT'ye bildirin" yoktur.
  - Ekran ve servis aynı kararı verir: kalan − 1, kalan ve kalan + 1 gün için sonuç ikisinde de
    aynıdır.
- [ ] CB-2 — **Olmayan personel:** Formda var olmayan bir personel numarası gönderilirse
  "Seçilen personel bulunamadı." mesajı gösterilir (ör. 99).
- [ ] CB-3 — **Tarih aralığı (BR-9):**
  - Bitiş tarihi başlangıçtan önceyse "Bitiş tarihi başlangıç tarihinden önce olamaz." mesajı
    gösterilir.
  - Bitiş = başlangıç geçerlidir ve 1 gün sayılır.
- [ ] CB-4 — **Bozuk ya da eksik girdi:** Aşağıdaki durumlarda "Lütfen personeli ve geçerli
  başlangıç ve bitiş tarihlerini girin." mesajı gösterilir:
  - tarih biçimi geçersiz (ör. `16.11.2026`);
  - tarih alanı boş;
  - personel numarası sayı değil ya da eksik.
- [ ] CB-5 — **Beklenmeyen hata:**
  - Talep kaydedilirken beklenmeyen bir hata olursa "Talep kaydedilemedi. Lütfen daha sonra
    tekrar deneyin." mesajı gösterilir.
  - Hata, stack trace'iyle uygulama loguna yazılır.
  - Kullanıcıya istisna metni, stack trace ya da iç ayrıntı gösterilmez.
- [ ] CB-6 — **Domain sözleşmesi:**
  - Talep oluşturma, iş kuralı ihlalinde tipli bir istisna fırlatır: `InsufficientBalance`,
    `EmployeeNotFound`, `InvalidDateRange`.
  - `InsufficientBalance`, kalan gün sayısını ve talep edilen gün sayısını taşır (S-2).
  - Başarısızlığı dönüş değeriyle bildirmez ve hata yutmaz.
  - Olmayan personel ve yetersiz bakiye için servisi doğrudan çağıran da istisnayı alır.
- [ ] CB-7 — **Belgeler kararları söyler (S-6):**
  - `docs/domain.md`: BR-6, Kalan ≥ gün kabul edilir şeklinde yazılır; "[IK onayı bekliyor]"
    ve "mevcut kod tutarsız" notları kalkar. BR-9 talep oluştururken uygulanır. Invariant'taki
    "bugün ihlal ediliyor" notu güncellenir.
  - `docs/architecture.md`: "Tipli domain istisnaları yok" hedeften kalan farklar listesinden
    çıkar.

## Preserved behavior
- [ ] PB-1 — **Geçerli talep aynen çalışır:**
  - Kullanıcı talepler ekranına yönlendirilir ve talep `Beklemede` durumuyla, sıradaki numarayla
    (9) listelenir.
  - Nedeni boş bırakılmış talep yine kaydedilir.
  - Geçmiş tarihli talep kabul edilir (BR-8).
  - Servis, başarılı oluşturmada bugünkü gibi `True` döner.
- [ ] PB-2 — **Diğer kurallar ve ekranlar değişmez:**
  - Hak, kıdem, kullanılan, kalan ve gün sayısı hesapları aynı kalır. `calc_days`'in ters
    aralıkta 0 dönmesi dahil (0001/AC-3); BR-9 talep oluşturmada uygulanır, hesap fonksiyonunda
    değil.
  - Ana sayfa, talepler ekranı ve yeni talep formunun alanları aynı kalır.
- [ ] PB-3 — **Güvenlik:**
  - `tests/test_security.py` değişmeden yeşil kalır.
  - Hata mesajları kullanıcı girdisini HTML olarak yorumlamaz.
  - `debug` kapalı kalır.
- [ ] PB-4 — **Katman kuralları:**
  - `tests/test_architecture.py` değişmeden yeşil kalır.
  - İstisnalar `domain`'de tanımlanır.
  - Türkçe kullanıcı mesajları `web`'dedir. Domain HTML ya da UI metni üretmez.
- [ ] PB-5 — **Testlerde yalnızca bu spec'in değiştirdikleri değişir:**
  - Yalnızca Supersedes'te anılan davranışları sabitleyen 5 test bilinçli olarak güncellenir:
    - `test_create_request_rejects_when_remaining_equals_days_current`
    - `test_create_request_unknown_employee_reports_success_current`
    - `test_post_insufficient_balance_shows_error`
    - `test_post_remaining_equals_days_is_silently_dropped_current`
    - `test_post_invalid_input_redirects_without_saving_current`
  - Diğer mevcut testler bayt düzeyinde aynıdır.
  - Full ve ters sıra koşuları yeşil, selftest 82/82, residue CLEAN, PR'da CI yeşil.
  - Yeni çalışma zamanı bağımlılığı yok (`logging` standart kütüphane).

## Out of scope
- Split: önerilen bölünme 0008 domain istisnaları ve 0009 web mesajlarıydı. Tek tutuldu
  (İbrahim Gürhan, 2026-11-04). Kullanıcı yeteneği tek: "başarısız talep söylenir". Domain
  istisnası tek başına kullanıcıya bir şey göstermez (S-5).
- Onay/red akışı (OD-7), kimlik doğrulama, bekleyen taleplerin bakiyeden düşülmesi (OD-3), iş
  günü hesabı (OD-4).
- Rozet markup'ı ve Jinja şablonları (F-3). Mesaj bugünkü sayfa yapısı içinde gösterilir.
- Hata sonrası formun girilen değerleri koruması (S-3).
- `create_request`'teki ölü geçmiş tarih dalı (0005 F-2). BR-8 davranışı korunur.

## Definition of Done
- [ ] `scripts/check` green
- [ ] Independent review done; real findings fixed, noise rejected with written rationale
- [ ] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots)
- [ ] Spec moved to `specs/done/` (immutable there)

## Kararlar (spec onayında, İbrahim Gürhan, 2026-11-04)
- **BR-6:** Kalan ≥ gün ise talep kabul edilir. Onaylayan: İbrahim Gürhan (IK adına),
  2026-11-04 (S-6).
- **BR-9:** Bitiş ≥ başlangıç, talep oluştururken uygulanır. `calc_days` değişmez.
- **S-1:** iş kuralı ihlali ve bozuk girdi 400, beklenmeyen hata 500.
- **S-2:** bakiye mesajı kalanı ve talep edilen günü söyler; istisna bu iki sayıyı taşır.
- **S-3:** formun değerleri koruması kapsam dışı; F-3 / Jinja işine kalır.
- **S-4:** ihlal sırası: bozuk girdi → olmayan personel → ters tarih → bakiye. Yalnızca ilk
  ihlal gösterilir.
- **S-5:** bölünmez.
- **S-6:** BR-6 kararı kayda geçti; belgeler CB-7 ile güncellenir.
