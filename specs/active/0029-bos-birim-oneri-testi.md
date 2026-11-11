# Spec 0029 — bos-birim-oneri-testi (mini)

- Status: In progress
- Mode: lite
- Plan: `specs/plans/0029-plan.md`
- Source: issue #43 — 0028 G-1 (spec 0028 VERIFY: "Boş birimin (yalnız boşluk) öneri listesine
  girmediğini sınayan karakterizasyon testi: `web/routes.py`'deki `.strip()` süzgeci kaldırılınca
  tüm suite yeşil kalıyor.")
- Design: —
- Supersedes: —

## Intent
Yeni Personel ekranındaki birim öneri listesi, kayıtlı personelin birimlerinden kurulur ve yalnız
boşluktan oluşan birimleri göstermez (spec 0022 R-1 / G-4, spec 0028 PB-1). Ekrandan böyle bir birim
girilemez (kırpılınca boş kalan birim reddedilir), ama veritabanında bulunabilir: eski veri, elle
düzenleme ya da ileride başka bir giriş yolu. Bugün bu süzgeci hiçbir test korumuyor; kaldırılsa
liste boş görünen seçenekler gösterir ve suite yeşil kalır. Bu iş davranışı değiştirmez; bugünkü
davranışı testle kilitler.

Triage kaydı (issue #43, 2026-11-11): rubrik (a) hata değil, (b) kriter değişmiyor, (c) ortak kod
yok; iş yeni bir test olduğu için trivial lane'in "yeni bir test → yeniden triage" kuralı gereği
CHANGE lane'de, mini-spec ile (spec 0023–0027 kalıbı).

### Gözlem (ANALYZE, 2026-11-11, HEAD `6742300`, bellek deposu, açılış verisi)
Açılış verisinde öneri listesi: `IK, IT, Muhasebe, Satis`. Depoya (`storage.add_employee`, depo
sözleşmesi) birimi `""`, `"   "`, `"\t"`, `" "` (bölünmez boşluk) ve `" 　 "` (ideografik
boşluk) olan beş personel eklendi: liste değişmedi, hâlâ `IK, IT, Muhasebe, Satis`. Birimi yalnız
`"​"` (sıfır genişlikli boşluk — Python'da boşluk karakteri sayılmaz) olan bir personel
eklenince bu değer listede görünür (bkz. Out of scope). Mevcut testler süzgeci sınamıyor: VERIFY
0028'de `.strip()` süzgeci kaldırılınca 712 test geçti.

## Changed behavior
none — no observable behavior change. Kanıtı aşağıdaki Preserved behavior kriterleri taşır.

## Preserved behavior
- [ ] PB-1 — **Yalnız boşluktan oluşan birim listede yok:** Depoda birimi `""`, `"   "`, `"\t"`,
  `" "` ve `" 　 "` olan personel varken Yeni Personel ekranının öneri listesi tam olarak
  açılış verisinin listesidir: `IK, IT, Muhasebe, Satis` (sıra dahil). Ekran 200 döner.
- [ ] PB-2 — **Gerçek birim yine listede:** Aynı durumda birimi boşluklarla çevrili bir ad olan
  personel (ör. `"  Arge  "`, depoya doğrudan) listede yazıldığı gibi görünür — süzgeç yalnız
  boşluktan oluşan birimleri atar, boşluk içeren birimleri değil.
- [ ] PB-3 — **Test gerçekten sınar** (VERIFY'da mutantla): süzgeç kaldırılırsa, yalnız boş metni
  atacak biçimde gevşetilirse (`if e["department"]`) ya da yalnız ASCII boşluğu kırpacak biçimde
  daraltılırsa (`.strip(" ")`) test kırmızıdır; bugünkü kod yeşil.
- [ ] PB-4 — Üretim kodu değişmez (`git diff main -- domain web storage app.py` boş); mevcut hiçbir
  test değişmez, zayıflatılmaz ya da silinmez; `scripts/check` full yeşil.

## Out of scope
- Sıfır genişlikli boşluk (U+200B) gibi Python'un boşluk saymadığı görünmez karakterlerden oluşan
  birimler: bugün listede görünür ve ekrandan da kabul edilir (spec 0022 VERIFY G-4: "aksiyon
  yok"). Bu test o davranışı ne kilitler ne değiştirir.
- Ekrandan boş / yalnız boşluk birim girişinin reddedilmesi (spec 0022 AC-3 testleri kapsar).
- Böyle bir personelin diğer ekranlarda (Ana Sayfa, Talepler) nasıl göründüğü.
- Issue #43'ün diğer maddeleri (0020 F2-1(b)).

## Decisions (ANALYZE; onay: İbrahim Gürhan, 2026-11-11 — S-1…S-5 önerildiği gibi)
- **S-1 Veri nasıl kurulur:** Boşluk birimli personel, uygulamanın deposuna depo sözleşmesinin
  `add_employee` metoduyla doğrudan eklenir (ekran ve domain bunu reddeder). *Öneri: kabul* —
  gerçek durumu (doğrulamadan geçmemiş eski veri) taklit eder; mevcut boş liste testindeki gibi özel
  alanı (`_employees`) değiştirmekten daha sağlam, çünkü sözleşmeli bir metot.
- **S-2 Hangi boşluklar:** `""`, `"   "`, `"\t"`, `" "`, `" 　 "`. *Öneri: kabul* — boş metin
  gevşek süzgeci (`if e["department"]`) yeşil bırakır; ASCII boşluk, sekme ve Unicode boşlukları
  birlikte, süzgecin daraltılmasını (`.strip(" ")`) da yakalar. PB-3'ün mutantları buna dayanır.
- **S-3 Pozitif kontrol (PB-2):** Boşluklarla çevrili gerçek bir birim de eklenir. *Öneri: kabul* —
  "her şeyi at" ya da "boşluk içereni at" gibi aşırı süzgeci yakalar; tek başına PB-1 boş listeyi
  de yeşil sayabilirdi, PB-1 tam liste olduğu için ikisi birlikte güçlü.
- **S-4 Yer:** `tests/test_add_employee.py`'de, mevcut öneri listesi testlerinin yanına tek bir
  yeni test. Yalnız bellek deposu (uygulamanın test deposu). *Öneri: kabul* — süzgeç `web`'de,
  depodan bağımsız; SQLite'ın aynı kayıtları aynen geri verdiği depo sözleşmesi testlerinde zaten
  sınanıyor.
- **S-5 Üretim kodu değişmez** (PB-4). *Öneri: kabul* — iş yalnız test.

## Self-critique (ANALYZE)
- **G-1 Belirsizlik:** "Boş birim" tanımı Python'un `str.strip()`'ine bağlı (Unicode boşlukları
  dahil, U+200B hariç). Spec bunu Gözlem ve Out of scope'ta açık yazar; PB-1 yalnız bugünkü
  süzgecin attığı karakterleri sayar.
- **G-2 Test edilebilirlik:** PB-1 ve PB-2 ekrandan (`GET /personel/yeni`) okunur; PB-3 VERIFY
  mutantlarıyla; PB-4 diff ve check ile.
- **G-3 Kırılganlık:** PB-1 açılış verisinin birim listesine bağlı; açılış verisi değişirse test
  güncellenir. Bu, mevcut öneri listesi testlerinin de bağımlılığı (aynı kalıp).

## Definition of Done
- [ ] `scripts/check` green
- [ ] Independent review done; real findings fixed, noise rejected with written rationale
- [ ] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots)
- [ ] Spec moved to `specs/done/` (immutable there)
