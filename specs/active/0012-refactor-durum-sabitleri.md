# Spec 0012 — refactor-durum-sabitleri (mini)

- Status: In progress
- Mode: lite
- Plan: `specs/plans/0012-plan.md`
- Source: #26
- Design: — (UI değişmez)
- Supersedes: —

## Intent
`docs/conventions.md` durum değerlerinin kodda sabit olarak tanımlanmasını, string olarak
dağıtılmamasını istiyor. Spec 0010 `domain/leave_service.py`'ye `PENDING`, `APPROVED`, `REJECTED`
sabitlerini ekledi; ama eski kodun bir kısmı hâlâ `"Beklemede"`, `"Onaylandi"`, `"Reddedildi"`
literallerini kullanıyor (0010 review F-2). Bu iş, uygulama kodundaki kalan kullanımları sabitlere
çevirir; birinin değiştirilip öbürünün unutulma riskini kaldırır. Davranış değişmez.

## Changed behavior
- none — no observable behavior change

## Preserved behavior
Mevcut karakterizasyon testleri bu davranışları sabitliyor; hepsi **hiçbir test değişmeden** yeşil
kalır.
- [ ] PB-1 — **Kullanılan:** yalnız `Onaylandi` durumundaki taleplerin günleri toplanır (BR-4;
  `tests/test_baseline_service.py::test_only_approved_requests_count_as_used` ve bakiye testleri).
- [ ] PB-2 — **Yeni talep `Beklemede` oluşur** (BR-7; `test_create_request_saves_pending_request`,
  `test_post_valid_request_is_listed_as_pending`).
- [ ] PB-3 — **Ana sayfa sayaçları** Bekleyen / Onaylanan / Reddedilen aynı sayılır
  (`test_dashboard_counts_and_balances`, `test_approval.py` sayaç testleri).
- [ ] PB-4 — **Durum rozeti** aynı renkleri verir, büyük/küçük harf davranışı dahil: `Onaylandi`
  yeşil, `Beklemede` **ve `BEKLEMEDE`** turuncu (turuncu kuralı harfe duyarsız), `Reddedildi`
  kırmızı; `onaylandi`, `reddedildi`, bilinmeyen değer gri (`test_status_badge[×7]`).
- [ ] PB-5 — **Kanıt:** `git diff main -- tests/` boş; `scripts/check` full yeşil; uygulama
  kodunda (`domain/`, `web/`, `app.py`) durum literali yalnız sabitlerin tanımında kalır.

## Out of scope
- `storage/memory.py` açılış verisindeki durum değerleri: bunlar veri kayıtları; storage'ın domain
  sabitlerini import etmesi katman yönünü (`web → domain → storage`) tersine çevirir.
- Testlerdeki literaller (testler değişmez; zaten veri değerini sınarlar).
- Rozetin harfe duyarsız turuncu kuralını ya da 0010 düğmelerinin harfe duyarlı kontrolünü
  düzeltmek: bu bir davranış değişikliği olur (`/change`).
- Durumu bir `Enum`'a çevirmek, yeni modül açmak.

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
