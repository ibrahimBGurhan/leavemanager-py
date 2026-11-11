# Spec 0028 — birim-onerisi-turkce-sira (mini)

- Status: Shipped
- Mode: lite
- Plan: `specs/plans/0028-plan.md`
- Source: issue #43 — 0022 G-2 (spec 0022 VERIFY: "Yeni Personel ekranındaki birim öneri listesi
  Türkçe alfabeye göre sıralansın (bugün kod noktası sırası: Ç, İ, Ö, Ş, Ü ile başlayan birimler
  Z'den sonra; `docs/domain.md` BR-11). Yeni bağımlılık olmadan; davranış değişikliği olduğu için
  `/change`.")
- Design: — (görünüm değişmez; yalnız öneri listesinin sırası değişir)
- Supersedes: 0022/AC-5 — yalnız öneri listesinin "alfabetik" sırası (0022 R-1, G-4); tekillik,
  yazıldığı gibi gösterim ve boş liste aynen kalır (PB-1).

## Intent
İK, Yeni Personel ekranında Birim alanına yazarken kayıtlı birimleri öneri listesinden seçer. Liste
bugün karakter koduna göre sıralı: Çağrı Merkezi, İdari İşler, Özel Proje, Şube, Üretim gibi Türkçe
harfle başlayan birimler ve küçük harfle yazılmış birimler Z'den sonra, listenin sonunda çıkıyor.
Bu değişiklikle liste Türkçe alfabe sırasına göre, büyük/küçük harf ayırmadan sıralanır; yeni bir
bağımlılık eklenmez ve sonuç sunucunun dil ayarına bağlı olmaz.

Triage kaydı (issue #43, 2026-11-11): rubrik (a) hata değil — kod noktası sırası 0022 VERIFY G-2'de
bilinen sınır olarak kabul edildi ve BR-11'e yazıldı; (b) kabul kriteri değişiyor (0022 AC-5'in
"alfabetik"i daralıyor) → CHANGE lane; (c) paylaşılan kod yok. İnsan onayı: İbrahim Gürhan.

### Gözlem (ANALYZE, 2026-11-11, HEAD `28d8035`, açılış verisi)
Açılış verisine (IT, Muhasebe, IK, Satis) İK olarak şu birimlerle birer personel eklendi: Üretim,
Çağrı Merkezi, İdari İşler, Şube, Özel Proje, Zemin, ıslak, ar-ge, Arge, ARGE, 2. Bölge, Éclair.
`GET /personel/yeni` öneri listesi: `2. Bölge, ARGE, Arge, IK, IT, Muhasebe, Satis, Zemin, ar-ge,
Çağrı Merkezi, Éclair, Özel Proje, Üretim, İdari İşler, ıslak, Şube`. Bugünkü test
(`tests/test_add_employee.py::test_unit_suggestions_are_distinct_and_sorted`) bu sırayı
`[..., "Satis", "it"]` ile sabitliyor.

## Changed behavior
- [x] CB-1 — **Türkçe alfabe (S-1):** Harfler şu sırayla karşılaştırılır:
  a b c ç d e f g ğ h ı i j k l m n o ö p q r s ş t u ü v w x y z. (q, w, x Türk alfabesinde yok;
  Latin alfabesindeki yerlerine konur.) Ç, Ğ, İ, Ö, Ş, Ü ile başlayan birimler alfabedeki yerinde
  görünür, Z'den sonra değil.
- [x] CB-2 — **Büyük/küçük harf ayrılmaz, Türkçe kurallarla (S-2):** Karşılaştırmada I ile ı, İ ile
  i aynı harftir; diğer harflerde büyük ve küçük aynıdır. Bu kuralla aynı harflerden oluşan iki
  birim (ör. "ARGE" ve "Arge") yan yana gelir; aralarında karakter kodu küçük olan önce gelir
  (genelde büyük harf önce; İ ile i'de i önce, çünkü İ'nin karakter kodu büyüktür) — sıra her
  zaman aynıdır. *(Spec revizyonu 1, review round 1 F-1: yalnız parantez düzeltildi; kural aynı.)*
- [x] CB-3 — **Harf olmayan karakterler ve alfabe dışı harfler (S-3):** Boşluk, noktalama ve
  rakamlar her harften önce gelir (kendi aralarında karakter koduna göre; böylece "IT Destek",
  "ITA"dan önce gelir). Bu alfabede olmayan harfler (ör. é, ä, ß) z'den sonra, karakter koduna göre
  gelir.
- [x] CB-4 — **Örnek (Gözlem'deki küme):** Öneri listesi tam olarak şu sırada görünür:
  `2. Bölge, ar-ge, ARGE, Arge, Çağrı Merkezi, IK, ıslak, IT, İdari İşler, Muhasebe, Özel Proje,
  Satis, Şube, Üretim, Zemin, Éclair`.
- [x] CB-5 — `docs/domain.md` BR-11'deki "Bilinen sınır (VERIFY 0022 G-2)" notu kalkar; yerine
  CB-1…CB-3'ün sıralama kuralı yazılır.

## Preserved behavior
- [x] PB-1 — **Listenin geri kalanı aynı (0022 R-1, G-4):** Her birim bir kez ve yazıldığı gibi
  görünür ("it" ile "IT" iki ayrı birimdir; spec 0021 tam eşleşme); yalnız boşluktan oluşan birim
  listede yoktur; personeli olmayan veritabanında liste boştur.
- [x] PB-2 — **Kayıt değişmez:** Birimler girildiği gibi saklanır (kırpma dışında, harf büyüklüğü
  korunur, 0022 R-3); Yönetici'nin birim eşleşmesi (spec 0021) ve diğer tüm ekranlar ile listelerin
  sırası (Ana Sayfa, Talepler, Yeni Talep'in personel listesi) bugünkü gibidir.
- [x] PB-3 — **Bağımsızlık (S-4):** Yeni bağımlılık yok (`requirements*.txt` değişmez); sıra
  işletim sisteminin ya da sunucunun dil (locale) ayarına bağlı değildir — Windows'ta ve CI'da
  (Linux) aynı sonuç.
- [x] PB-4 — **Testler gerçekten sınar** (VERIFY'da mutantla): kod noktası sırası (bugünkü kod),
  harf büyüklüğüne duyarlı sıra, Türkçe kuralı olmayan büyük/küçük harf eşlemesi (`str.lower`:
  I → i) ve ç/ş/ğ/ö/ü/ı'yı temel harfe indiren sıra kırmızıdır.
- [x] PB-5 — Mevcut testler değişmeden geçer; tek istisna
  `test_unit_suggestions_are_distinct_and_sorted`'ın beklenen listesidir (Supersedes 0022/AC-5:
  o testin kümesinde `"it"` artık `"IT"` ile `"Muhasebe"` arasına gelir). `scripts/check` full
  yeşil.

## Out of scope
- Diğer listelerin sırası (Ana Sayfa bakiye tablosu, Talepler, Yeni Talep'in personel listesi):
  numara ya da kayıt sırasıyla gelir, değişmez.
- Birim adlarının normalleştirilmesi (harf büyüklüğünü birleştirme, "ar-ge" = "Arge" sayma).
- Tarayıcının öneri listesini kendi filtrelemesi ve gösterimi (`<datalist>` yazarken süzme
  tarayıcıya aittir; sıra yalnız sunucunun gönderdiği sıradır).
- Issue #43'ün diğer maddeleri (0020 F2-1(b)).

## Decisions (ANALYZE; onay: İbrahim Gürhan, 2026-11-11 — S-1…S-5 önerildiği gibi)
- **S-1 Alfabe:** 29 harflik Türk alfabesi; q, w, x Latin yerlerine (p–r, v–y arası). *Öneri: kabul*
  — birim adlarında yabancı kökenli kelimeler (Web, Quality, Xerox) olabilir; Latin yerleri
  kullanıcının beklediği yer, alfabe dışına atmak onları listenin sonuna iter.
- **S-2 Harf büyüklüğü:** Türkçe kurallarla büyük/küçük ayırmadan (I↔ı, İ↔i); eşitlikte karakter
  kodu. *Öneri: kabul* — sözlük sırası budur; eşitlik kuralı sırayı her çalıştırmada aynı tutar.
  Bilinçli sonuç: Türkçe kuralla "I" küçük "ı"dır, "i" ise büyük "İ". Bu yüzden "IK" ve "IT" ı
  harfiyle sıralanır ve "İdari İşler"den önce gelir (CB-4); "IT" ile "it" Türkçede aynı kelime
  değildir (ıt / it), aralarına ı ya da i ile başlayan başka birimler girebilir. *Alternatif:*
  I'yı i saymak (Latin kuralı) — "IT"/"it" yan yana gelir ama "Islak" ile "İslam" gibi Türkçe
  çiftler karışır; Türkçe kural issue'nun istediği.
- **S-3 Harf dışı ve alfabe dışı karakterler:** boşluk/noktalama/rakam önce, alfabe dışı harfler z'den
  sonra, ikisi de kendi içinde karakter koduna göre. *Öneri: kabul* — basit, öngörülebilir ve
  tam sıra; "IT Destek" < "ITA" sözlük beklentisine uyar. *Alternatif:* é→e gibi aksanları temel
  harfe indirmek (`unicodedata`) — Türkçe harflerle çakışmaması ek kural ister; birim adlarında
  nadir, şimdi gereksiz.
- **S-4 Bağımlılık ve locale:** Kural uygulamanın kendi kodunda tanımlanır; `locale`/ICU
  kullanılmaz. *Öneri: kabul* — issue yeni bağımlılık istemiyor; `locale.strxfrm` sunucunun kurulu
  dil paketine bağlıdır (Windows ile CI farklı sonuç verir) ve süreç genelinde ayar değiştirir.
  Kodun yeri (domain kuralı mı, web yardımcısı mı) PLAN kararıdır.
- **S-5 Kapsam:** yalnız birim öneri listesi. *Öneri: kabul* — issue maddesi bunu istiyor; diğer
  listeler ad/birim sırasıyla değil numarayla sıralı, aynı sorun orada yok.

## Self-critique (ANALYZE)
- **G-1 Belirsizlik:** "Türkçe alfabe sırası" tek başına harf büyüklüğü, rakam ve aksanlar için
  yoruma açıktı; CB-2, CB-3 ve CB-4'teki somut örnek bunu kapatır. CB-4 ile CB-1…CB-3 çelişirse
  CB-1…CB-3 esastır ve çelişki spec hatasıdır.
- **G-2 Test edilebilirlik:** Her CB ekran üzerinden (`GET /personel/yeni` öneri listesi) sınanır;
  CB-5 doküman diff'iyle. PB-4'teki mutantlar CB'lerin gerçekten ayırt edildiğini gösterir.
- **G-3 Supersedes:** Mevcut bir testin beklentisi değişiyor (PB-5). Bu, onaylı Supersedes'in
  sonucudur; plan değişen satırı tek tek gösterir, başka test dokunulmaz.
- **G-4 Risk:** Sıralama anahtarı tüm Unicode'u karşılamalı (boşluk, emoji, birleşik karakterler)
  ve hata vermemeli; 50 karakter sınırı ve birim sayısı küçük olduğu için performans sorun değil.

## Verification (VERIFY, 2026-11-11, HEAD `a49a07a`, bağımsız QA subagent)
CB-1…CB-5, PB-1…PB-5 Pass; full `CHECK GREEN (full, 3 steps, 71 s)` (712 passed, 5 skipped).
Mutantlar repo dışı kopyada: istenen beş mutant (kod noktası, harfe duyarlı, `str.lower`, temel
harfe indirme, eşitlik yok) ve 9 ek mutant kırmızı; değişmemiş kopya ve iki kontrol yeşil. Önce /
sonra öneri sırası HTML'den okundu: `main` Gözlem'le, HEAD CB-4 ile birebir aynı; öneri kutusu açık
ekran görüntüleri PR'da (merge'den önce). Review: round 1 F-1 (düşük) real → fix-1 + spec
revizyonu 1 (CB-2 parantezi); round 2 clean. **Kayıt notları:** VERIFY G-1 — "yalnız boşluktan
oluşan birim listede yok" maddesini koruyan test yok (0022'den beri; issue #43'e takip işi);
G-2 — eşitlik kuralını deterministik olarak birim testi korur, ekran testi seed'e bağlı;
G-3 — bazı birim testleri anahtarın şeklini de sınar, yanlarında davranış assert'i var. Ayrıntı:
`specs/plans/0028-plan.md` "Triage" ve "Verify".

## Definition of Done
- [x] `scripts/check` green
- [x] Independent review done; real findings fixed, noise rejected with written rationale
- [x] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots)
- [x] Spec moved to `specs/done/` (immutable there)
