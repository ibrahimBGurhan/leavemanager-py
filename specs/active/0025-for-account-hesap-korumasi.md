# Spec 0025 — for-account-hesap-korumasi (mini)

- Status: In progress
- Mode: lite
- Plan: `specs/plans/0025-plan.md`
- Source: issue #43 — 0020 G-3 (spec 0020 VERIFY: "Mimari koruma testi
  (`test_routes_reach_data_only_through_for_account`) `for_account` argümanının `g.account` olmasını
  da şart koşabilir; bugün sahte bir hesapla çağrıyı yakalamıyor")
- Design: —
- Supersedes: —

## Intent
Web katmanı veriye yalnız `svc.for_account(...)` üzerinden ulaşır ve bunu bir mimari test kilitler.
Ama test çağrıya hangi hesabın verildiğine bakmaz: bir route `svc.for_account({"role": "IK"})` ya da
başka bir hesapla çağırsa mimari test yeşil kalır, hatayı yalnız ekran testleri (tesadüfen)
yakalar. Bu iş davranışı değiştirmez; görünümün her zaman kapının kurduğu oturum hesabıyla
(`g.account`, spec 0019) açıldığını ayrı bir mimari testle kilitler.

Triage kaydı (issue #43, 2026-11-10): rubrik (a) hata değil, (b) kriter değişmiyor, (c) ortak kod
yok; iş yeni test olduğu için trivial lane'in "yeni bir test → yeniden triage" kuralı gereği insan
kararıyla CHANGE lane'de, mini-spec ile (spec 0004, 0023, 0024 kalıbı).

## Changed behavior
none — no observable behavior change. Kanıtı aşağıdaki Preserved behavior kriterleri taşır.

## Preserved behavior
- [ ] PB-1 — **Hesap kuralı:** `web/` altındaki her `svc.for_account` kullanımı bir çağrıdır ve
  tam olarak tek bir konumsal argüman alır: `g.account` (anahtar sözcüklü argüman yok). Bugünkü tek
  çağrı (`web/routes.py`, `view()`) bu kurala uyar; kural ihlal edilirse test dosyayı ve satırı
  adlandırarak kırmızıya düşer.
- [ ] PB-2 — **Boşuna geçmez:** test `web/` altında en az bir `svc.for_account` çağrısı bulmazsa da
  kırmızıdır (çağrı silinir ya da yeniden adlandırılırsa kural sessizce boş kalmaz).
- [ ] PB-3 — Testler gerçekten sınar (VERIFY'da mutantla): argüman sabit bir hesap sözlüğü,
  `session[...]`, başka bir değişken ya da `g.user` olursa; ek argüman ya da anahtar sözcüklü
  argüman eklenirse; `svc.for_account` bir değişkene atanıp öyle çağrılırsa test kırmızı; bugünkü
  kod yeşil.
- [ ] PB-4 — Üretim kodu değişmez (`git diff main -- domain web storage app.py` boş); mevcut
  testlerin hiçbiri (`test_routes_reach_data_only_through_for_account` dahil) değişmez, zayıflatılmaz
  ya da silinmez; `scripts/check` full yeşil.

## Out of scope
- `g.account`'un doğru kurulması (spec 0019 ve 0023 testleri kapsar) ve `g.account`'a başka bir
  yerde değer atanması.
- `getattr(svc, "for_account")` gibi dinamik erişim (mevcut mimari test de yakalamaz; kod
  incelemesine kalır).
- Issue #43'ün diğer maddeleri (0020 F2-1(b); 0021 G-B, G-E; 0022 G-1, G-2).

## Decisions (ANALYZE; onay: İbrahim Gürhan, 2026-11-10 — S-1…S-3 önerildiği gibi)
- **S-1 Yer:** yeni test `tests/test_architecture.py` içinde, mevcut testin yanında
  (`test_for_account_gets_the_logged_in_account`); dosyanın yardımcıları (`layer_files`, `parse`,
  `where`) kullanılır. Mevcut test fonksiyonları değişmez. *Öneri: kabul.*
- **S-2 Biçim:** kural ast ile, sözdizimine bakılarak kurulur (argüman `ast.Attribute`: ad `g`,
  öznitelik `account`); `svc.for_account` adının her geçişi incelenir, yalnız çağrılar değil (atama
  ile kaçış yakalanır). *Öneri: kabul.*
- **S-3 Boşluk koruması:** en az bir çağrı şartı (PB-2). *Öneri: kabul.*

## Definition of Done
- [ ] `scripts/check` green
- [ ] Independent review done; real findings fixed, noise rejected with written rationale
- [ ] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots)
- [ ] Spec moved to `specs/done/` (immutable there)
