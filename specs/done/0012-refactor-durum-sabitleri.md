# Spec 0012 — refactor-durum-sabitleri (mini)

- Status: Shipped
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
- [x] PB-1 — **Kullanılan:** yalnız `Onaylandi` durumundaki taleplerin günleri toplanır (BR-4;
  `tests/test_baseline_service.py::test_only_approved_requests_count_as_used` ve bakiye testleri).
- [x] PB-2 — **Yeni talep `Beklemede` oluşur** (BR-7; `test_create_request_saves_pending_request`,
  `test_post_valid_request_is_listed_as_pending`).
- [x] PB-3 — **Ana sayfa sayaçları** Bekleyen / Onaylanan / Reddedilen aynı sayılır
  (`test_dashboard_counts_and_balances`, `test_approval.py` sayaç testleri).
- [x] PB-4 — **Durum rozeti** aynı renkleri verir, büyük/küçük harf davranışı dahil: `Onaylandi`
  yeşil, `Beklemede` **ve `BEKLEMEDE`** turuncu (turuncu kuralı harfe duyarsız), `Reddedildi`
  kırmızı; `onaylandi`, `reddedildi`, bilinmeyen değer gri (`test_status_badge[×7]`).
- [x] PB-5 — **Kanıt:** `git diff main -- tests/` boş; `scripts/check` full yeşil; uygulama
  kodunda (`domain/`, `web/`, `app.py`) durum literali yalnız sabitlerin tanımında kalır.

## Out of scope
- `storage/memory.py` açılış verisindeki durum değerleri: bunlar veri kayıtları; storage'ın domain
  sabitlerini import etmesi katman yönünü (`web → domain → storage`) tersine çevirir.
- Testlerdeki literaller (testler değişmez; zaten veri değerini sınarlar).
- Rozetin harfe duyarsız turuncu kuralını ya da 0010 düğmelerinin harfe duyarlı kontrolünü
  düzeltmek: bu bir davranış değişikliği olur (`/change`).
- Durumu bir `Enum`'a çevirmek, yeni modül açmak.

## Definition of Done
- [x] `scripts/check` green
- [x] Independent review done; real findings fixed, noise rejected with written rationale
- [x] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots)
- [x] Spec moved to `specs/done/` (immutable there)

## Review (2026-11-05, HEAD `7e2985c`, bağımsız reviewer subagent)
Round 1: **clean**, bulgu yok; fix round yok. Mutantlar repo dışında, scratch'teki `git archive`
kopyalarında kuruldu; hiçbiri commit'lenmedi. Suite kanıtı: HEAD `7e2985c` için `190 passed,
5 skipped`, `CHECK GREEN (full)`; `scripts/doctor` 0 fail, 0 warn.

Refactor iş akışında ayrı VERIFY segmenti yok; aşağıdaki tablo üreticinin değil, bağımsız
reviewer'ın kanıtından kuruldu.

| Kriter | Kanıt | Durum |
|---|---|---|
| PB-1 | `get_used_days` `== APPROVED`; değişen ifadeyi bozan mutant kırmızı (`test_only_approved_requests_count_as_used`, bakiye testleri) | Pass |
| PB-2 | `create_request` `"status": PENDING`; mutant kırmızı (`test_create_request_saves_pending_request`, `test_post_valid_request_is_listed_as_pending`) | Pass |
| PB-3 | Üç sayaç `PENDING` / `APPROVED` / `REJECTED`; her sayaç için mutant kırmızı (`test_dashboard_counts_and_balances`, `test_approval.py` sayaç testleri) | Pass |
| PB-4 | `status_badge`: `APPROVED`, `status.lower() == PENDING.lower()`, `REJECTED`; düz `== PENDING` (M4) ve tek taraflı `.lower()` (M5) dahil mutantlar kırmızı (`test_status_badge[BEKLEMEDE-orange]`) | Pass |
| PB-5 | `git diff main -- tests/` boş; `CHECK GREEN (full)`; `git grep` literal taraması `domain/ web/ app.py`'de yalnız üç sabit tanımını gösterir | Pass |

Kayıtlar:
- Mutantlar: 9'un 9'u kırıldı (değişen her ifade için en az bir mutant).
- Harfe duyarsız taramada kalan `"onaylandi"` / `"reddedildi"` (`web/routes.py` `RESULTS` ve
  yönlendirme) durum değeri değil, başarı mesajının `?sonuc=` URL parametresi; sabite bağlamak
  ilgisiz iki kavramı birleştirir. Dokunulmadı (reviewer önerisi).
- Plan sapması: plan web adımı için "5 satır" diyordu; gerçek 6 satır (rozet 3 + sayaç 3).
  Kapsam aynı, plan tablosu zaten altı ifadeyi listeliyordu; plan metni ship'te düzeltildi.
- İleride ayrı iş olabilir: storage açılış verisinin de kullanabileceği, bağımlılığı olmayan bir
  durum sabitleri modülü (kapsam dışı, bugün gerekli değil).

## Scorecard (fill at ship — honest numbers make the process improvable)
| Metric | Value |
|---|---|
| Spec revisions | 0 |
| Fix rounds | 0 |
| Review findings: real / noise | 0 / 0 (round 1 clean) |
| Regressions introduced | 0 |
| Bugs escaped to production | 0 (henüz yayında değil) |
