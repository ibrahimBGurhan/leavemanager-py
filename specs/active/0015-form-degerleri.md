# Spec 0015 — form-degerleri (mini)

- Status: Approved
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
- [ ] CB-1 — **Bakiye hatası değerleri korur:** Zeynep Kaya, 1–18 Aralık 2026, neden "Aile" →
  bakiye mesajı formun üstünde; formda Personel "Zeynep Kaya" seçili, Başlangıç 2026-12-01,
  Bitiş 2026-12-18, Neden "Aile".
- [ ] CB-2 — **Diğer domain ve sunucu hataları (K-1):** ters tarih, iş günü yok (ör. 14–15 Kasım
  2026) ve beklenmeyen hata (500) ekranlarında aynı şekilde personel seçili, tarihler ve neden dolu.
- [ ] CB-3 — **Bozuk girdi (K-3):** Başlangıç "2026-13-01" → Başlangıç boş, personel, Bitiş ve
  Neden korunur; personel numarası "abc" → hiçbir personel seçili değil, tarihler ve neden korunur;
  personel alanı hiç yoksa aynı.
- [ ] CB-4 — **Olmayan personel (K-4):** personel 99 → mesaj, hiçbir seçenek seçili değil, tarihler
  ve neden korunur.
- [ ] CB-5 — **Kaçış (K-5):** neden `"><script>x</script>` ve `' onfocus='x` olarak gönderilince
  değer kutusunda metin olarak görünür; sayfada yeni `script` öğesi ya da yeni öznitelik oluşmaz.

## Preserved behavior
- [ ] PB-1 — **Boş form:** `GET /new` bugünkü gibi: 5 personel seçeneği, hiçbiri seçili
  işaretlenmemiş, tarih ve neden alanları boş, "Kaydet" (0001/AC-9).
- [ ] PB-2 — **Hata davranışı:** mesaj metinleri, mesajın formun üstünde olması, durum kodları
  (400 / 500), kayıt oluşmaması ve ihlal sırası (0008, 0013, 0014) aynı.
- [ ] PB-3 — **CSRF hatası (K-2):** 400, Türkçe mesaj, form boş, kayıt yok (0011) aynı.
- [ ] PB-4 — **Başarılı gönderim:** Talepler ekranına yönlendirme ve yeni satır aynı; sonraki
  `GET /new` boş.
- [ ] PB-5 — **Testler:** mevcut testler değişmeden yeşil; `scripts/check` full yeşil.

## Out of scope
- Neden alanına uzunluk sınırı (`docs/security.md` hedefi; ayrı iş).
- "Seçiniz" boş seçeneği, alan bazlı hata mesajları, istemci tarafı doğrulama.
- Formu Jinja şablonuna taşımak (F-3 / `|safe` borcu; ayrı iş).
- Talepler ekranındaki onay/red hata ekranları (form yok).

## Definition of Done
- [ ] `scripts/check` green
- [ ] Independent review done; real findings fixed, noise rejected with written rationale
- [ ] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots)
- [ ] Spec moved to `specs/done/` (immutable there)

## Scorecard (fill at ship — honest numbers make the process improvable)
| Metric | Value |
|---|---|
| Spec revisions | |
| Fix rounds | |
| Review findings: real / noise | |
| Regressions introduced | |
| Bugs escaped to production | |
