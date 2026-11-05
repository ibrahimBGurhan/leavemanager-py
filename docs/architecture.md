# Architecture

> Bootstrap'te (2026-10-23) karara bağlandı. **Hedef** mimariyi ve **bugünkü durumu** ayrı ayrı
> anlatır; aradaki fark `/refactor` işleriyle kapatılır, kendiliğinden değil.

## System overview
LeaveManager, IK ve personelin yıllık izin taleplerini ve bakiyelerini takip eden bir Flask web
uygulamasıdır. Stil: **modüler monolit, üç katman** — `web → domain → storage`. Gerekçe: iş
kuralları (kıdem, hak, bakiye) Flask olmadan test edilebilmeli ve 2016'dan beri bekleyen kalıcı
veritabanı geçişi yalnızca storage katmanını değiştirmeli.

**Bugünkü durum (spec 0006):** üç katman ayrı paketlerde:
- **`storage/memory.py`:** `MemoryStorage` kayıtları bellekte tutar ve her başlatmada açılış
  verisiyle kurulur.
- **`domain/leave_service.py`:** `LeaveService` saati ve depoyu kurulumda parametre olarak alır.
- **`web/routes.py`:** route'lar, sayfa ve durum rozeti burada.
- **`app.py`:** yalnızca kurulum noktası (composition root). Flask uygulamasını, saati
  (`SystemClock`), depoyu ve servisi kurup birbirine bağlar; `app`, `clock`, `storage`, `svc`
  adları testlerin bağlantı noktalarıdır (spec 0005).
  Log yapılandırması da burada kurulur (spec 0009); katmanlar yalnızca
  `logging.getLogger(__name__)` kullanır.

Hedeften kalan farklar:
- Route'lar HTML'i hâlâ string birleştirerek kuruyor (Jinja şablonu yok).

Bu ayrı bir işle kapatılır. Depo arayüzü artık yazılı bir sözleşmedir (spec 0016):
`storage/contract.py` (`LeaveStorage`); her depo uygulaması `tests/test_storage_contract.py`'den
geçer. Kalıcı depo SQLite olacak (ADR-0001).

## Modules / components and ownership

| Module | Single responsibility | Owns |
|---|---|---|
| `web` | HTTP: route'lar, form girdisinin ayrıştırılması/doğrulanması, Jinja şablonları, kullanıcı mesajları | Sunum (HTML, durum rozeti renkleri, Türkçe UI metinleri) |
| `domain` | İş kuralları: kıdem, hak, kullanılan, kalan, talep oluşturma ve durum geçişleri | Kural ve kavramlar (`docs/domain.md`); tipli domain istisnaları |
| `storage` | Kalıcılık: repository arayüzü ve uygulaması (bugün bellek; hedef SQLite, [ADR-0001](decisions/0001-kalicilik-sqlite.md)) | Personel ve izin talebi kayıtları |

## Communication rules
- `web` yalnızca `domain`'in public servis fonksiyonlarını çağırır.
- `domain`, `storage`'a yalnızca repository arayüzü üzerinden erişir; arayüz dışarıdan enjekte edilir.
- "Bugün" (saat) de dışarıdan enjekte edilir; domain `datetime.now()` çağırmaz (`docs/conventions.md`).
- Olay/mesaj altyapısı yok; tüm çağrılar senkron ve süreç içi.

## Forbidden dependencies (make them testable)
`tests/test_architecture.py` (import, string ve öznitelik taraması, `ast` ile) bunları doğrular
(kural 1–4 spec 0006, kural 5 spec 0007). Kural 3 ve 4 import düzeyinde sınanır; özel alan erişimi
(ör. `svc._storage`) ve ham SQL string'leri review'da kontrol edilir. Kural 5 de yazılı erişime
bakar; dinamik erişim (`getattr(date, "today")`, `__import__`), atamayla yeniden bağlanan ad
(`d = date; d.today()`), aynı adın dosyada birden çok `datetime` import'una bağlanması ve saati
okuyan bir fonksiyonun domain dışından import edilmesi review'da kontrol edilir.
1. `domain` paketi `flask`, `werkzeug` veya `jinja2` import etmez.
2. `domain` HTML üretmez (HTML etiketi içeren string döndürmez; sunum `web`'e aittir).
3. `web`, `storage`'a doğrudan erişmez — her zaman `domain` üzerinden gider.
4. SQL (ham sorgu veya ORM oturumu) yalnızca `storage` içinde bulunur.
5. `domain` gerçek saati okumaz (`date.today`, `datetime.now`…); saat dışarıdan verilir.

## Deliberately out of scope
- Bordro/muhasebe entegrasyonu, e-posta/SMS bildirimleri, mobil uygulama.
- Birden çok şirket/kiracı (multi-tenant).
- İzin türleri (mazeret, ücretsiz, doğum vb.) — yalnızca yıllık ücretli izin. Gerekirse yeni spec.
- Not: kimlik doğrulama / yetkilendirme kapsam *dışı değil*; planlanmış ayrı bir feature
  (`docs/security.md`).
