# Spec 0031 — log-adi-mimari-testi (mini)

- Status: In progress
- Mode: lite
- Plan: `specs/plans/0031-plan.md`
- Source: spec 0030 G-2 (`specs/done/0030-refactor-karar-log-adi.md`, Self-critique: "Yeni test
  olmadan ileride biri web'e yeniden bir log adı tablosu ekleyebilir … gerekirse
  `tests/test_architecture.py`'ye 'web `domain.access`'ten `ACTION_` adı içe aktarmaz' kuralı ayrı
  bir işle eklenir"); issue #43 kapanış yorumu ("iş değil" notu, 2026-11-13)
- Design: —
- Supersedes: —

## Intent
Yetkisiz bir denemenin log'a hangi işlem adıyla ("onay", "red", "bakiye" …) yazılacağına yalnız
yetki katmanı karar verir; spec 0030 bunu onay / red için tek yere topladı. Ama bugün bu kuralı
koruyan kalıcı bir test yok: kanıt yalnız 0030 VERIFY'daki tek seferlik tarama ve mutantlardı.
Bu iş davranışı değiştirmez; web katmanının log adlarını yetki katmanından almasını ayrı bir mimari
testle kilitler, böylece ad tablosunun web'e geri dönmesi `scripts/check`'te kırmızıya düşer.

Triage kaydı (2026-11-13, İbrahim Gürhan onayı: "CHANGE, 0030 G-2"): (a) hata değil — bugünkü kod
spec 0030'a uyuyor, kalıcı testin yokluğu G-2'de kabul edilmiş risk; (b) yeni bir kriter (kalıcı
kural) gerekiyor ve iş yeni bir test — trivial lane'in "yeni bir test → yeniden triage" kuralı;
(c) ortak kod yok (yalnız `tests/test_architecture.py`) → CHANGE lane, mini-spec (0025, 0029
kalıbı).

### Gözlem (ANALYZE, 2026-11-13, HEAD `2f133d2`)
- Yetki katmanı beş log adı tanımlıyor (`domain/access.py:22-26`): `ACTION_APPROVE` "onay",
  `ACTION_REJECT` "red", `ACTION_CREATE_FOR_OTHER` "baskasi adina talep", `ACTION_BALANCE`
  "bakiye", `ACTION_ADD_EMPLOYEE` "personel ekleme".
- `web/` bunların hiçbirini içe aktarmıyor; `domain.access`'ten yalnız `parse_request_id` alıyor
  (`web/routes.py:12`). `app.py` `domain.access`'i hiç içe aktarmıyor.
- `web/` içinde "onay", "baskasi adina talep", "bakiye", "personel ekleme" metin sabiti yok;
  `"red"` üç yerde var ama CSS rengi (`web/routes.py:84`, `:165`, `:328`) — log adı değil.
- Mevcut mimari testler (`tests/test_architecture.py`) import'ları `ast` ile tarıyor; bu kuralı
  sınayan test yok.

## Changed behavior
none — no observable behavior change. Kanıtı aşağıdaki Preserved behavior kriterleri taşır.

## Preserved behavior
- [ ] PB-1 — **Ad kuralı:** `web/` altındaki hiçbir dosya yetki katmanının log adlarını
  (`domain.access` içindeki `ACTION_` önekli adlar) kullanmaz: ne adla içe aktarır
  (`from domain.access import ACTION_…`, takma adla da), ne yıldızla içe aktarır
  (`from domain.access import *`), ne de modülü içe aktarıp öznitelik olarak erişir
  (`import domain.access` / `from domain import access` → `….ACTION_…`). Bugünkü kod uyar; kural
  ihlal edilirse test dosyayı ve satırı adlandırarak kırmızıya düşer.
- [ ] PB-2 — **Boşuna geçmez:** yetki katmanında `ACTION_` önekli en az bir modül düzeyi ad yoksa
  (adlar yeniden adlandırılır ya da taşınırsa) test de kırmızıdır; kural sessizce boş kalmaz.
- [ ] PB-3 — **Test gerçekten sınar** (VERIFY'da mutantla, repo dışı kopyada): web'e
  `from domain.access import ACTION_APPROVE` (düz ve takma adla), yıldızlı import,
  `from domain import access` + `access.ACTION_REJECT` ve `import domain.access` +
  `domain.access.ACTION_BALANCE` eklenirse; yetki katmanındaki adlar `LOG_` önekine çevrilirse test
  kırmızı; bugünkü kod yeşil.
- [ ] PB-4 — Üretim kodu değişmez (`git diff main...HEAD -- domain web storage app.py` boş);
  mevcut testlerin hiçbiri değişmez, zayıflatılmaz ya da silinmez (yeni test eklenir); `scripts/check`
  full yeşil.

## Out of scope
- Web'de log adlarının metin sabiti olarak yazılması (`"onay"`, `"red"` …): `"red"` CSS rengiyle
  çakışıyor, metin taraması gürültü üretir; review'a kalır (bkz. S-2).
- `app.py` ve `storage/` (bugün `domain.access`'i içe aktarmıyorlar; kural `web/` için).
- Dinamik erişim (`getattr(access, "ACTION_" + …)`, `__import__`) — mevcut mimari testler gibi
  yazılı erişime bakar; review'a kalır.
- Log biçimi, adların kendisi, yetki davranışı.

## Decisions (ANALYZE; onay: İbrahim Gürhan, 2026-11-13 — S-1…S-5 ve G-1…G-3 önerildiği gibi)
- **S-1 Şimdi değer mi:** spec 0030 bu testin bugünkü değerini "düşük" saydı (G-2). Seçenekler:
  (a) şimdi yap — kural ucuz (tek test, mevcut yardımcılar), 0030'un hedefini kalıcı kılar ve
  mimari kurallar dosyasının kalıbına oturur; (b) yapma — G-2 notu yeterli, review yakalar.
  *Öneri: (a)* — maliyet küçük, kayıp riski (sessiz geri dönüş) kalıcı; #43'te kalan başka iş yok.
- **S-2 Kapsam — beş adın hepsi:** kural yalnız onay / red için değil, `ACTION_` önekli tüm adlar
  için (önekle, adları tek tek listelemeden: yeni bir ad da otomatik kapsanır). Metin sabiti
  taraması yok (Out of scope). *Öneri: kabul* — "log adlarını yalnız yetki katmanı bilir" tek kural;
  önek, ad listesinin testte ikinci kez tutulmasını önler (0030'un çözdüğü sorunun aynısı).
- **S-3 Yer ve biçim:** yeni test `tests/test_architecture.py` içinde
  (ör. `test_web_does_not_use_the_decision_log_names`), dosyanın yardımcıları (`layer_files`,
  `parse`, `imports`, `where`) ile, `ast` taramasıyla; mevcut test fonksiyonları değişmez.
  *Öneri: kabul* — 0025 kalıbı.
- **S-4 Mimari doküman:** `docs/architecture.md`'de `domain/access.py` maddesine tek cümle: log
  adlarını yalnız yetki katmanı bilir, web kullanmaz (`tests/test_architecture.py`) — `web/routes.py`
  maddesindeki `for_account` cümlesinin kalıbıyla. "Forbidden dependencies" listesine yeni numara
  eklenmez. *Öneri: kabul* — kural belgelenmiş olur; numaralı liste katmanlar arası import
  yasakları için.
- **S-5 Dal:** `feature/0031-log-adi-mimari-testi` (`docs/git.md`, Branching: "Also for
  CHANGE-lane mini-specs"; iş refactor değil, yeni test). *Öneri: kabul* — 0029'un dalıyla
  (`feature/0029-bos-birim-oneri-testi`) aynı kalıp.

## Self-critique (ANALYZE)
- **G-1 Gürültü:** Önek kuralı `domain.access` dışından gelen `ACTION_` adlarını (ör. web'in kendi
  `MSG_ACTION_UNEXPECTED`'i) yakalamamalı: kural yalnız `domain.access` kaynaklı adlara bakar;
  web'in kendi sabitleri serbest. *Öneri:* PB-1 bu sınırla yazıldı; VERIFY'da zararsız kontrol
  olarak `MSG_ACTION_UNEXPECTED`'in varlığında testin yeşil kaldığı gösterilir.
- **G-2 Göreli import:** `web/` içinden `from ..domain.access import …` — proje göreli import
  kullanmıyor, ama mevcut `imports()` yardımcısı göreli import'u çözüyor; kural ona dayanırsa
  ücretsiz kapsanır. *Öneri:* PB-1'e ayrıca yazma; plan yardımcıyı kullanırsa yeter.
- **G-3 Sabit yerine metin:** Biri web'e `{"approve_request": "onay"}` gibi metinle bir tablo
  koyarsa test yakalamaz (S-2, Out of scope). Log adlarını tam eşitlikle sınayan mevcut testler
  (`test_forbidden_is_logged` vb.) davranışı korur; yapıyı review korur. *Öneri: kabul edilebilir
  sınır, kayıt notu.*
- **G-4 Test edilebilirlik:** PB-1, PB-2 yeni testle; PB-3 VERIFY mutantlarıyla; PB-4 diff + check.
- **G-5 Boyut:** Tek kural, 4 kriter — bölme gerekmez.

## Definition of Done
- [ ] `scripts/check` green
- [ ] Independent review done; real findings fixed, noise rejected with written rationale
- [ ] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots)
- [ ] Spec moved to `specs/done/` (immutable there)
