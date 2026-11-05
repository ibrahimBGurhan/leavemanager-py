# Spec 0015 — form-degerleri (mini)

- Status: Shipped
- Mode: lite
- Plan: `specs/plans/0015-plan.md`
- Source: #31
- Design: — (form düzeni değişmez; yalnız alanlar dolu gelir. Önce/sonra ekran görüntüsü kanıttır)
- Supersedes: 0008 "Out of scope" S-3 ve 0011 K-4 (form değerlerinin korunmaması kapsam dışı
  notlarıydı; kabul kriteri değişmez)

## Intent
Yeni Talep formu bir hatayla yeniden gösterildiğinde personel seçimi ilk personele (Ayse Yilmaz)
döner, tarihler ve neden boşalır. Kullanıcı tarihi düzeltip tekrar gönderdiğinde farkına varmadan
talebi yanlış personel adına girebilir. Bu iş, hata ekranında kullanıcının girdiği değerleri
korur; girilen metin sayfaya güvenli (kaçışlı) basılır.

## Kararlar (clarify)
- **K-1 Hangi hatalar:** domain ve sunucu hataları — olmayan personel, ters tarih, iş günü yok,
  yetersiz bakiye, beklenmeyen hata (500) — ve bozuk girdi. Değerler korunur.
- **K-2 CSRF hatası: korunmaz.** Token geçersizse isteğin kaynağı belirsizdir; başka bir siteden
  gelen sahte formun verisi sayfaya geri basılmaz. Form boş gelir (0011 davranışı aynı).
- **K-3 Bozuk girdi:** her alan ayrı değerlendirilir; geçerli olan korunur, geçersiz olan boş
  gelir. Tarih yalnız `YYYY-MM-DD` olarak ayrıştırılabiliyorsa geri basılır (ham metin değil).
  Personel yalnız var olan bir personelin numarasıysa seçili gelir.
- **K-4 Olmayan personel:** hiçbir seçenek seçili işaretlenmez (tarayıcı ilk seçeneği gösterir);
  tarihler ve neden korunur. Arayüzden üretilemeyen bir durum (değiştirilmiş form); "Seçiniz"
  seçeneği eklemek formu değiştirir (0001/AC-9), kapsam dışı.
- **K-5 Kaçış:** neden ve tarihler öznitelik değeri olarak kaçışlı basılır; `"`, `'`, `<`, `>`, `&`
  metin olarak görünür, yeni öğe ya da öznitelik oluşmaz (`docs/security.md`).

### Hasım okur taraması (onaylı)
- **S-1 Mevcut testler:** değişiklik yalnız öznitelik eklediği için kırılmaları beklenmez; plan
  web dahil tam denemeyle doğrular, kırılan olursa R-07.
- **S-2 Neden boşlukları:** neden metni olduğu gibi (boşluklarıyla) geri basılır.
- **S-3 Boyut:** tek yetenek, 5 CB; bölme yok.

Spec onayı: İbrahim Gürhan, 2026-11-05 (K-1…K-5, S-1…S-3 önerildiği gibi).

## Changed behavior
- [x] CB-1 — **Bakiye hatası değerleri korur:** Zeynep Kaya, 1–18 Aralık 2026, neden "Aile" →
  bakiye mesajı formun üstünde; formda Personel "Zeynep Kaya" seçili, Başlangıç 2026-12-01,
  Bitiş 2026-12-18, Neden "Aile".
- [x] CB-2 — **Diğer domain ve sunucu hataları (K-1):** ters tarih, iş günü yok (ör. 14–15 Kasım
  2026) ve beklenmeyen hata (500) ekranlarında aynı şekilde personel seçili, tarihler ve neden dolu.
- [x] CB-3 — **Bozuk girdi (K-3):** Başlangıç "2026-13-01" → Başlangıç boş, personel, Bitiş ve
  Neden korunur; personel numarası "abc" → hiçbir personel seçili değil, tarihler ve neden korunur;
  personel alanı hiç yoksa aynı.
- [x] CB-4 — **Olmayan personel (K-4):** personel 99 → mesaj, hiçbir seçenek seçili değil, tarihler
  ve neden korunur.
- [x] CB-5 — **Kaçış (K-5):** neden `"><script>x</script>` ve `' onfocus='x` olarak gönderilince
  değer kutusunda metin olarak görünür; sayfada yeni `script` öğesi ya da yeni öznitelik oluşmaz.

## Preserved behavior
- [x] PB-1 — **Boş form:** `GET /new` bugünkü gibi: 5 personel seçeneği, hiçbiri seçili
  işaretlenmemiş, tarih ve neden alanları boş, "Kaydet" (0001/AC-9).
- [x] PB-2 — **Hata davranışı:** mesaj metinleri, mesajın formun üstünde olması, durum kodları
  (400 / 500), kayıt oluşmaması ve ihlal sırası (0008, 0013, 0014) aynı.
- [x] PB-3 — **CSRF hatası (K-2):** 400, Türkçe mesaj, form boş, kayıt yok (0011) aynı.
- [x] PB-4 — **Başarılı gönderim:** Talepler ekranına yönlendirme ve yeni satır aynı; sonraki
  `GET /new` boş.
- [x] PB-5 — **Testler:** mevcut testler değişmeden yeşil; `scripts/check` full yeşil.

## Out of scope
- Neden alanına uzunluk sınırı (`docs/security.md` hedefi; ayrı iş).
- "Seçiniz" boş seçeneği, alan bazlı hata mesajları, istemci tarafı doğrulama.
- Formu Jinja şablonuna taşımak (F-3 / `|safe` borcu; ayrı iş).
- Talepler ekranındaki onay/red hata ekranları (form yok).

## Review (2026-11-05, bağımsız reviewer subagent)
- **Round 1** (HEAD `8f0abd8`): güvenlik clean — her geri basma yolu probe'landı (kaçış, uzun ve
  denetim karakterli girdi, tam genişlikli rakam, tekrarlı alan, CSRF yolu); 14 mutantın 12'si
  kırmızı (biri güvenli eşdeğer). Bulgular F-1 (düşük), F-2 (bilgi).
- **Round 2** (HEAD `485b240`, fix diff'i): **clean**; F-1 düzeldi, `.strip()` mutantı kırmızı.

### Triage (İbrahim Gürhan, 2026-11-05)
- **F-1 — real → fix-1 (`485b240`):** S-2 (neden boşluklarıyla geri basılır) testle korunmuyordu;
  `reason-spaces` parametresi eklendi.
- **F-2 — noise:** plan haritasındaki test adları koddakinden farklı (500 ayrı test,
  `raw-text-dates` ek parametre); davranış tam kapsanıyor, VERIFY gerçek adları kullanır.

## Verification (VERIFY, 2026-11-05, HEAD `d68e1c9`, bağımsız QA subagent)
Deneyler, gerçek süreç ve ekran görüntüleri repo dışında, scratch'teki `git archive` kopyalarında
(`main` `919d125` ve HEAD) üretildi; hiçbiri commit'lenmedi. Suite: HEAD `244 passed, 5 skipped`,
`CHECK GREEN (full)`. Ters kontrol: HEAD'in `tests/test_form_values.py` testleri `main`'in kodunda
`12 failed, 3 passed` (yeşil 3: PB-1, PB-3, PB-4 — bugünkü davranış). CSRF'te değer geçiren ve
nedeni kaçışsız basan mutantlar kırmızı. Test adları koddaki gerçek adlardır (F-2).

| Kriter | Kanıt | Durum |
|---|---|---|
| CB-1 | `test_balance_error_keeps_values` (`main`'de kırmızı). Gerçek süreç: 400, bakiye mesajı, Zeynep seçili, `2026-12-01`, `2026-12-18`, `Aile "x"`; önce/sonra ekran görüntüsü | Pass |
| CB-2 | `test_other_errors_keep_values[reversed/no-working-days]`, `test_unexpected_error_keeps_values` (500, iç metin sızmaz). Gerçek süreç: ters tarih ve hafta sonu hatalarında değerler dolu | Pass |
| CB-3 | `test_malformed_input_keeps_valid_fields[bad-start/bad-employee/missing-employee/raw-text-dates/reason-spaces]`. Gerçek süreç: `2026-13-01` → başlangıç boş, diğerleri dolu | Pass |
| CB-4 | `test_unknown_employee_selects_nothing`. Gerçek süreç: personel 99 → seçili yok, diğerleri dolu | Pass |
| CB-5 | `test_reason_is_escaped[double-quote/single-quote]`; kaçışsız mutant kırmızı. Gerçek süreç: `script` öğesi 0, `input` sayısı `main` ile aynı | Pass |
| PB-1 | `test_empty_form_on_get` (iki sürümde yeşil); HEAD `value=""` basar, tarayıcıda aynı | Pass |
| PB-2 | Mevcut `test_request_errors.py`, `test_baseline_screens.py` değişmeden yeşil; gerçek süreçte mesajlar, durum kodları ve kayıt sayısı `main` ile aynı | Pass |
| PB-3 | `test_csrf_error_keeps_nothing` (CSRF mutantında kırmızı), değişmeyen `test_csrf.py`. Gerçek süreç: token'sız POST'ta gönderilen metin sayfada yok, form boş | Pass |
| PB-4 | `test_success_redirects_and_next_form_is_empty`; gerçek süreç: 302 `/requests`, yeni satır, sonraki form boş | Pass |
| PB-5 | `tests/` diff'i yalnız yeni dosya; mevcut 12 test dosyası blob-identical | Pass |

Ekran görüntüleri (repoda değiller, PR'a eklenir): bakiye hatası önce (form boş) / sonra (form
dolu), CSRF hatası (form boş), kaçış örneği.

### VERIFY triage (İbrahim Gürhan, 2026-11-05)
- **G-1 — kabul:** 500 gerçek süreçte üretilemiyor; `test_unexpected_error_keeps_values` kanıtlar.
- **G-2 — kabul:** QA kopyasında exec-bits atlandı; repoda `git ls-files -s` ile ve ship
  commit'inden sonra `scripts/check` full ile kapanır.
- **G-3 — kapsam dışı:** repoda takip edilmeyen `.agents/` ve `.codex/` klasörleri belirdi (bu iş
  ya da `scripts/init` üretmedi; dış bir araç). Dokunulmadı, commit'e girmedi; insan inceler.
- **G-4 — bilgi:** QA'nın bir süreç sorgusu izin sınıflandırıcısınca reddedildi; etrafından
  dolaşılmadı.

## Definition of Done
- [x] `scripts/check` green
- [x] Independent review done; real findings fixed, noise rejected with written rationale
- [x] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots)
- [x] Spec moved to `specs/done/` (immutable there)

## Scorecard (fill at ship — honest numbers make the process improvable)
| Metric | Value |
|---|---|
| Spec revisions | 0 |
| Fix rounds | 1 (fix-1: review F-1, yalnız test) |
| Review findings: real / noise | 1 / 1 (F-1 real, F-2 noise; round 2 clean). VERIFY: G-1/G-2 kabul, G-3 kapsam dışı |
| Regressions introduced | 0 |
| Bugs escaped to production | 0 (henüz yayında değil) |
