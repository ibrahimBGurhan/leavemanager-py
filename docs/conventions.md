# Conventions

> Bootstrap'te (2026-10-23) dolduruldu. Buradaki her kural ya bir araçla zorlanır (tercih edilen)
> ya da review'da kontrol edilir.

## Language
<!-- Set at bootstrap (step 0) and mirrored in AGENTS.md. Changing it later is allowed — edit both
     places; existing documents are not translated retroactively. -->
- Chat language (interviews, sessions): Turkish (`tr`)
- Document language (docs/, specs, plans, ADRs, review and verify reports): Turkish (`tr`)
- Always English (protocol, not prose): ANEW core files, template headings and field labels,
  `Status:` values (Draft / Approved / In progress / Shipped), `Approved by / on:`, `Source:`.
- Code identifiers, branch names, commit messages: English. UI metinleri Türkçe.
- Agent messages (handoff summaries, refusals, `Next:` lines): chat language; command names, file
  paths and protocol fields verbatim.

## Language & framework versions
- Python **3.13** (proje içi sanal ortam: `.venv`). Kurulum:
  `python -m venv .venv` ve ardından `.venv/Scripts/python -m pip install -r requirements-dev.txt`
  (Linux/macOS'ta `.venv/bin/python`).
- Çalışma zamanı bağımlılıkları `requirements.txt`, geliştirme bağımlılıkları `requirements-dev.txt`
  içinde durur ve **sürümleri sabitlenir** (`==`). Bugün: Flask 3.1.3 · pytest 9.1.1 · ruff 0.17.2.

## Naming
- PEP 8: modül/fonksiyon/değişken `snake_case`, sınıf `PascalCase`, sabit `UPPER_SNAKE`.
- Kod tanımlayıcıları İngilizce ve `docs/domain.md` sözlüğüyle birebir eşleşir
  (`entitlement`, `remaining`, `LeaveRequest`…). Durum değerleri ASCII Türkçe veridir
  (`Beklemede`/`Onaylandi`/`Reddedildi`); kodda sabit olarak tanımlanır, string olarak dağıtılmaz.
- Testler: `tests/test_<konu>.py`, fonksiyonlar `test_<davranış>`. Branch adları için bkz. `docs/git.md`.

## Error handling
- Hata yutmak yasak: `except Exception: return True`, boş `except` ve "loglanacak" yorumu kabul edilmez.
- İş kuralı ihlalinde domain **tipli bir istisna** fırlatır (ör. `InsufficientBalance`,
  `EmployeeNotFound`, `InvalidDateRange`). Başarısızlığı `True/False` dönüşüyle bildirmez.
- Web katmanı domain istisnasını yakalar ve kullanıcıya anlaşılır bir Türkçe mesaj gösterir
  (ör. "Kalan izin bakiyeniz yetersiz."). Beklenmeyen hata `logging` ile stack trace'iyle loglanır;
  kullanıcıya genel bir mesaj gider.
- Kullanıcıya asla sızmaz: stack trace, istisna metni, iç hata kodları ("ERR-412 NullReferenceGibi"),
  dahili telefon numaraları, dosya yolları.

## Data rules
- Tarihler `datetime.date`, zaman damgaları timezone-aware `datetime`; saat dilimi `Europe/Istanbul`.
- "Bugün" tek bir saat kaynağından gelir ve enjekte edilir (parametre ya da clock nesnesi). Domain
  `datetime.now()` / `date.today()` çağırmaz; testler bugünü sabitler.
- İzin günü tam sayıdır (`int`); yarım gün izin yok.
- Kimlikler (`id`) pozitif tam sayıdır ve storage tarafından verilir.

## Enforced by tooling
- **ruff** (`ruff.toml`, kurallar sabit: `E4, E7, E9, F`): sözdizimi hataları, tanımsız isimler,
  kullanılmayan import ve değişkenler. Kural seti yalnızca bir spec/plan ile genişletilir.
- **pytest**: tüm test seti `./scripts/check` içinde çalışır.
- **exec-bits** (`tools/check_exec_bits.py`, spec 0002): git'te izlenen ve `#!` ile başlayan her dosya
  `100755` olmalı (`adapters/` şablonları hariç). Windows'ta yeni bir script eklerken
  `git add --chmod=+x <dosya>` kullanın. Proje kökünde `.git` olduğu hâlde git depoyu okuyamıyorsa
  (ör. dubious ownership) bu bir atlama değil, `exec-bits` adımında kırmızıdır (spec 0003).
- **Proje araçları** `tools/` altında durur. `scripts/` altındaki ANEW core dosyaları (`doctor`,
  `check`, `residue`, `selftest`, `init`) yerelde değiştirilmez; `scripts/check.conf` projeye aittir
  ve proje adımları, ANEW yükseltmelerinde çakışma olmasın diye, onun üzerinden bağlanır.
- Mimari yasaklar (spec 0006) ve domain'in gerçek saati okumaması (spec 0007)
  `tests/test_architecture.py` ile zorlanır.
- Henüz araçla zorlanmayan, review'da kontrol edilen kurallar: hata yönetimi, mypy (refactor
  sonrası).
