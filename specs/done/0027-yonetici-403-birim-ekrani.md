# Spec 0027 — yonetici-403-birim-ekrani (mini)

- Status: Shipped
- Mode: lite
- Plan: `specs/plans/0027-plan.md`
- Source: issue #43 — 0021 G-B (spec 0021 VERIFY: "`tests/test_manager_role.py::test_manager_cannot_decide`
  403 ekranının birime süzülmüş olduğunu da pozitif olarak doğrulasın (satır adları
  `== {"Ayse Yilmaz", "Ahmet Celik"}`); bugün yalnız Muhasebe verisinin yokluğu sınanıyor.")
- Design: —
- Supersedes: —

## Intent
Yönetici yetkisi olmayan bir talebi onaylamaya ya da reddetmeye kalkarsa 403 ve "Bu işlem için
yetkiniz yok." alır; ekranda kendi biriminin talepleri görünür (spec 0021, "birime süzülmüş
ekranla"). Bugünkü test yalnız başka birimin verisinin **görünmediğini** sınıyor: ekran boş ya da
yalnız yöneticinin kendi talepleriyle gelse de yeşil kalır. Bu iş davranışı değiştirmez; 403
ekranında birimin taleplerinin **göründüğünü** testle kilitler.

Triage kaydı (issue #43, 2026-11-10): rubrik (a) hata değil, (b) kriter değişmiyor, (c) ortak kod
yok; iş test olduğu için trivial lane'in "yeni bir test → yeniden triage" kuralı gereği insan
kararıyla CHANGE lane'de, mini-spec ile (spec 0023–0026 kalıbı).

### Gözlem (ANALYZE, 2026-11-10, HEAD `0c34fde`, açılış verisi)
Yönetici (Ahmet Celik, IT) olarak `POST /requests/<no>/approve`, numara 4 (kendi bekleyen talebi),
2 (Muhasebe'nin bekleyen talebi), 1 (IT'de sonuçlanmış), 999 (yok), `abc` (sayısal değil): beşinde
de 403 ve aynı tablo — başlık + 3 satır: Ayse Yilmaz (Yaz tatili, Onaylandi), Ahmet Celik
(Yilbasi oncesi, Beklemede), Ayse Yilmaz (Yil sonu, Beklemede). Bu tablo yöneticinin normal
Talepler ekranıyla (`GET /requests`) satır satır aynı.

## Changed behavior
none — no observable behavior change. Kanıtı aşağıdaki Preserved behavior kriterleri taşır.

## Preserved behavior
- [x] PB-1 — **Birim görünür:** `test_manager_cannot_decide`'ın her durumunda (onay ve red × kendi
  bekleyen talebi, başka birimin bekleyen talebi, birimde sonuçlanmış talep, olmayan numara,
  sayısal olmayan numara = 10 durum) 403 ekranının talep tablosundaki personel adları kümesi tam
  olarak `{"Ayse Yilmaz", "Ahmet Celik"}`'tir.
- [x] PB-2 — **Normal ekranla aynı** (S-1): aynı durumlarda 403 ekranının talep tablosu, yöneticinin
  aynı andaki Talepler ekranının tablosuyla satır satır aynıdır (aynı talepler, aynı alanlar, aynı
  sıra).
- [x] PB-3 — **Bugünkü güvenceler korunur:** testin bugünkü assert'leri (403 ve ileti, hiçbir
  kaydın değişmemesi, Muhasebe verisinin yokluğu, log satırı) kaldırılmaz ve zayıflatılmaz.
- [x] PB-4 — Testler gerçekten sınar (VERIFY'da mutantla): 403 ekranı süzülmemiş tüm talepleri,
  boş bir tabloyu ya da yalnız yöneticinin kendi taleplerini gösterirse test kırmızıdır; bugünkü
  kod yeşil.
- [x] PB-5 — Üretim kodu değişmez (`git diff main -- domain web storage app.py` boş);
  `test_manager_cannot_decide` dışında hiçbir test değişmez, zayıflatılmaz ya da silinmez;
  `scripts/check` full yeşil.

## Out of scope
- İK ve Personel'in 403 ekranları (spec 0020 testleri kapsar).
- 403 ekranındaki Onayla / Reddet düğmelerinin hangi satırlarda göründüğü (spec 0021 testleri).
- Issue #43'ün diğer maddeleri (0020 F2-1(b); 0021 G-E; 0022 G-2).

## Decisions (ANALYZE; onay: İbrahim Gürhan, 2026-11-10 — S-1…S-3 önerildiği gibi)
- **S-1 Güç:** issue'nun istediği ad kümesine (PB-1) ek olarak tablo, yöneticinin normal Talepler
  ekranıyla da karşılaştırılır (PB-2). *Öneri: kabul* — ad kümesi eksik süzmeyi (ör. yalnız kendi
  talepleri) yakalar ama aynı adlı bir satırın düşmesini yakalamaz; normal ekranla karşılaştırma
  satırları da sabitler. İkisi birlikte: normal ekran da bozulursa ad kümesi yine yakalar.
- **S-2 Yer:** `test_manager_cannot_decide` yerinde güçlendirilir; ikinci bir test eklenmez.
  *Öneri: kabul* — 0026 S-4 gerekçesi; 10 durumun hepsi zaten bu testte.
- **S-3 Üretim kodu değişmez** (PB-5). *Öneri: kabul* — iş yalnız test.

## Verification (VERIFY, 2026-11-10, HEAD `dc58612`, bağımsız QA subagent)
PB-1…PB-5 PASS; 6/6 bozucu mutant 10/10 kırmızı, değişmemiş kopya ve 2 kontrol yeşil; 4 mutantı
(boş tablo, yalnız kendi talepleri, satır düşmesi, ters sıra) yalnız yeni assert'ler yakalıyor.
**Kayıt notu (VERIFY G-1):** süzgeç iki ekranda birlikte gevşerse PB-2 tek başına yeşil kalır; onu
PB-1 ve `assert_no_b_data` yakalar — PB-1 ileride kaldırılırsa bu boşluk açılır. Review round 1:
verdict clean; F-1 (düşük) noise. Ayrıntı: `specs/plans/0027-plan.md` "Triage" ve "Verify".

## Definition of Done
- [x] `scripts/check` green
- [x] Independent review done; real findings fixed, noise rejected with written rationale
- [x] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots)
- [x] Spec moved to `specs/done/` (immutable there)
