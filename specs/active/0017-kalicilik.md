# Spec 0017 — kalicilik

- Status: Approved
- Mode: lite
- Plan: `specs/plans/0017-plan.md`
- Source: ADR-0001 (`docs/decisions/0001-kalicilik-sqlite.md`), `docs/domain.md` OD-8; kararlar
  `specs/done/0016-refactor-depo-sozlesmesi.md` "0017 için onaylanan kararlar" (K-1…K-8)
- Design: — (yeni ekran yok; boş durumlar aşağıda)

## Intent
LeaveManager'ın verisi bugün her yeniden başlatmada kayboluyor: girilen ve onaylanan talepler
gidiyor, uygulama açılış (demo) verisine dönüyor. Bu iş ADR-0001'i uygular: personel ve talepler
bir SQLite dosyasında saklanır ve yeniden başlatmada korunur. Üretim boş bir veritabanıyla başlar;
demo verisi yalnız açıkça istendiğinde yüklenir. Başarı: bir talep girilip onaylandıktan sonra
uygulama yeniden başlatıldığında talep, durumu ve bakiyeler aynen yerindedir.

Bilinçli olarak yapılmayanlar: personel ekleme ekranı (K-1; giriş sisteminden sonra ayrı spec),
giriş sistemi, yedekleme otomasyonu (K-7), bellekteki verinin taşınması (K-8).

## Requirements
- **R-1 Kalıcılık:** Personel ve talep kayıtları ile talep durumları uygulama yeniden
  başlatıldığında korunur. Kayıt alanları ve türleri aynen geri gelir (tarihler tarih, Türkçe
  karakterler bozulmadan).
- **R-2 Veritabanı yeri:** Dosya yolu `DATABASE_PATH` ortam değişkeninden okunur; tanımlı değilse
  uygulama klasöründe `instance/leavemanager.db`. Klasör yoksa oluşturulur (K-5).
- **R-3 Açılamayan veritabanı (K-5):** Dosya oluşturulamıyor ya da yazılamıyorsa uygulama açılmaz
  ve log'a yolu ve nedeni söyleyen açık bir hata yazılır; veri belleğe sessizce geri dönmez.
  Dosyanın şema sürümü uygulamanın bildiğinden yeniyse de uygulama açılmaz ve log'a iki sürümü
  söyleyen bir hata yazılır; dosyaya dokunulmaz (S-4).
- **R-4 Boş başlangıç (K-1, K-2):** Yeni bir veritabanı boş başlar. Boş verideki ekranlar mevcut
  davranışla tutarlıdır; yeni mesaj ya da ekran yoktur.
- **R-5 Demo verisi (K-3):** `SEED_DEMO_DATA=1` verildiğinde açılış verisi (5 personel, 8 talep)
  **yalnız veritabanı boşsa** (hiç personel ve hiç talep yoksa, S-3) yüklenir; dolu veritabanında hiçbir kayıt ezilmez ya da çoğaltılmaz.
  Başka herhangi bir değer ya da tanımsız → yüklenmez.
- **R-6 Talep numarası (K-4):** Yeni talep numarası veritabanındaki en büyük numaranın bir
  fazlasından devam eder; yeniden başlatmadan sonra da numara tekrar kullanılmaz.
- **R-7 Sözleşme:** SQLite deposu, `MemoryStorage` ile aynı sözleşmeyi sağlar ve
  `tests/test_storage_contract.py`'den testler değişmeden geçer (spec 0016).
- **R-8 Testler (K-6):** Mevcut testler bellek deposuyla, değişmeden çalışır; testler ve
  `scripts/check` repoda veritabanı dosyası bırakmaz (ANEW-0007, `docs/testing.md`).
- **R-9 Güvenlik:** Kullanıcı girdisi (ör. neden alanı) veritabanına veri olarak yazılır, sorgu
  metnine karışmaz; `'`, `;`, `--` içeren metin aynen saklanır ve geri gelir. Veritabanı dosyası
  KVKK kapsamında kişisel veri taşır (`docs/security.md`); repoya girmez.
- **R-10 Belgeler (K-7):** `.env.example` (`DATABASE_PATH`, `SEED_DEMO_DATA`), `.gitignore`
  (`instance/`), yedekleme yöntemi ve KVKK notu, `docs/architecture.md` bugünkü durum.

## User experience
- **Flow:** değişmez. Kullanıcı aynı üç ekranı kullanır; fark, verinin yeniden başlatmada kalması.
- **States:**
  - *Boş veritabanı — ana sayfa:* sayaçlar "Bekleyen: 0", "Onaylanan: 0", "Reddedilen: 0"; bakiye
    tablosunda yalnız başlık satırı.
  - *Boş veritabanı — Talepler:* tabloda yalnız başlık satırı.
  - *Boş veritabanı — Yeni Talep:* form görünür, personel listesi boş; gönderilirse
    "Seçilen personel bulunamadı." (mevcut mesaj), kayıt oluşmaz.
  - *Dolu veritabanı:* bugünkü ekranlar, kalıcı veriyle.
  - *Açılamayan veritabanı:* uygulama başlamaz (ekran yok; operatör log'u görür).
- **Design reference:** none — the flow above is the design.
- **Accessibility:** değişmez.

## Constraints & out of scope
- **Kısıtlar:** Yeni çalışma zamanı bağımlılığı yok (standart kütüphane `sqlite3`, ADR-0001).
  SQL yalnız `storage` içinde (mimari kural 4, `tests/test_architecture.py`). Tek sunucu, tek kopya
  varsayımı (ADR-0001). WAL modu ve `PRAGMA user_version` ile şema sürümü (ADR-0001).
- **Kapsam dışı:** personel ekleme / düzenleme ekranı ve içe aktarma (K-1); giriş sistemi ve
  kullanıcı tabloları; yedekleme otomasyonu (K-7); bellek verisinin taşınması (K-8); birden çok
  sunucu; şema geçiş aracı (Alembic).
- **Split:** spec 0016 (sözleşme) ile bölündü; bu spec tek yetenek: "veri kalıcı".

## Hasım okur taraması (onaylı)
- **S-1 Testlerin deposu:** AC-9 yeter; plan, korunan bir test altyapısı satırının değişmesini
  gerektirirse adıyla listeleyip onaya sunar.
- **S-2 Yeniden başlatma:** testlerde aynı dosyaya yeni depo / uygulama örneği; gerçek süreç
  yeniden başlatması VERIFY'da gözlenir.
- **S-3 "Boş":** hiç personel ve hiç talep yok; tek kayıt varsa demo verisi yüklenmez.
- **S-4 Daha yeni şema:** uygulama açılmaz, ERROR iki sürümü söyler, dosyaya dokunulmaz.
- **S-5 Boyut:** 10 AC, tek yetenek; bölme yok.

Spec onayı: İbrahim Gürhan, 2026-11-05 (K-1…K-8 0016'da; S-1…S-5 önerildiği gibi).

## Acceptance criteria
Örneklerde açılış verisi = 0016'daki demo verisi (5 personel, 8 talep, en büyük talep numarası 8).
- [ ] AC-1 — **Yeniden başlatmada korunur (R-1):** Demo verili bir veritabanında Mehmet Demir için
  16–18 Kasım 2026 talebi girilir (#9) ve #2 onaylanır; aynı dosyayla uygulama yeniden
  başlatıldığında #9 `Beklemede`, #2 `Onaylandi` görünür; ana sayfa sayaçları ve bakiyeler
  yeniden başlatmadan öncekiyle aynıdır.
- [ ] AC-2 — **Alan ve türler (R-1, R-9):** Saklanıp geri okunan kayıtlarda tarihler tarih
  türündedir; "Şükrü Öztürk" ve "İzin; 'test' -- x" metinleri aynen geri gelir; veritabanında
  başka bir değişiklik olmaz.
- [ ] AC-3 — **Boş başlangıç (R-4):** `SEED_DEMO_DATA` tanımsızken yeni bir veritabanıyla açılan
  uygulamada ana sayfa, Talepler ve Yeni Talep yukarıdaki boş durumları gösterir; Yeni Talep
  gönderimi "Seçilen personel bulunamadı." verir ve kayıt oluşmaz.
- [ ] AC-4 — **Demo verisi yalnız boşsa (R-5):** `SEED_DEMO_DATA=1` ile boş veritabanı 5 personel
  ve 8 talep alır; aynı dosyayla `SEED_DEMO_DATA=1` ile tekrar başlatılınca kayıt sayısı ve
  içerik değişmez (talep durumları dahil); `SEED_DEMO_DATA=0` / `yes` / boş → yüklenmez.
- [ ] AC-5 — **Numara devam eder (R-6):** Demo verili veritabanında yeni talep #9 olur; yeniden
  başlatmadan sonra bir sonraki talep #10 olur.
- [ ] AC-6 — **Varsayılan yer (R-2):** `DATABASE_PATH` tanımsızken veritabanı uygulama
  klasöründeki `instance/leavemanager.db` dosyasıdır; `instance/` yoksa oluşturulur;
  `DATABASE_PATH` verilince o dosya kullanılır (klasörü yoksa oluşturulur).
- [ ] AC-7 — **Açılamayan veritabanı (R-3):** `DATABASE_PATH` yazılamayan bir yeri gösterdiğinde
  uygulama başlamaz (sıfırdan farklı çıkış), log'da yolu ve nedeni içeren bir ERROR satırı vardır;
  bellek deposuyla çalışmaya devam etmez. Şema sürümü uygulamanınkinden yeni bir dosyada da
  uygulama başlamaz, ERROR iki sürümü söyler ve dosya değişmez (S-4).
- [ ] AC-8 — **Sözleşme (R-7):** `tests/test_storage_contract.py` hem bellek hem SQLite deposuyla
  (testler değişmeden, yalnız depo listesine SQLite eklenerek) yeşildir.
- [ ] AC-9 — **Testler temiz (R-8):** Mevcut test dosyaları değişmeden yeşildir (plan, değişmesi
  zorunlu bir test altyapısı satırı bulursa adıyla listeler ve onaya sunar); `scripts/check` full
  sonrası repoda veritabanı dosyası yoktur (`git status` temiz).
- [ ] AC-10 — **Belgeler (R-10):** `.env.example` iki değişkeni açıklar, gerçek değer içermez;
  `.gitignore` `instance/`'ı içerir; yedekleme yöntemi ve KVKK notu yazılıdır;
  `docs/architecture.md` bugünkü durumu SQLite olarak anlatır.

## Definition of Done
- [ ] Every acceptance criterion mapped to proof (test or reproducible observation)
- [ ] `scripts/check` green
- [ ] Independent review done; real findings fixed, noise rejected with written rationale
- [ ] Docs / ADRs updated if behavior or architecture changed
- [ ] Spec moved to `specs/done/` (it becomes immutable there)

## Scorecard (fill at ship — honest numbers make the process improvable)
| Metric | Value |
|---|---|
| Spec revisions | |
| Fix rounds | |
| Review findings: real / noise | |
| Regressions introduced | |
| Bugs escaped to production | |
