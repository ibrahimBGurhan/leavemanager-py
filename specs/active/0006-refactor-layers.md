# Spec 0006 — refactor-layers (mini)

- Status: Approved
- Mode: lite
- Plan: `specs/plans/0006-plan.md`
- Source: #13
- Design: —
- Supersedes: —

## Intent
`app.py` bugün web, iş kuralları ve veriyi tek dosyada tutuyor. Bu iş onu
`docs/architecture.md`'deki üç katmana ayırır: `web → domain → storage`. Böylece iş kuralları
Flask olmadan sınanabilir hale gelir ve ileride kalıcı veritabanına geçiş yalnızca `storage`'ı
değiştirir. Ürün davranışı değişmez. Testler spec 0005'te bu işe hazırlandı; mevcut testlerin
hiçbiri değişmez.

## Changed behavior
none — no observable behavior change.

## Preserved behavior
- [ ] PB-1 — Ürün davranışı aynen kalır: ana sayfa, talepler ekranı, yeni talep formu ve
  gönderimi (geçerli talep, yetersiz bakiye, bozuk girdi, geçmiş tarih) `main` ile bayt düzeyinde
  aynı yanıtı verir (durum kodu, yönlendirme adresi, gövde). Karşılaştırma birden çok "bugün"
  tarihinde, farklı yıllar dahil, yapılır.
- [ ] PB-2 — Mevcut testler hiç değişmez: `git diff main -- tests/` yalnızca PB-5'teki yeni dosyayı
  gösterir; mevcut test dosyaları bayt düzeyinde aynıdır. Full profil yeşil, ters sırada da
  (`ANEW_REVERSE_ORDER=1`). Gereken bir test değişikliği davranış değişikliği demektir: iş durur,
  insana sorulur.
- [ ] PB-3 — Bağlantı noktaları korunur (spec 0005 taahhüdü): `app.py` composition root olarak
  kalır ve `app.clock`, `app.storage`, `app.svc`, `app.app` adlarını aynı anlamla korur.
  `storage.employees()/requests()` bu anahtarlara sahip sözlükler döndürür; `add_*` aynı biçimi
  kabul eder. `python app.py` uygulamayı eskisi gibi başlatır.
- [ ] PB-4 — "Bugün" dışarıdan verilir ve tek kaynaktan gelir: `domain` `datetime.now()` /
  `date.today()` çağırmaz; servis saati ve depoyu kurulumda parametre olarak alır. Kanıt yöntemi
  (spec 0005 F-1): bir kopyada gerçek saat başka bir yıla kaydırılır; kod olduğu gibiyken testler
  yeşil, servis saati yok sayınca kırmızı.
- [ ] PB-5 — Katman kuralları test edilir: yeni bir mimari testi (`tests/test_architecture.py`,
  import taraması) `docs/architecture.md`'deki yasakları sınar:
  - `domain` `flask`, `werkzeug` veya `jinja2` import etmez;
  - `domain` HTML üretmez;
  - `web`, `storage`'ı doğrudan import etmez;
  - SQL kütüphaneleri yalnızca `storage`'da bulunur.

  Her kural, bilerek bozulmuş bir kopyada kırmızıya düşer.
- [ ] PB-6 — Geri kalan her şey aynen kalır: `tests/test_exec_bits.py`, `tools/`,
  `scripts/check.conf` ve ANEW core dosyaları değişmez; `./scripts/selftest` 82/82; residue CLEAN;
  PR'da CI yeşil. Yeni bağımlılık yok.

## Kararlar (spec onayında, İbrahim Gürhan, 2026-11-03)
- **K-1 — Durum rozeti `web`'e taşınır**, çıktısı bayt düzeyinde aynı kalır. `test_status_badge`
  rozeti ekrandan okuduğu için (spec 0005) test değişmez. #13'teki "taşınırsa teste dokunulur"
  notu yanlıştı; #13'e düzeltme yorumu yazılır. Markup değişikliği (F-3) kapsam dışı kalır.
- **K-2 — Mimari testi bu işte eklenir** (PB-5): yeni dosya; mevcut testler değişmez (PB-2).
- **K-3 — Yerleşim:** kökte `domain/`, `storage/`, `web/` paketleri; `SystemClock` `app.py`'de
  (composition root); `LeaveService(clock, storage)`; route'lar veriye servisin salt okuma
  fonksiyonları üzerinden erişir.
- **K-4 — Belgeler bu işte güncellenir:** `docs/architecture.md` "Bugünkü durum",
  `docs/testing.md:19` (spec 0005 N-1).

## Out of scope
- Herhangi bir davranış değişikliği: OD-1…OD-8, BR-9, kalıcılık (SQL), kimlik doğrulama.
- HTML'in Jinja şablon dosyalarına taşınması ve rozet markup'ının değişmesi (F-3).
- mypy (`docs/testing.md`: "refactor sonrası") — ayrı iş.
- `create_request`'teki ölü geçmiş tarih dalının kaldırılması (spec 0005 F-2) — ayrı iş.

## Definition of Done
- [ ] `scripts/check` green
- [ ] Independent review done; real findings fixed, noise rejected with written rationale
- [ ] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots)
- [ ] Spec moved to `specs/done/` (immutable there)
