# Spec 0001 — baseline-tests

- Status: Shipped
- Mode: lite
- Plan: `specs/plans/0001-plan.md`

## Intent
IK ve geliştirme ekibi, kimsenin sahiplenmediği 2015'ten kalma uygulamayı güvenle
değiştirebilmek istiyor. Bunun için uygulamanın **bugünkü** davranışı otomatik testlerle
sabitleniyor (karakterizasyon / baseline):
- iş kuralları: kıdem, hak, kullanılan, kalan, gün sayısı, talep oluşturma, durum rozeti;
- üç ekranda kullanıcının gördüğü sonuçlar: ana sayfa, talepler, yeni talep.

Başarı ölçütü: davranışı değiştiren her değişiklik en az bir testi kırmızıya düşürür ve
`./scripts/check` gerçek testlerle yeşil olur. Bilinen hatalar **düzeltilmez**; olduğu gibi
sabitlenir ve ilgili BR/OD numarasıyla işaretlenir. Düzeltme ileride `/change` veya `/fix-bug`
ile, bu testleri bilinçli olarak güncelleyerek yapılır. Uygulama kodu değişmez.

## Requirements
- R-1 Testler, `docs/domain.md`'deki "Mevcut kod" davranışını birebir doğrular. Kanuna veya
  hedef kurala uymayan yerler de buna dahildir.
- R-2 Bilinen hatalı davranışı sabitleyen her test, ilgili kuralı/kararı (BR-n / OD-n) anar ve
  okuyana "bu mevcut davranıştır, hedef değildir" bilgisini verir.
- R-3 Testler "bugün"ü **2026-10-23** olarak görür; gerçek saatten bağımsız olarak her gün aynı
  sonucu verir.
- R-4 Her test aynı başlangıç verisinden (uygulamanın açılış verisi) başlar. Bir testin yaptığı
  değişiklik başka bir teste ulaşmaz; testlerin sırası sonucu değiştirmez.
- R-5 Ekran testleri kullanıcının gördüğü değerleri doğrular: sayılar, adlar, durumlar ve
  mesajlar. Biçimlendirmenin birebir aynısını aramaz; yaklaşan "HTML'i şablona taşı" refactor'ı
  davranış değişmediği sürece testleri kırmamalıdır.
- R-6 Uygulama kodu (`app.py`) ve davranışı değişmez. Yeni çalışma zamanı bağımlılığı eklenmez.
- R-7 İlk testler geldiği için `./scripts/check`'teki geçici "test bulunamadı = yeşil" toleransı
  kaldırılır; bundan sonra hiç test toplanmaması check'i kırmızıya düşürür.

## User experience
none — no user interface (bu iş yalnızca test ekler; kullanıcının gördüğü hiçbir şey değişmez).

## Constraints & out of scope
- **Kapsam dışı — güvenlik açıkları:** `reason` alanındaki stored XSS ve `debug=True`. Bunlar
  bilinen ve kasıtlı olarak test edilmeyen davranışlardır; ayrı bir `/fix-bug` kendi testleriyle
  kapatır. Hiçbir test bu açıkların varlığını "korunacak davranış" olarak doğrulamaz.
- **Kapsam dışı:** hataları düzeltmek, `app.py`'yi refactor etmek, saat enjeksiyonu, yeni
  özellik, e2e/tarayıcı testi, sunucuyu (`app.run`) başlatmak.
- Test aracı: mevcut pytest ve Flask test istemcisi. Yeni geliştirme bağımlılığı plan aşamasında
  önerilir ve onaylanır (`docs/security.md`).
- Check, geride süreç ve veri bırakmaz (`docs/testing.md`, Resource hygiene); residue testi temiz kalır.
- Split: 11 kriter, ~8–10 eşiğinin üstünde. Önerilen bölünme: 0001 servis kuralları, 0002 ekranlar.
  Önerim: tek tutmak. Kullanıcı yeteneği tek (mevcut davranışı sabitlemek), kriterler aynı
  fixture'ı paylaşıyor ve ayrı spec'ler sadece tören ekler.
  (Split: proposed 0001 servis kuralları, 0002 ekranlar; kept as one — İbrahim Gürhan, 2026-10-23,
  tek kullanıcı yeteneği.)
- Plana bırakılanlar (spec onayında kararlaştırıldı): AC-5'teki geçmiş tarihli talebin somut
  örneği; AC-11'deki sıra bağımsızlığının ek bağımlılık gerektirmeyen kanıt yöntemi.

## Acceptance criteria
Tüm değerler bugün = 2026-10-23 ve açılış verisi içindir.

- [x] AC-1 — **Hak sınırları (mevcut, BR-1/OD-1):** kıdemi 0 olan için hak 0; 1 → 14; 5 → 14;
  6 → 20; 14 → 20; 15 → 20 (kanunda 26, OD-1); 16 → 26.
  *(Revizyon 1, 2026-10-23, review F-1 / R-08: 14 yıl sınırı `docs/testing.md` ile hizalandı.)*
- [x] AC-2 — **Kıdem = yıl farkı (mevcut, BR-2/OD-2):** 2025-12-31'de işe giren biri 1 yıl kıdemli
  sayılır. 2020-02-29'da işe giren 6 yıl, 2026-06-01'de işe giren 0 yıl kıdemlidir.
- [x] AC-3 — **Gün sayısı = takvim günü (mevcut, BR-3/OD-4):** başlangıç = bitiş → 1 gün.
  Pazartesi–Pazar arası bir hafta → 7 gün (hafta sonu da düşer). Bitiş başlangıçtan bir gün önce →
  0 gün (BR-9 doğrulanmıyor).
- [x] AC-4 — **Kullanılan ve kalan (BR-4/BR-5):** yalnızca `Onaylandi` talepler kullanılanı
  artırır; bekleyen ve reddedilenler etkilemez. Açılış verisinde personel başına
  hak / kullanılan / kalan: Ayse Yilmaz 26/12/14 · Mehmet Demir 20/0/20 · Zeynep Kaya 14/0/14 ·
  Ahmet Celik 20/0/20 · Elif Sahin 0/0/0.
- [x] AC-5 — **Servis ile talep oluşturma (BR-6/7/8):**
  - Kalan, talep gününden büyükse talep `Beklemede` durumuyla, bir sonraki numarayla (9)
    kaydedilir ve işlem başarılı döner.
  - Geçmiş tarihli talep de kaydedilir.
  - Kalan, talep gününe **eşitse** talep kaydedilmez ve işlem başarısız döner (mevcut, BR-6).
  - Olmayan bir personel için talep kaydedilmez ama işlem **başarılı** döner (mevcut).
- [x] AC-6 — **Durum rozeti:** `Onaylandi` yeşil, `Beklemede` turuncu, `Reddedildi` kırmızı
  gösterilir; bilinmeyen bir durum gri gösterilir. Turuncu kuralı büyük/küçük harfe duyarsızdır
  (`BEKLEMEDE` de turuncu), diğerleri duyarlıdır (`onaylandi` gri). Rozet durum metnini içerir.
- [x] AC-7 — **Ana sayfa:** Bekleyen 4, Onaylanan 1, Reddedilen 3 gösterir. Bakiye tablosunda her
  personelin adı, birimi ve AC-4'teki hak / kullanılan / kalan değerleri görünür.
- [x] AC-8 — **Talepler ekranı:** açılış verisindeki 8 talebin her biri; personel adı,
  başlangıç–bitiş tarihi, gün sayısı, neden ve durum metniyle, kayıt sırasıyla listelenir
  (ör. Ayse Yilmaz, 2026-07-06 – 2026-07-17, 12 gün, "Yaz tatili", Onaylandi).
- [x] AC-9 — **Yeni talep formu:** 5 personelin her biri seçenek olarak, ayrıca başlangıç, bitiş,
  neden alanları ve "Kaydet" düğmesi görünür.
- [x] AC-10 — **Yeni talep gönderme:**
  - Geçerli talep (ör. Mehmet Demir, 3 gün) → kullanıcı talepler ekranına yönlendirilir ve
    talep `Beklemede` olarak orada görünür.
  - Kalan < gün (ör. Elif Sahin, 1 gün) → `ERR-412` ve `bakiye yetersiz` içeren bir hata
    mesajı gösterilir ve kayıt oluşmaz. Mesajın geri kalanı (dahili numara vb.) kasıtlı olarak
    sabitlenmez; `docs/conventions.md`'ye göre düzeltilecek bir sızıntıdır.
  - Neden alanı boş bırakılmış geçerli bir talep yine kaydedilir (neden boş olarak).
  - Kalan = gün (ör. Zeynep Kaya, 14 gün) → yönlendirilir ama kayıt oluşmaz (mevcut, BR-6:
    sessiz kayıp).
  - Geçersiz tarih formatı veya olmayan personel → talepler ekranına yönlendirilir ve kayıt
    oluşmaz (mevcut: hata yutuluyor).
- [x] AC-11 — **Test tabanı:** testler herhangi bir sırada çalıştırıldığında aynı sonucu verir
  (R-3, R-4). `./scripts/check` (full) yeşildir ve test sayısı > 0'dır; geçici tolerans
  kaldırılmıştır (R-7). Residue testi (full ve fast) temizdir. `app.py`'nin diff'i boştur (R-6).

## Verification (VERIFY, 2026-10-23, HEAD `3e95822`, bağımsız QA subagent)
Kanıt: `CHECK GREEN (full, 2 steps, 3 s)`, 39 test — tekrar: `./scripts/check`.
Tüm testler `tests/test_baseline_service.py` ve `tests/test_baseline_screens.py` içinde; eşleme
`specs/plans/0001-plan.md` "Criterion ↔ test map".

| Acceptance criterion | Evidence | Status |
|---|---|---|
| AC-1 | `test_entitlement_by_seniority`, `test_entitlement_at_15_years_current` | Pass |
| AC-2 | `test_seniority_is_year_difference_current` | Pass |
| AC-3 | `test_calc_days_counts_calendar_days_current` | Pass |
| AC-4 | `test_balances_at_opening_data`, `test_only_approved_requests_count_as_used` | Pass |
| AC-5 | `test_create_request_*` (4) | Pass |
| AC-6 | `test_status_badge` | Pass |
| AC-7 | `test_dashboard_counts_and_balances` | Pass |
| AC-8 | `test_requests_list_shows_all_requests_in_order` | Pass |
| AC-9 | `test_new_request_form_fields` | Pass |
| AC-10 | `test_post_*` (6 vaka) | Pass |
| AC-11 | `./scripts/check` (39 > 0) · `ANEW_REVERSE_ORDER=1 .venv/Scripts/python -m pytest` 39 passed · `./scripts/residue` ve `--fast` RESIDUE CLEAN · `git diff main -- app.py` boş | Pass |

Mutasyon kontrolü (repo dışı geçici kopya): 39 mutasyonun 37'si kırmızı. Hayatta kalanlar:
`dahili 4127` metni (AC-10 gereği kasıtlı sabitlenmiyor) ve `next_id` artışı (kriter dışı boşluk →
takip spec'i önerildi). R-3 (saatten bağımsızlık) kod okumasıyla doğrulandı.

## Definition of Done
- [x] Every acceptance criterion mapped to proof (test or reproducible observation)
- [x] `scripts/check` green
- [x] Independent review done; real findings fixed, noise rejected with written rationale
- [x] Docs / ADRs updated if behavior or architecture changed
- [x] Spec moved to `specs/done/` (it becomes immutable there)

## Scorecard (fill at ship — honest numbers make the process improvable)
| Metric | Value |
|---|---|
| Spec revisions | 1 (AC-1, review F-1) |
| Fix rounds | 2 |
| Review findings: real / noise | 5 / 0 |
| Regressions introduced | 0 |
| Bugs escaped to production | 0 (henüz yayında değil) |
