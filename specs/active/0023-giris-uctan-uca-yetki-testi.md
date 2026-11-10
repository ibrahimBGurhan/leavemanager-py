# Spec 0023 — giris-uctan-uca-yetki-testi (mini)

- Status: In progress
- Mode: lite
- Plan: `specs/plans/0023-plan.md`
- Source: issue #43 — 0020 G-1 (spec 0020 VERIFY: "Gerçek girişle Personel ve bağlı personel kaydı
  olmayan hesap için uçtan uca test")
- Design: —
- Supersedes: —

## Intent
Spec 0020'nin rol kuralları (Personel yalnız kendi verisini görür; personel kaydına bağlı olmayan
hesap hiçbir veri görmez) bugün testlerde oturum kontrolü değiştirilerek sınanıyor; gerçek giriş
ekranından geçen yol yalnız elle gözlemlendi. Bu iş davranışı değiştirmez: gerçek giriş (`/giris`,
gerçek şifre özeti, gerçek oturum çerezi, açık CSRF) ile bu iki hesabın uçtan uca yolculuğunu bir
testle kilitler; böylece giriş kapısı ile yetki görünümü arasındaki bağ (oturumdaki hesabın
`AccountView`'a ulaşması) bir refactor'da sessizce kopamaz.

Triage kaydı (issue #43, 2026-11-10): rubrik (a) hata değil, (b) kriter değişmiyor, (c) ortak kod
yok; ancak iş yeni test olduğu için trivial lane'in "yeni bir test → yeniden triage" kuralı
gereği insan kararıyla CHANGE lane'de, mini-spec ile yürütülür (spec 0004 kalıbı).

## Changed behavior
none — no observable behavior change. Kanıtı aşağıdaki Preserved behavior kriterleri taşır.

## Preserved behavior
Testler gerçek oturum kontrolüyle (`logged_out` fikstürü) ve açık CSRF ile çalışır: hesaplar
gerçek şifre özetiyle açılır, giriş `/giris` formundan yapılır, her form gönderimi sayfadaki
token'ı kullanır (S-2). A = Ayse Yilmaz (1, IT), B = Mehmet Demir (2, Muhasebe), demo verisi.

- [ ] PB-1 — **Personel (A'ya bağlı)** gerçek girişten sonra: Ana Sayfa yalnız A'nın sayılarını
  ve bakiye satırını gösterir, B'nin adı ve birimi yoktur (0020 AC-2); Talepler yalnız A'nın
  taleplerini gösterir ve hiçbir Onayla / Reddet düğmesi yoktur (0020 AC-3); Yeni Talep personel
  seçimi göstermez, A'nın adını gösterir ve geçerli gönderim A adına `Beklemede` bir talep açar
  (0020 AC-4).
- [ ] PB-2 — **Personel (A'ya bağlı)**, aynı oturumda: B'nin bekleyen talebini onaylama ve B
  adına talep gönderme 403 + "Bu işlem için yetkiniz yok." alır, hiçbir kayıt değişmez, log'da
  hesabın e-postasıyla WARNING vardır (0020 AC-5, AC-6); "Yeni Personel" bağlantısı ve ekranı
  yoktur / 403 (0022 AC-6).
- [ ] PB-3 — **Personel kaydına bağlı olmayan Personel hesabı** gerçek girişten sonra: Ana
  Sayfa'da sayılar 0 ve bakiye satırı yok, Talepler boş, Yeni Talep form göstermez ve G-1
  iletisini 200 ile verir, talep gönderimi 403 alır ve hiçbir talep oluşmaz (0020 AC-8).
- [ ] PB-4 — Çıkıştan (`/cikis`) sonra aynı istemciyle Ana Sayfa yine girişe yönlendirir ve
  aynı tarayıcıda ikinci hesapla giriş, ilk hesabın kapsamını taşımaz (S-3).
- [ ] PB-5 — Testler gerçekten gerçek yolu sınar: oturumdaki hesabı görünüme bağlayan kod
  bozulursa (ör. görünüm sabit bir İK hesabıyla kurulursa ya da giriş kapısı `g.account`'u
  oturumdan okumazsa) bu testlerden en az biri kırmızıya düşer (VERIFY'da mutantla gösterilir).
- [ ] PB-6 — Üretim kodu değişmez (`git diff main -- domain web storage app.py` boş); mevcut
  testlerin hiçbiri değişmez, zayıflatılmaz ya da silinmez; `scripts/check` full yeşil.

## Out of scope
- Davranış değişikliği; yeni ileti ya da ekran.
- Yönetici ve İK için uçtan uca test (0021 ve 0019 testleri kapsar; S-1).
- Issue #43'ün diğer maddeleri (0020 G-3, G-4, F2-1(b); 0021 G-B, G-E; 0022 G-1, G-2).

## Decisions (ANALYZE; onay: İbrahim Gürhan, 2026-11-10 — S-1…S-4 önerildiği gibi)
- **S-1 Kapsam:** yalnız issue'nun adlandırdığı iki hesap (bağlı Personel, bağlantısız Personel).
  Yönetici eklenmez. *Öneri: kabul.*
- **S-2 CSRF açık:** gerçek tarayıcı yolu gibi, token sayfadan alınır (`tests/test_login.py`
  `csrf_client` kalıbı). *Öneri: kabul.*
- **S-3 Çıkış ve hesap değişimi:** aynı istemciyle çıkış + ikinci hesapla giriş (PB-4) eklenir;
  oturum verisinin hesaplar arasında taşınmadığını gerçek yolda gösterir. *Öneri: kabul.*
- **S-4 Yer:** yeni dosya `tests/test_login_authorization_e2e.py`; mevcut test dosyaları
  değişmez. *Öneri: kabul.*

## Definition of Done
- [ ] `scripts/check` green
- [ ] Independent review done; real findings fixed, noise rejected with written rationale
- [ ] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots)
- [ ] Spec moved to `specs/done/` (immutable there)
