# Spec 0024 — yeni-talep-ve-bos-talepler-testleri (mini)

- Status: In progress
- Mode: lite
- Plan: `specs/plans/0024-plan.md`
- Source: issue #43 — 0020 G-4 (spec 0020 VERIFY: "Yeni Talep ekranında tarih, neden alanları ve
  'Kaydet'in varlığı, bağlı ama talebi olmayan Personel'in boş Talepler ekranı ve klavye sırası
  için test")
- Design: —
- Supersedes: —

## Intent
Spec 0020'nin Personel ekran durumlarından üçü bugün yalnız gözlemle doğrulanmış, testle
kilitli değil: Personel'in Yeni Talep formunda tarih ve neden alanlarıyla "Kaydet"in bulunması,
personel kaydına bağlı ama hiç talebi olmayan Personel'in Talepler ekranı ve formun klavye yolu
(tarih → neden → Kaydet; 0020 Accessibility). Bu iş davranışı değiştirmez; bu durumları testle
kilitler ki bir ekran değişikliği onları sessizce bozamasın.

Triage kaydı (issue #43, 2026-11-10): rubrik (a) hata değil, (b) kriter değişmiyor, (c) ortak kod
yok; iş yeni test olduğu için trivial lane'in "yeni bir test → yeniden triage" kuralı gereği insan
kararıyla CHANGE lane'de, mini-spec ile (spec 0004 ve 0023 kalıbı).

## Changed behavior
none — no observable behavior change. Kanıtı aşağıdaki Preserved behavior kriterleri taşır.

## Preserved behavior
Testler bugünkü test kalıbıyla çalışır (oturum kontrolü `as_account` ile; gerçek giriş yolu spec
0023'te kilitli). A = Ayse Yilmaz (1, IT). C = talebi olmayan, test içinde eklenen bir personel.

- [ ] PB-1 — **Yeni Talep, Personel (A'ya bağlı):** tek bir form vardır; içinde personel alanı
  olarak A'nın adı düz metin, Başlangıç ve Bitiş tarih alanları (`type="date"`), Neden metin
  alanı ve "Kaydet" gönderme düğmesi bulunur; personel seçimi yoktur (0020 States, Yeni Talep).
  Aynı alanlar İK'nın formunda da bugünkü gibi bulunur (seçimle birlikte).
- [ ] PB-2 — **Klavye yolu:** formda alanlar sırasıyla Başlangıç → Bitiş → Neden → Kaydet gelir
  (İK'da önce personel seçimi); sayfada `tabindex` ve betik yoktur; düğme formun içindedir,
  Enter formu gönderir (0020 Accessibility; `tests/test_login.py::test_keyboard_path` kalıbı).
- [ ] PB-3 — **Talepler, bağlı ama talebi olmayan Personel (C'ye bağlı):** sayfa 200 döner,
  tablo yalnız başlık satırından oluşur (Personel, Baslangic, Bitis, Gun, Neden, Durum), hiçbir
  düğme ve başka personelin verisi yoktur. Ana Sayfa'da sayılar 0 ve yalnız C'nin bakiye satırı
  vardır (0020 States, "Talepler, talebi yok").
- [ ] PB-4 — Testler gerçekten sınar: Yeni Talep'ten bir alan ya da "Kaydet" kaldırılırsa,
  alanların sırası değişirse, sayfaya `tabindex` eklenirse ya da talebi olmayan Personel'e
  başka talepler görünürse bu testlerden en az biri kırmızıya düşer (VERIFY'da mutantla).
- [ ] PB-5 — Üretim kodu değişmez (`git diff main -- domain web storage app.py` boş); mevcut
  testlerin hiçbiri değişmez, zayıflatılmaz ya da silinmez; `scripts/check` full yeşil.

## Out of scope
- Davranış ya da ekran değişikliği (ör. Yeni Talep alanlarına `<label>` eklemek — erişilebilirlik
  iyileştirmesi ayrı bir `/change` olur).
- Yönetici ve İK için ayrı boş-ekran testleri (0021 / 0020 testleri kapsar).
- Issue #43'ün diğer maddeleri (0020 G-3, F2-1(b); 0021 G-B, G-E; 0022 G-1, G-2).

## Decisions (ANALYZE; onay: İbrahim Gürhan, 2026-11-10 — S-1…S-4 önerildiği gibi)
- **S-1 Oturum:** `as_account` kalıbı (gerçek giriş 0023'te kilitli; burada ekran durumları
  sınanır). *Öneri: kabul.*
- **S-2 Talebi olmayan personel:** demo verisinde talebi olmayan personel yok; test bir personel
  ekler (C, id 6) ve hesabı ona bağlar. *Öneri: kabul.*
- **S-3 Klavye yolu kanıtı:** DOM sırası + `tabindex`/betik yokluğu + düğmenin formda olması
  (tarayıcı testi yok; `test_login.py` kalıbı). *Öneri: kabul.*
- **S-4 Yer:** yeni dosya `tests/test_staff_screens.py`; mevcut test dosyaları değişmez.
  *Öneri: kabul.*

## Definition of Done
- [ ] `scripts/check` green
- [ ] Independent review done; real findings fixed, noise rejected with written rationale
- [ ] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots)
- [ ] Spec moved to `specs/done/` (immutable there)
