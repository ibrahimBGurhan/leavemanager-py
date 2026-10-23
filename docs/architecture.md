# Architecture

> Bootstrap'te (2026-10-23) karara bağlandı. **Hedef** mimariyi ve **bugünkü durumu** ayrı ayrı
> anlatır; aradaki fark `/refactor` işleriyle kapatılır, kendiliğinden değil.

## System overview
LeaveManager, IK ve personelin yıllık izin taleplerini ve bakiyelerini takip eden bir Flask web
uygulamasıdır. Stil: **modüler monolit, üç katman** — `web → domain → storage`. Gerekçe: iş
kuralları (kıdem, hak, bakiye) Flask olmadan test edilebilmeli ve 2016'dan beri bekleyen kalıcı
veritabanı geçişi yalnızca storage katmanını değiştirmeli.

**Bugünkü durum:** her şey tek dosyada (`app.py`). `Db` bellekte tutuluyor ve her başlatmada
`seed()` ile sıfırlanıyor. `LeaveService` iş kurallarının yanında HTML de üretiyor
(`status_badge`), route'lar HTML'i string birleştirerek kuruyor. Katmanlara ayrılma ayrı bir
refactor spec'iyle yapılır.

## Modules / components and ownership

| Module | Single responsibility | Owns |
|---|---|---|
| `web` | HTTP: route'lar, form girdisinin ayrıştırılması/doğrulanması, Jinja şablonları, kullanıcı mesajları | Sunum (HTML, durum rozeti renkleri, Türkçe UI metinleri) |
| `domain` | İş kuralları: kıdem, hak, kullanılan, kalan, talep oluşturma ve durum geçişleri | Kural ve kavramlar (`docs/domain.md`); tipli domain istisnaları |
| `storage` | Kalıcılık: repository arayüzü ve uygulaması (bugün bellek, sonra SQL) | Personel ve izin talebi kayıtları |

## Communication rules
- `web` yalnızca `domain`'in public servis fonksiyonlarını çağırır.
- `domain`, `storage`'a yalnızca repository arayüzü üzerinden erişir; arayüz dışarıdan enjekte edilir.
- "Bugün" (saat) de dışarıdan enjekte edilir; domain `datetime.now()` çağırmaz (`docs/conventions.md`).
- Olay/mesaj altyapısı yok; tüm çağrılar senkron ve süreç içi.

## Forbidden dependencies (make them testable)
Bir pytest mimari testi (import taraması) bunları doğrular; katmanlar ayrıldığında eklenir.
1. `domain` paketi `flask`, `werkzeug` veya `jinja2` import etmez.
2. `domain` HTML üretmez (HTML etiketi içeren string döndürmez; sunum `web`'e aittir).
3. `web`, `storage`'a doğrudan erişmez — her zaman `domain` üzerinden gider.
4. SQL (ham sorgu veya ORM oturumu) yalnızca `storage` içinde bulunur.

## Deliberately out of scope
- Bordro/muhasebe entegrasyonu, e-posta/SMS bildirimleri, mobil uygulama.
- Birden çok şirket/kiracı (multi-tenant).
- İzin türleri (mazeret, ücretsiz, doğum vb.) — yalnızca yıllık ücretli izin. Gerekirse yeni spec.
- Not: kimlik doğrulama / yetkilendirme kapsam *dışı değil*; planlanmış ayrı bir feature
  (`docs/security.md`).
