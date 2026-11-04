# Spec 0009 — logging-config (mini)

- Status: Shipped
- Mode: lite
- Plan: `specs/plans/0009-plan.md`
- Source: #21
- Design: — (kullanıcı arayüzü yok; değişiklik yalnızca sürecin log çıktısında)
- Supersedes: — (shipped bir kriter değişmiyor; 0008/CB-5 aşağıda korunan davranış olarak duruyor)

## Intent
Spec 0008'den beri beklenmeyen hatalar loglanıyor, ama uygulamada log yapılandırması yok. Kayıt
stderr'e zaman damgası, seviye ve kaynak bilgisi olmadan düşüyor ve seviye ayarlanamıyor.
İşletmede bir hatanın ne zaman ve nerede olduğu bu çıktıdan okunamıyor.

Bu iş, uygulamanın ürettiği her log satırını okunur bir biçime sokar ve log seviyesinin bir ortam
değişkeniyle ayarlanmasını sağlar. Hedef stderr olarak kalır; çıktıyı süreç yöneticisi ya da
konteyner toplar.

Bugünkü davranış (gözlem, 2026-11-04, `main` @ `9cad237`): beklenmeyen hatada stderr'e yalnızca
`izin talebi kaydedilemedi` satırı ve ardından stack trace düşüyor; zaman, seviye ve logger adı yok.

## Changed behavior
"Log satırı", uygulamanın (kendi kodu, Flask ve Werkzeug) `logging` ile ürettiği bir kayıttır.
- [x] CB-1 — **Biçim:** her log satırı sırasıyla zaman damgasını (yerel saatle tarih ve saat), seviyeyi
  (`INFO`, `ERROR` …), logger adını (ör. `web.routes`) ve mesajı içerir. Stack trace taşıyan bir
  kayıtta stack trace bu satırın hemen altında gelir.
- [x] CB-2 — **Hedef:** log satırları stderr'e yazılır. stdout'a log yazılmaz; diskte log dosyası
  oluşmaz.
- [x] CB-3 — **Seviye ayarı:** seviye `LOG_LEVEL` ortam değişkeniyle seçilir (`DEBUG`, `INFO`,
  `WARNING`, `ERROR`, `CRITICAL`; büyük/küçük harf fark etmez). Değişken yoksa ya da boşsa seviye
  `INFO`'dur. Seçilen seviyenin altındaki kayıtlar yazılmaz. Örnek: `LOG_LEVEL=ERROR` iken
  Werkzeug'un istek satırları (INFO) yazılmaz, beklenmeyen hata (ERROR) yazılır.
- [x] CB-4 — **Geçersiz değer:** `LOG_LEVEL` tanınmayan bir değer taşıyorsa (ör. `verbose`)
  uygulama yine başlar, seviye `INFO` olur ve stderr'e bir kez, geçersiz değeri ve kullanılan
  seviyeyi adıyla söyleyen bir `WARNING` satırı yazılır.
- [x] CB-5 — **Tek kez:** her olay tam olarak bir log satırı (ve varsa stack trace'i) üretir; aynı
  kayıt iki farklı biçimde ya da iki kez yazılmaz. Werkzeug'un istek satırları da CB-1 biçimindedir.
- [x] CB-6 — **Başlatma yolu:** yapılandırma, uygulama ister `python app.py` ile ister bir WSGI
  sunucusunun uygulamayı yüklemesiyle başlatılsın, aynı biçimde geçerli olur.

## Preserved behavior
- [x] PB-1 — **0008/CB-5 aynen:** beklenmeyen hatada yanıt 500 ve genel mesajdır
  ("Talep kaydedilemedi. Lütfen daha sonra tekrar deneyin."); istisna metni ve stack trace sayfaya
  sızmaz; stack trace logda (artık CB-1 biçiminde) yer alır.
- [x] PB-2 — **Debug kapalı:** `LOG_LEVEL=DEBUG` dahil hiçbir `LOG_LEVEL` değeri Werkzeug
  debugger'ını ya da Flask debug modunu açmaz (`docs/security.md`).
- [x] PB-3 — **Ekranlar aynı:** GET `/`, `/requests`, `/new` ve geçerli/geçersiz talep POST'larının
  yanıtları (durum kodu ve gövde) `main` ile aynıdır.
- [x] PB-4 — **Testler:** mevcut testler değişmeden geçer; `./scripts/check` (normal ve ters sıra)
  yeşil. Test koşusu repoda log dosyası bırakmaz (`docs/testing.md`).

## Out of scope
- Log dosyasına yazma, döndürme (rotation).
- Yapılandırılmış (JSON) log; düz metin yeterli (#21 kararı).
- Yeni log çağrıları eklemek (ör. her talebi INFO ile loglamak); yalnızca var olan kayıtların
  biçimi ve seviyesi ele alınır.
- Debug modunu açma yolu (`FLASK_DEBUG`); dokunulmaz.
- İstek kimliği (request id), kullanıcı bilgisi gibi bağlam alanları.

## Verification (VERIFY, 2026-11-04, HEAD `8467a82`, bağımsız QA subagent; fix-2 sonrası CI ile @ `4b0edc2`)
Mutantlar ve karşılaştırmalar repo dışında, scratch'teki `git archive` kopyalarında yapıldı;
hiçbiri commit'lenmedi. Gerçek süreç `python app.py` ile koşuldu (`Debug mode: off`).

| Kriter | Kanıt | Durum |
|---|---|---|
| CB-1 | `test_log_line_has_time_level_logger_and_message[import\|main]`. Gerçek süreç (bozuk storage): `2026-11-04 17:26:55,019 ERROR web.routes: izin talebi kaydedilemedi`, ardından `Traceback …`. `main`'de aynı olay öneksizdi. Mutantlar M04 (format) ve M05 (datefmt) yakalandı | Pass |
| CB-2 | `test_logs_go_to_stderr_only`. Gerçek süreçte stdout'ta yalnızca Flask banner'ı var; `*.log` dosyası 0. Mutant M03 (`stdout`) yakalandı | Pass |
| CB-3 | `test_level_from_env`: 8 değer × 2 giriş; DEBUG kaydı yalnızca `debug`'da (fix-2, G-1). Gerçek süreç: `ERROR`/`WARNING` iken istek satırları ve "Running on" gizli, `DEBUG` iken DEBUG kaydı görünür. Mutantlar M01, M07, M08, M09, M10 (fix-2 sonrası) ve M17 yakalandı | Pass |
| CB-4 | `test_invalid_level_falls_back_to_info_with_one_warning[verbose\|WARN\|10 × import\|main]` (fix-2, G-2). Gerçek süreç: `WARNING app: LOG_LEVEL='verbose' tanınmıyor; seviye INFO kullanılıyor`, bir kez. Mutantlar M06, M13 (fix-2 sonrası), M14 ve M16 yakalandı | Pass |
| CB-5 | `test_each_event_is_logged_once[import\|main]`. Gerçek süreç: her istek için tek bir `INFO werkzeug:` satırı; hata kaydı tek. Kökte tek bir stderr handler var; `app.logger` ve `werkzeug` handler'sız | Pass |
| CB-6 | CB-1, CB-3, CB-4 ve CB-5 testleri `import`/`main` ile. WSGI tarzı yükleme (`import app` ile `make_server`) gözlemlendi. Mutant M15 yakalandı | Pass |
| PB-1 | `tests/test_request_errors.py::test_screen_unexpected_error_is_logged_not_shown` değişmedi ve yeşil. Gerçek süreç: 500 ve genel mesaj; gövdede sızıntı yok. 500 gövdesi `main` ile bayt bayt aynı | Pass |
| PB-2 | `test_log_level_debug_does_not_enable_debug_mode` ve mevcut güvenlik testi yeşil. Gerçek süreç: `LOG_LEVEL=DEBUG` dahil her değerde `Debug mode: off` | Pass |
| PB-3 | `main` ve HEAD: 3 GET, 6 POST ve sonraki listeler; durum, Location, Content-Type ve gövde sha256 → `all identical: True cases: 21` | Pass |
| PB-4 | Mevcut test assert'leri değişmedi. `tests/conftest.py`'ye yalnızca `LOG_LEVEL` izolasyonu eklendi (review F-1, rule 5'e uygun, VERIFY N-3). `main`'in 83 testi HEAD kodunda `83 passed, 5 skipped`. Full, ters sıra ve `LOG_LEVEL=CRITICAL` check'leri yeşil @ `4b0edc2`: `113 passed, 5 skipped`. Doctor --strict `0 fail, 0 warn`. Selftest 82/82. Residue `RESIDUE CLEAN` @ `8467a82`; `4b0edc2`'de yalnızca Windows sistem servisleri kaldı (kalan `python.exe` yok; N-5). PR #24: run 41854223110 (pull_request) ve 41854004983 (push), ikisi de `4b0edc2`: `117 passed, 1 skipped`, `CHECK GREEN (full)`; doctor 0 fail, 0 warn; selftest 82/82 | Pass |

Kayıtlar:
- Test sayısı 83 → 113 (Windows) / 87 → 117 (Linux CI): 30 yeni test, tümü `tests/test_logging_config.py`'de.
- Mutantlar: 17 mutantın 13'ü VERIFY'da yakalandı. Sağ kalan M02, M10 ve M13 fix-2 ile yakalanır
  hâle geldi (G-3, G-1, G-2). M12 (`daemon`) eşdeğer: yalnızca hata yolunda fark ediyor.
- Review round 1: F-1…F-4 real (fix-1). VERIFY:
  - G-1, G-2 ve G-3 real (fix-2).
  - G-4: CI SHA'sı HEAD ile eşleşti (`4b0edc2`).
  - N-4: README'ye eklendi.
  - N-1, N-2, N-5 ve N-6 kabul edildi.
- UI yok. Kanıt gerçek sürecin stderr ve stdout çıktısı; ekranların yanıtları `main` ile aynı (PB-3).
- Linux CI `117 passed, 1 skipped`, Windows `113 passed, 5 skipped` (exec-bits testleri NTFS'te
  atlanıyor).

## Definition of Done
- [x] `scripts/check` green
- [x] Independent review done; real findings fixed, noise rejected with written rationale
- [x] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI yok: kanıt gerçek süreçten
  alınmış stderr çıktısıdır)
- [x] Spec moved to `specs/done/` (immutable there)

## Kararlar (spec onayında, İbrahim Gürhan, 2026-11-04)
- **S-1:** Ortam değişkeninin adı `LOG_LEVEL`. `FLASK_` öneki yok, böylece debug ile karışmaz.
- **S-2:** Geçersiz değerde uygulama başlar, seviye `INFO` olur ve bir `WARNING` yazılır (CB-4).
- **S-3:** Werkzeug'un istek satırları da aynı biçime girer (CB-5).
- **S-4:** Yapılandırma hem `python app.py` ile hem bir WSGI sunucusuyla yüklemede geçerlidir (CB-6).
- **S-5:** Zaman damgası yerel saatle yazılır, saat dilimi belirtilmez (CB-1). Gerekirse sonra
  değiştirilir.
- **S-6:** Yapılandırma, testlerin log yakalamasını (`caplog`) bozmaz. Bu, plana açık bir koşul
  olarak yazılır (PB-4).

## Scorecard (fill at ship — honest numbers make the process improvable)
| Metric | Value |
|---|---|
| Spec revisions | 0 (S-1…S-6 onay öncesi taslağa işlendi) |
| Plan amendments | 2 R-07 kaydı: BUILD'de D-1/D-2; review F-1/F-3 ile plan dışı dosyalar (`tests/conftest.py`, `docs/testing.md`, `scripts/check.conf`) |
| Fix rounds | 2 (fix-1 review F-1…F-4, fix-2 VERIFY G-1…G-3 ve N-4; production kodu değişmedi) |
| Review findings: real / noise | 4 / 0 (round 1); VERIFY G-1…G-3 real, G-4 ship'te kapandı |
| Regressions introduced | 0 (F-1'in ortama bağlı test kırılması merge öncesi yakalandı) |
| Bugs escaped to production | 0 (henüz yayında değil) |
