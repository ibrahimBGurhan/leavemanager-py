# ADR 0002 — Kimlik doğrulama: uygulama içi kullanıcı ve şifre (yeni paket yok)

- Status: Accepted
- Date: 2026-11-05

## Context
LeaveManager'da bugün kimlik doğrulama yok: herkes her şeyi görür, herkes adına talep girer ve
bekleyen her talebi onaylayıp reddedebilir (`docs/security.md`, AuthN / AuthZ; spec 0010'da
bilinçli kabul edilen risk). Hedef, varsayılan olarak kapalı bir uygulama ve üç rol: **Personel**
(kendi bakiyesi ve talepleri), **Yönetici** (biriminin talepleri), **IK** (tüm personel). Rollerin
ve yetkinin önünde, kullanıcının kim olduğunu nasıl bildiğimiz kararı var; bu ADR o kararı verir.

Kısıtlar ve bağlam:
- İç ağda çalışan, az kullanıcılı bir İK uygulaması; küçük ekip, düşük işletim bütçesi.
- Zemin hazır: kalıcı depo (ADR-0001, SQLite, `storage` katmanı), imzalı Flask oturumu
  (`SECRET_KEY` ortamdan), CSRF koruması (spec 0011), `HttpOnly` + `SameSite=Lax` oturum çerezi.
- Her yeni paket insan onayı ister (`docs/security.md`, Dependencies).
- Şirkette kullanılabilir bir kurumsal kimlik sistemi (Active Directory / LDAP, SSO) olup
  olmadığı **bilinmiyor**. Karar bu belirsizliğe göre verildi.
- Bugün uygulama iç ağda **HTTP** ile çalışıyor (spec 0011'de `Secure` çerez zorlanmadı). Şifre
  taşıyan bir giriş formu bu durumu değiştirir: HTTP'de şifre ağda açık metin gider.

## Decision
Kimlik doğrulama **uygulama içinde, kullanıcı ve şifre ile** yapılır; yeni paket eklenmez:
şifre özeti Werkzeug `generate_password_hash` / `check_password_hash` (varsayılan scrypt), oturum
mevcut Flask oturumu, form koruması mevcut CSRF; kullanıcılar ve rolleri SQLite deposunda
(ADR-0001), depo sözleşmesinin (spec 0016) genişletilmesiyle tutulur. Ayrıntılar (karar: İbrahim
Gürhan, 2026-11-05):
- **D-1 Giriş kimliği:** e-posta adresi (ileride AD / SSO'ya geçişte kullanıcı eşleştirmesini
  kolaylaştırır).
- **D-2 İlk IK hesabı:** komut satırı aracıyla oluşturulur; şifre ekranda gösterilmeden sorulur.
  Kodda, yapılandırmada ya da demo verisinde **varsayılan şifre yoktur**.
- **D-3 Şifre kuralı:** en az 12 karakter; karmaşıklık (büyük harf, rakam, sembol) zorunluluğu
  yok (NIST SP 800-63B).
- **D-4 Kaba kuvvete karşı:** aynı hesapta 5 başarısız denemeden sonra 15 dakika kilit. Her
  başarısız deneme log'a WARNING olarak yazılır; şifre hiçbir log'a yazılmaz. Giriş hatası
  iletisi geneldir: hesabın var olup olmadığını ya da hangi alanın yanlış olduğunu söylemez.
- **D-5 Oturum:** en fazla 8 saat (bir iş günü); çıkış düğmesi; başarılı girişte önceki oturum
  verisi temizlenir (oturum sabitleme saldırısına karşı).
- **D-6 HTTPS dağıtım şartı:** giriş sistemi **yayına yalnız HTTPS ile çıkar** (ters vekil
  sunucu). `SESSION_COOKIE_SECURE` ortamdan açılabilir olur; HTTPS'li dağıtımda açılır.

Uygulama ayrı spec'lerle yapılır (giriş / çıkış, ardından roller ve yetki); bu ADR kod içermez.

## Consequences
Kazandıklarımız:
- Yeni paket yok: lisans, bakım ve CVE takibi yükü artmaz. Werkzeug zaten Flask'ın bağımlılığı.
- Mevcut altyapı yeniden kullanılır: Flask oturumu, CSRF koruması, çerez ayarları, SQLite deposu
  ve depo sözleşme testleri.
- Tamamen bizim kontrolümüzde ve testlerde kolay kurulur: dış bir kimlik sunucusu gerekmez, test
  ortamı bugünkü gibi bellek deposuyla çalışır.
- Kurumsal bir sistemin varlığını beklemeden "varsayılan kapalı" hedefine ilerlenir; uygulamanın
  bugünkü en büyük güvenlik açığı (herkesin her şeyi yapabilmesi) kapanabilir.
- E-posta ile giriş, ileride AD / SSO'ya geçişte mevcut kullanıcıları ve rollerini eşleştirmeyi
  kolaylaştırır.

Ödediklerimiz:
- **Şifre yaşam döngüsü bizim işimiz:** şifre değiştirme, unutulan şifre (bugün IK sıfırlar; e-posta
  ile sıfırlama yok), kilit açma ve hesap kapatma kendimiz yazılır ve test edilir.
- **Kullanıcılar bir şifre daha ezberler;** işten ayrılan kişinin hesabı merkezi olarak değil, IK
  tarafından uygulamada kapatılır. Unutulursa erişim sürer.
- **Kilit kötüye kullanılabilir:** başkasının e-postasıyla 5 yanlış deneme o hesabı 15 dakika
  kilitler. Az kullanıcılı bir iç uygulamada kabul edildi; log'daki WARNING'ler bunu görünür kılar.
- **Kilit sayacı tek süreç varsayımına dayanır** (ADR-0001 ile aynı): birden çok sunucu kopyasında
  sayaç paylaşılmazsa koruma zayıflar.
- **HTTPS bir dağıtım işi:** ters vekil sunucu ve sertifika kurulmadan giriş sistemi yayına
  çıkamaz. Bu, operasyonun (BT) zamanına ve iznine bağlıdır.
- **Oturum imzalı bir çerezde tutulur:** sunucu tarafında tek bir oturumu iptal etmek mümkün
  değildir; zorla çıkış için ya `SECRET_KEY` değiştirilir (herkes çıkar) ya da kullanıcıya bağlı
  bir sürüm alanı eklenir. 8 saatlik süre sınırı bu riski sınırlar.
- **MFA yok:** tek etken şifre. İç ağ ve düşük risk profili için kabul edildi.
- Şifre özeti, giriş denemesi ve kullanıcı verisi KVKK kapsamında korunması gereken veridir;
  veritabanı dosyası ve yedekleri için `docs/security.md` "Veri ve yedekleme" kuralları geçerlidir.

## Alternatives considered
- **Uygulama içi şifre + Flask-Login:** `login_required`, kullanıcı yükleme ve "beni hatırla"
  hazır gelir; olgun, MIT lisanslı bir paket. Kaybetti çünkü yeni bir bağımlılık getiriyor ve bu
  boyutta bir uygulamada aynı işi birkaç satırlık bir decorator ve oturumdaki kullanıcı numarası
  görüyor. Oturum ve yetki kodu karmaşıklaşırsa ilk aday bu.
- **Active Directory / LDAP (`ldap3`):** tek şifre, işten ayrılan kişinin erişimi merkezden kapanır,
  şifre politikası BT'nin. Kaybetti çünkü böyle bir sistemin varlığı ve erişim izni bilinmiyor; yeni
  bir paket ve zor kurulan bir test ortamı gerektiriyor. Roller yine uygulamada tutulacağından
  geçişte yalnız şifre doğrulaması değişir.
- **SSO / OIDC (Authlib, kurumsal kimlik sağlayıcı):** en iyi kullanıcı deneyimi; MFA ve hesap
  yönetimi kimlik sağlayıcıda. Kaybetti çünkü bir kimlik sağlayıcı ve BT entegrasyonu gerektiriyor;
  bugünkü ölçek ve belirsizlik için fazla.

## Revisit triggers
- Şirket AD / LDAP ya da SSO sağlarsa ya da BT kurumsal kimlik sistemi kullanımını şart koşarsa
  (→ LDAP ya da OIDC; roller uygulamada kalır).
- MFA bir uyum ya da denetim şartı olursa.
- Kullanıcı sayısı ya da şifre sıfırlama / kilit açma yükü IK için belirgin bir iş haline gelirse.
- Oturum ve yetki kodu karmaşıklaşırsa (→ Flask-Login).
- HTTPS sağlanamazsa: giriş sistemi yayına çıkmaz; karar yeniden konuşulur.
- Uygulama birden çok sunucuda çalışmaya başlarsa (kilit sayacı ve oturum iptali; ADR-0001 ile
  birlikte açılır).
