# ADR 0001 — Kalıcılık: SQLite, standart kütüphane `sqlite3`, storage katmanının arkasında

- Status: Accepted
- Date: 2026-11-05

## Context
LeaveManager'ın verisi (personel, izin talepleri) bugün bellekte tutuluyor (`storage/memory.py`,
`MemoryStorage`) ve her yeniden başlatmada açılış verisine dönüyor (`docs/domain.md` OD-8; kodda
"sonra SQL'e geçilecek (2016)" notu). Bu, gerçek kullanımın önündeki en büyük engel: onaylanan ve
girilen her talep bir yeniden başlatmada kayboluyor.

Sıradaki büyük iş — giriş sistemi ve roller (`docs/security.md`, AuthN / AuthZ) — kullanıcıların,
şifre özetlerinin ve rollerin kalıcı saklanmasını gerektiriyor; bellekte bir kullanıcı tablosu
anlamsız. Bu yüzden karar şimdi, auth'tan önce veriliyor.

Kısıtlar ve bağlam:
- İç ağda çalışan bir İK uygulaması; birkaç İK kullanıcısı ve personel. Veri hacmi küçük (yılda
  yüzlerce talep), yazma yükü düşük.
- Mimari baştan bu geçiş için kuruldu: `web → domain → storage`; SQL yalnız `storage` içinde
  (`docs/architecture.md` yasak bağımlılık kuralı 4, `tests/test_architecture.py`). Depo arayüzü
  bugün yazılı bir sözleşme değil, ortak metot adları (mimarideki "hedeften kalan fark").
- Her yeni paket insan onayı ister (`docs/security.md`, Dependencies); küçük ekip, düşük işletim
  bütçesi.
- **Varsayım:** uygulama bugün **tek sunucuda, tek kopya** olarak çalışır (İbrahim Gürhan,
  2026-11-05). Bu varsayım bozulursa karar yeniden açılır (Revisit triggers).

## Decision
Kalıcı depo olarak **SQLite**, Python standart kütüphanesindeki **`sqlite3`** ile kullanılır;
SQL yalnız `storage` katmanındaki yeni bir `SqliteStorage` uygulamasında bulunur. Ayrıntılar:
- Depo arayüzü yazılı bir sözleşmeye dönüşür; `MemoryStorage` (hızlı testler için kalır) ve
  `SqliteStorage` aynı **sözleşme testlerinden** geçer.
- Veritabanı dosyasının yolu ortamdan okunur: `DATABASE_PATH` (varsayılan
  `instance/leavemanager.db`); dosya ve `instance/` `.gitignore`'a eklenir.
- WAL modu açılır (okumalar yazmaları beklemez); şema sürümü `PRAGMA user_version` ile tutulur,
  geçişler sürüm numaralı SQL adımlarıdır.
- **Açılış (demo) verisi üretimde yüklenmez:** veritabanı boş başlar; demo verisi yalnız testlerde
  ve `SEED_DEMO_DATA=1` verildiğinde yüklenir.

Uygulama ayrı bir spec ile yapılır (bu ADR kod içermez).

## Consequences
Kazandıklarımız:
- Veri yeniden başlatmada korunur; uygulama ilk kez gerçek kullanıma uygun hale gelir.
- Yeni paket yok: lisans, bakım ve CVE takibi yükü artmaz; kurulum tek dosya.
- Katman sınırı korunur ve sınanır: SQL yalnız `storage`'da (kural 4); domain ve web değişmez.
- Sözleşme testleri depo arayüzünü yazılı hale getirir; ileride başka bir veritabanına geçiş
  aynı testleri geçen yeni bir uygulamayla yapılabilir.
- Testler hızlı kalır: çoğu test `MemoryStorage` ile, SQLite sözleşme testleri geçici dosya ya da
  `:memory:` ile çalışır.
- Auth için zemin hazır: kullanıcı ve oturum verisi aynı depoda tutulabilir.

Ödediklerimiz:
- **Tek sunucu sınırı:** SQLite dosyası birden çok sunucu ya da ağ paylaşımı üzerinden güvenle
  kullanılamaz. Ölçeklemek ya da yüksek erişilebilirlik istemek bu kararı yeniden açar.
- **Yazmalar sıraya girer:** aynı anda tek yazma. Bu hacimde fark edilmez; yoğun eşzamanlı yazma
  olursa darboğaz olur.
- **Şema geçişlerini kendimiz yazarız:** hazır bir araç (Alembic) yok; veri dönüştüren ya da geri
  alınabilir geçişler elle yazılır ve test edilir.
- **Yedekleme ve geri yükleme operasyonun işi:** tek dosya kopyalanarak (çalışırken `sqlite3`
  backup API'siyle) yedeklenir; bunu kurmak ve denemek gerekir. Dosya KVKK kapsamında kişisel veri
  (sağlık bilgisi içerebilen izin nedeni) taşır: dosya izinleri ve yedeklerin korunması gerekir.
- **İki depo uygulaması bakımı:** `MemoryStorage` testler için kaldığından her depo değişikliği
  iki yerde yapılır; sözleşme testleri aralarındaki farkı yakalar ama emek ister.
- Testlerin bir kısmı (`storage.reset()` ile açılış verisine dönen) depo seçimine bağlı; geçiş
  spec'i test bağlantı noktalarını (spec 0005) korumalı.

## Alternatives considered
- **SQLite + SQLAlchemy (ve Alembic):** İleride PostgreSQL / MSSQL'e geçişi ve şema geçişlerini
  kolaylaştırır. Kaybetti çünkü iki yeni bağımlılık (onay, bakım, CVE takibi) ve bu boyutta bir
  uygulama için gereksiz soyutlama ve öğrenme maliyeti getiriyor; geçiş kolaylığını sözleşme
  testleri de büyük ölçüde sağlıyor. Şema geçişleri karmaşıklaşırsa ilk aday bu.
- **PostgreSQL (sunucu):** Eşzamanlı yazma ve çoklu sunucu için doğru araç, kurumsal yedekleme
  araçlarıyla uyumlu. Kaybetti çünkü bir veritabanı sunucusu kurmak ve işletmek, yeni bir sürücü
  paketi (`psycopg`) ve daha ağır test / yerel geliştirme düzeni gerektiriyor; bugünkü hacim ve tek
  sunucu varsayımı bu maliyeti haklı çıkarmıyor.
- **JSON dosyası:** En basit seçenek. Kaybetti çünkü eşzamanlı yazmada bozulmaya açık, sorgu yok,
  kullanıcı ve şifre verisi için uygun değil.

## Revisit triggers
- Uygulamanın birden çok sunucuda ya da container kopyasında çalışması gerekirse (tek sunucu
  varsayımı bozulursa).
- BT politikası merkezi bir veritabanı (MSSQL / PostgreSQL) ya da kurumsal yedekleme şart koşarsa.
- Şema geçişleri karmaşıklaşırsa (veri dönüştürme, geri alma) → SQLAlchemy + Alembic.
- Yazma çakışmaları (`database is locked`) ya da gecikme ölçülebilir bir sorun haline gelirse.
