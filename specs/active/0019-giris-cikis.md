# Spec 0019 — giris-cikis

- Status: In progress
- Mode: lite
- Plan: `specs/plans/0019-plan.md`
- Source: ADR-0002 (`docs/decisions/0002-kimlik-dogrulama-uygulama-ici-sifre.md`) D-4…D-6;
  ANALYZE kararları S-1…S-7 ve self-critique G-1…G-7 (İbrahim Gürhan, 2026-11-06); spec 0018
  VERIFY G-1, G-2
- Design: — (none — the flow below is the design)

## Intent
İK, yöneticiler ve personel uygulamaya kendi hesaplarıyla girmeli; giriş yapmamış kimse hiçbir
sayfayı görmemeli. Bu iş spec 0018'de açılan hesaplarla e-posta + şifre girişini, çıkışı ve
oturum süresini getirir; kaba kuvvete karşı 5 başarısız denemede hesap 15 dakika kilitlenir
(ADR-0002 D-4…D-6). Başarı: doğru şifreyle giren kullanıcı bugünkü ekranları aynen görür; yanlış
şifre ya da kilitte hesabın var olup olmadığı anlaşılmaz; oturum en fazla 8 saat sürer. Bilinçli
olarak yapılmayanlar: rol bazlı yetki (girişli herkes bugünkü gibi her şeyi görür), hesap ve
personel yönetim ekranları, şifre değiştirme ve sıfırlama.

## Requirements
- **R-1 Varsayılan kapalı:** Giriş yapmamış bir kullanıcının giriş ekranı dışındaki her isteği
  (sayfa açma ya da form gönderme) giriş ekranına yönlendirilir; hiçbir kayıt değişmez, hiçbir
  personel ya da talep verisi gösterilmez. Yeni eklenen sayfalar da kendiliğinden kapalıdır
  (açık bırakmak bilinçli bir istisna gerektirir).
- **R-2 Giriş:** Kullanıcı e-posta ve şifresiyle giriş yapar. E-posta spec 0018 R-5'teki gibi
  (boşluk atılıp küçük harfe çevrilerek) karşılaştırılır; şifre olduğu gibi kullanılır. Doğru
  bilgiyle, aktif ve kilitsiz bir hesap girer ve **her zaman Ana Sayfa'ya** gider; giriş öncesi
  istenen sayfaya geri dönülmez (S-7). Başarılı giriş, art arda başarısız deneme sayacını sıfırlar
  ve önceki oturum verisini temizler (D-5).
- **R-3 Genel hata iletisi (D-4):** Bilinmeyen e-posta, yanlış şifre, pasif hesap, kilitli hesap
  ve boş alan aynı iletiyi ve aynı durum kodunu (401, giriş ekranı yeniden gösterilir; G-1) alır:
  "E-posta ya da şifre hatalı." İleti hesabın var olup olmadığını,
  hangi alanın yanlış olduğunu ya da kilidi söylemez. Girilen e-posta formda geri basılır, şifre
  basılmaz. Giriş ekranında sabit bir not durur: "Çok sayıda hatalı denemeden sonra hesap geçici
  olarak kilitlenir." (S-2)
- **R-4 Kilit (D-4, S-2):** Var olan, aktif bir hesapta art arda 5. başarısız denemede hesap 15
  dakika kilitlenir. Kilit sürerken doğru şifre de reddedilir ve sayaç artmaz. Kilit bitince
  sayaç sıfırdan başlar. Sayaç ve kilit bitiş zamanı yeniden başlatmada korunur (spec 0018 R-6).
  Bilinmeyen e-postada ve pasif hesapta sayaç tutulmaz.
- **R-4a Girdi sınırı (G-3):** E-posta en fazla 254, şifre en fazla 1024 karakterdir. Sınırı
  aşan deneme genel iletiyi alır; şifre özeti hesaplanmaz, sayaç artmaz, WARNING yazılır (girilen
  metin yazılmaz).
- **R-4b Eşzamanlı denemeler (G-4):** Aynı anda gelen denemeler sayacı kaybetmez; kilit en geç
  5. başarısız denemede başlar.
- **R-5 Zamanlama (S-4):** Bilinmeyen e-postayla yapılan deneme, yanlış şifreyle yapılan deneme
  kadar şifre doğrulama işi yapar. Doğrulama işi her yolda eşittir; yanlış şifrede sayaç yazımı
  kadar küçük bir süre farkı kabul edilmiştir (review 0019 F-2, İbrahim Gürhan, 2026-11-06).
- **R-6 Log (D-4, S-3):** Her başarısız deneme log'a WARNING olarak yazılır. Var olan hesapta
  e-posta ve art arda deneme sayısı; bilinmeyen e-postada girilen metin değil yalnız "bilinmeyen
  hesap"; pasif ve kilitli hesapta e-posta ve durumu. Kilit başladığında ayrıca bir WARNING
  (e-posta, kilit bitişi). Başarılı giriş ve çıkış INFO (e-posta). Şifre ya da özeti hiçbir
  kayda yazılmaz.
- **R-7 Oturum süresi (D-5, S-6):** Oturum girişten itibaren en fazla 8 saat sürer; kullanıcı
  işlem yaptıkça uzamaz. Süre dolunca sonraki istek giriş ekranına yönlendirilir ve "Oturumunuzun
  süresi doldu. Lütfen tekrar giriş yapın." iletisi gösterilir; hiçbir kayıt değişmez.
- **R-8 Oturumdaki hesabın değişmesi (S-5):** Oturum açıkken hesap pasife alınır ya da artık
  yoksa sonraki istekte oturum kapanır ve kullanıcı giriş ekranına yönlendirilir; hiçbir kayıt
  değişmez.
- **R-9 Çıkış:** Girişli her sayfanın menüsünde kullanıcının e-postası (HTML kaçışlı; G-5) ve
  bir "Çıkış" düğmesi vardır. Çıkış bir form gönderimidir ve CSRF token taşır (spec 0011); çıkıştan sonra oturum
  verisi kalmaz ve kullanıcı giriş ekranında "Çıkış yapıldı." iletisini görür. Token'sız ya da
  bozuk token'lı çıkış isteği spec 0011'deki gibi reddedilir ve oturum açık kalır.
- **R-10 Giriş ekranı:** Sayfa başlığı ve form başlığı "Giriş", düğme "Giriş Yap" (G-7). Menü
  göstermez. Giriş formu CSRF token taşır (giriş CSRF'ine karşı);
  token hatası spec 0011 iletisini giriş ekranında gösterir ve kimse girmez. Girişli kullanıcı
  giriş ekranını açarsa Ana Sayfa'ya yönlendirilir.
- **R-11 Güvenli çerez (D-6, S-7):** Oturum çerezinin `Secure` özelliği yalnız ortamda
  `SESSION_COOKIE_SECURE=1` verildiğinde açılır; varsayılan kapalıdır (yerel / iç ağ HTTP).
  Belgeler, giriş sisteminin yayına yalnız HTTPS ile çıktığını ve orada bunun açılması
  gerektiğini söyler.
- **R-12 Değişmeyenler:** Girişli kullanıcı Ana Sayfa, Talepler ve Yeni Talep ekranlarını,
  iletilerini ve davranışını bugünkü gibi görür; tek fark menüdeki e-posta ve Çıkış düğmesidir.
- **R-13 Hesap aracı düzeltmeleri (0018 G-1, G-2):** `hesap-ac` şifre sorusu "Şifre (yazarken
  görünmez):" ve "Şifre (tekrar):" olur; "Bu e-posta adresiyle bir hesap zaten var: <e-posta>."
  iletisi noktayla biter.
- **R-14 Belgeler:** `README.md` (giriş, `SESSION_COOKIE_SECURE`, HTTPS şartı),
  `docs/security.md` AuthN bölümü bugünkü duruma, `docs/architecture.md` güncellenir.

## User experience
- **Flow (kullanıcı):** herhangi bir adresi açar → giriş ekranı → e-posta ve şifreyi girer →
  Ana Sayfa (menüde e-postası ve Çıkış) → işini yapar → Çıkış → giriş ekranı, "Çıkış yapıldı."
- **States — giriş ekranı:**
  - *İlk açılış:* "Giriş" başlığı, boş e-posta ve şifre alanları, "Giriş Yap" düğmesi, kilit
    notu; menü yok.
  - *Hatalı giriş (her neden):* "E-posta ya da şifre hatalı.", e-posta alanı dolu, şifre boş.
  - *Oturum süresi doldu:* "Oturumunuzun süresi doldu. Lütfen tekrar giriş yapın."
  - *Çıkış yapıldı:* "Çıkış yapıldı."
  - *Form süresi dolmuş / token hatası:* spec 0011 CSRF iletisi.
- **States — girişli sayfalar:** bugünkü durumlar aynen; menüde e-posta ve Çıkış.
- **Design reference:** none — the flow above is the design.
- **Accessibility:** her alanın görünür bir etiketi var (`<label>` alana bağlı); e-posta alanı
  `type=email` değil düz metin olabilir ama otomatik doldurma ipuçları (`username`,
  `current-password`) verilir; yalnız klavyeyle doldurulup Enter ile gönderilir; iletiler düz
  metin, yalnız renge dayanmaz.

## Constraints & out of scope
- **Kısıtlar:** Yeni çalışma zamanı bağımlılığı yok (Flask oturumu, Werkzeug şifre özeti;
  ADR-0002). Mimari kurallar geçerli: kilit ve giriş kuralları domain'de, domain gerçek saati
  okumaz (saat bağlantı noktasıyla), web depoya doğrudan erişmez. Tek sunucu varsayımı
  (ADR-0001). Oturum ve kilit süreleri uygulamanın saat bağlantı noktasından okunur; testler
  zamanı ileri alır (G-6). `SECRET_KEY` kuralı (spec 0011) aynen; tanımlı değilse yeniden başlatmada
  oturumlar düşer.
- **Mevcut testler (S-1):** Süreç içi test istemcileri ortak test altyapısında giriş yapmış
  sayılır; üretim kodunda test için kapı, bayrak ya da ortam değişkeni olmaz. Ayrı süreçte
  uygulamayı çalıştıran `test_persistence.py` ve `test_logging_config.py` betiklerindeki gerekli
  satırlar planda R-07 onayına gelir; başka mevcut test değişmez.
- **Kapsam dışı:** rol bazlı yetki (spec 0020+), hesap / personel yönetim ekranları, şifre
  değiştirme ve sıfırlama, "beni hatırla", IP bazlı sınırlama, çok faktörlü doğrulama, kilidi
  elle açma (kilit 15 dakikada kendiliğinden biter), hesabı pasife alma aracı ya da ekranı
  (R-8 ileride gelecek yönetim ekranına hazırlık; testte depo üzerinden yapılır, G-2).
- **Split:** proposed — kilit ayrı spec; kept as one — İbrahim Gürhan, kilitsiz giriş D-4'e
  aykırı olurdu (S-7 boyut notu).

## Acceptance criteria
- [ ] AC-1 — Giriş yapmamışken `/`, `/requests`, `/new` (GET) ve onay / red / Yeni Talep (POST)
  istekleri giriş ekranına yönlendirilir; POST'lar hiçbir kaydı değiştirmez; yanıtta personel ya
  da talep verisi yok. Uygulamanın giriş ekranı dışındaki her route'u kapalıdır (route listesi
  üzerinden).
- [ ] AC-2 — Doğru e-posta (büyük harf ve boşluklu yazım dahil) ve şifreyle aktif hesap girer,
  Ana Sayfa'ya yönlendirilir; giriş öncesi istenen sayfa ne olursa olsun hedef Ana Sayfa'dır.
  Menüde e-posta (HTML kaçışlı, G-5) ve Çıkış görünür; Ana Sayfa, Talepler ve Yeni Talep bugünkü içerikleri gösterir.
- [ ] AC-3 — Bilinmeyen e-posta, yanlış şifre, pasif hesap, kilitli hesap, boş e-posta ve boş
  şifre aynı iletiyi ve 401 durum kodunu alır (G-1); e-posta geri basılır, şifre basılmaz; kimse girmez.
- [ ] AC-4 — Art arda 4 yanlış denemeden sonra doğru şifre girer ve sayaç sıfırlanır; 5. yanlış
  denemede hesap kilitlenir, kilit sürerken doğru şifre reddedilir ve sayaç artmaz; 15 dakika
  dolunca (dolmasına 1 saniye kala değil) doğru şifre girer; kilit bitiminden sonraki ilk yanlış
  deneme sayacı 1 yapar. Sayaç ve kilit uygulama yeniden başlatıldığında (SQLite) korunur.
  Aynı anda gelen yanlış denemelerden sonra kilit en geç 5. başarısız denemede başlamıştır (G-4).
- [ ] AC-5 — Bilinmeyen e-postayla deneme, yanlış şifreyle deneme kadar şifre doğrulaması yapar
  (doğrulama çağrısı sayılarak); bilinmeyen e-posta ve pasif hesapta hiçbir hesabın sayacı değişmez.
  254 / 1024 karakter kabul edilir; 255 karakterlik e-posta ya da 1025 karakterlik şifre genel
  iletiyi alır, özet hesaplanmaz, sayaç artmaz (G-3).
- [ ] AC-6 — Log: her başarısız deneme bir WARNING (R-6 içeriği), kilit başlangıcı ayrı WARNING,
  başarılı giriş ve çıkış INFO; bilinmeyen e-postanın yazılan metni, şifre ve özet hiçbir log
  kaydında yok.
- [ ] AC-7 — Oturum girişten 8 saat sonra geçersizdir (8 saat dolmasına 1 saniye kala geçerli),
  arada yapılan istekler süreyi uzatmaz; süresi dolmuş oturumla gelen istek giriş ekranına gider,
  süre doldu iletisi görünür, POST hiçbir kaydı değiştirmez. Yeniden giriş yeni 8 saat başlatır.
- [ ] AC-8 — Oturum açıkken hesap pasife alınırsa ya da silinirse sonraki istek giriş ekranına
  gider ve oturum kapanır; POST hiçbir kaydı değiştirmez.
- [ ] AC-9 — Başarılı girişte giriş öncesi oturuma konmuş veri girişten sonra yoktur (oturum
  sabitleme). Çıkış CSRF token'lı form gönderimiyle oturumu bitirir, "Çıkış yapıldı." gösterilir,
  sonraki istekler giriş ekranına gider; token'sız ya da bozuk token'lı çıkış 400 alır ve oturum
  açık kalır; çıkış GET ile yapılamaz.
- [ ] AC-10 — Giriş ekranı: başlık "Giriş", düğme "Giriş Yap", menü yok, alan etiketleri bağlı, otomatik doldurma ipuçları var, kilit
  notu görünür, form CSRF token taşır (token'sız giriş 400 + spec 0011 iletisi, kimse girmez);
  girişli kullanıcı giriş ekranını açınca Ana Sayfa'ya yönlendirilir.
- [ ] AC-11 — `SESSION_COOKIE_SECURE=1` ile oturum çerezi `Secure` taşır; değişken yoksa ya da
  başka bir değerse taşımaz. Çerez her durumda `HttpOnly` ve `SameSite=Lax`.
- [ ] AC-12 — `hesap-ac` şifre soruları "Şifre (yazarken görünmez):" ve "Şifre (tekrar):"; var olan
  e-posta iletisi "…zaten var: <e-posta>." ile biter.
- [ ] AC-13 — Mevcut testler yalnız S-1'de onaylanan satırlarla değişir ve geçer; `README.md`,
  `docs/security.md`, `docs/architecture.md` bugünkü durumu anlatır.

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
