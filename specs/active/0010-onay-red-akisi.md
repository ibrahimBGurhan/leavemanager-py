# Spec 0010 — onay-red-akisi

- Status: In progress
- Mode: lite
- Plan: `specs/plans/0010-plan.md`
- Source: `docs/domain.md` OD-7
- Design: — (hazır tasarım yok; aşağıdaki akış tasarımdır)

## Intent
IK bugün bekleyen izin taleplerini sonuçlandıramıyor. Bir talebin durumu yalnızca açılış
verisinde değişiyor; bu yüzden personelin Kullanılan ve Kalan günleri gerçeği göstermiyor.

Bu iş, IK'nın bekleyen bir talebi uygulamanın içinden onaylamasını ya da reddetmesini sağlar.
Onaylanan talebin günleri Kullanılan'a eklenir ve Kalan'dan düşer (BR-4, BR-5). Reddedilen talep
bakiyeyi etkilemez. Başarı: bekleyen her talep uygulamadan sonuçlandırılabilir ve sonuç ana
sayfadaki sayaçlarda, talepler ekranında ve personel bakiyelerinde hemen görünür.

Bilinçli olarak yapılmayanlar: kimlik doğrulama ve yetki kısıtı, bildirim, kararı geri alma,
red gerekçesi, denetim izi (kim / ne zaman).

## Requirements
- **R-1 Geçişler:** Bir talep yalnızca `Beklemede` durumundayken sonuçlandırılabilir:
  `Beklemede → Onaylandi` ya da `Beklemede → Reddedildi`. `Onaylandi` ve `Reddedildi` son
  durumlardır; bu spec'te hiçbir işlem onları değiştirmez (S2).
- **R-2 Onayda bakiye kontrolü:** Onay, BR-6 ile aynı kuralla yeniden kontrol edilir: talebin
  izin günü ≤ personelin o anki Kalan'ı ise onaylanır. Yetmezse talep `Beklemede` kalır ve
  kullanıcı kalanı ve talep edilen günü söyleyen bir mesaj görür. Karar yalnızca domain'de
  verilir ve talep oluşturmadaki bakiye kararıyla aynıdır (S3).
- **R-3 Redde kontrol yok:** Bekleyen bir talebin reddi, bakiyeden bağımsız olarak her zaman
  gerçekleşir.
- **R-4 Geçmiş tarih:** Başlangıç tarihi bugünden önce olan bekleyen bir talep de onaylanabilir
  ve reddedilebilir (BR-8 ile tutarlı; S7).
- **R-5 Başarısız işlem başarılı görünmez:** Zaten sonuçlanmış bir talebe ya da var olmayan bir
  talebe yapılan işlem hiçbir kaydı değiştirmez ve kullanıcı nedenini söyleyen bir mesaj görür
  (S6). Domain bu durumları tipli istisnalarla bildirir (`docs/conventions.md`); web onları
  Türkçe mesaja çevirir.
- **R-6 Sayfa görüntülemek durum değiştirmez:** Bir sayfayı açmak ya da bir bağlantıyı izlemek
  hiçbir talebin durumunu değiştirmez; durum yalnızca kullanıcının bilinçli olarak gönderdiği
  bir işlemle değişir.
- **R-7 Yetki (S1):** Kimlik doğrulama henüz olmadığından onay ve red, talep girmede olduğu gibi
  uygulamayı açan herkese açıktır. "Yalnızca IK" kısıtı auth spec'iyle gelir. Bu risk
  `docs/security.md`'ye yazılır.

## User experience
- **Flow:** Kullanıcı "Talepler" ekranını açar → `Beklemede` bir satırda "Onayla" ya da "Reddet"
  düğmesine basar → ek bir onay adımı olmadan işlem yapılır → kullanıcı Talepler ekranına geri
  döner ve sonucu söyleyen mesajı görür; satırın durumu güncellenmiştir (S5).
- **States:**
  - *Bekleyen satır:* "Onayla" ve "Reddet" düğmeleri görünür.
  - *Sonuçlanmış satır* (`Onaylandi` / `Reddedildi`): düğme yoktur; yalnızca durum rozeti görünür.
  - *Bekleyen talep yok:* liste satırları düğmesiz gösterilir; ekstra bir boş durum metni
    istenmez (liste bugün de boş olabilir; davranışı değişmez).
  - *Başarı:* listenin üstünde "Talep #N onaylandı." ya da "Talep #N reddedildi." mesajı.
  - *Hata:* listenin üstünde hata mesajı (yetersiz bakiye / zaten sonuçlanmış / bulunamadı /
    beklenmeyen hata); hiçbir satırın durumu değişmez.
  - *Yetki yok:* uygulanmaz (R-7).
- **Design reference:** none — the flow above is the design.
- **Accessibility:** Düğmeler klavyeyle (Tab + Enter) erişilebilir; görünür metinleri "Onayla"
  ve "Reddet" olur, yalnızca renk ya da simgeyle ayırt edilmez. Mesaj, görünür metin olarak
  sayfadadır.

## Constraints & out of scope
- **Kapsam dışı:**
  - Kimlik doğrulama ve rol bazlı yetki (Yönetici / IK ayrımı dahil), denetim izi — auth spec'i.
  - Kararı geri alma ya da değiştirme; iptal (personelin kendi talebini geri çekmesi).
  - Red gerekçesi (S4), bildirim (e-posta vb.).
  - Bekleyen taleplerin Kalan'dan düşülmesi (OD-3); iş günü hesabı (OD-4).
  - CSRF koruması: bugün hiçbir formda yok (`/new` dahil); tüm formlar için ayrı bir işte ele
    alınır (K-3, #25).
  - Jinja şablonlarına geçiş; rozet görünümü.
- **Kısıtlar:** Yeni çalışma zamanı bağımlılığı yok. Mevcut ekranların alanları ve hesapları
  değişmez. `tests/test_security.py` ve `tests/test_architecture.py` değişmeden yeşil kalır.
- **Split:** gerekmiyor — tek kullanıcı yeteneği ("IK bekleyen talebi sonuçlandırır"), onay ve red
  aynı yeteneğin iki ucu.

## Acceptance criteria
Örnekler bugün = 2026-10-23 ve açılış verisi içindir. "Mesaj gösterilir" = Talepler ekranında
listenin üstünde görünür metin. HTTP durumu (K-4, 0008 ile tutarlı): başarıda Talepler ekranına
yönlendirme; yetersiz bakiye ve zaten sonuçlanmış talep **400**, bulunamayan talep **404**,
beklenmeyen hata **500**.

- [ ] AC-1 — **Onay (mutlu yol):** Mehmet Demir'in bekleyen talebi #2 (3 gün) onaylanınca durumu
  `Onaylandi` olur; "Talep #2 onaylandı." mesajı gösterilir; ana sayfada Mehmet'in Kullanılan'ı
  0 → 3, Kalan'ı 20 → 17 olur; sayaçlar Bekleyen 4 → 3, Onaylanan 1 → 2 olur. Başarıdan sonra
  sayfayı yenilemek işlemi tekrar göndermez (K-5). Uygulama loguna talep numarasını ve sonucu
  içeren bir INFO satırı yazılır; satırda personel adı ve izin nedeni yoktur (K-6, AC-2 için de
  geçerli).
- [ ] AC-2 — **Red (mutlu yol):** Ahmet Celik'in bekleyen talebi #4 reddedilince durumu
  `Reddedildi` olur; "Talep #4 reddedildi." mesajı gösterilir; Ahmet'in Kullanılan ve Kalan'ı
  değişmez; sayaçlar Bekleyen 4 → 3, Reddedilen 3 → 4 olur.
- [ ] AC-3 — **Araya giren onay (R-2):** Ayse Yilmaz (Kalan 14) için 12 günlük yeni bir talep
  girilip onaylandıktan sonra Kalan 2 olur. Bu durumda bekleyen #5 (3 gün) onaylanmak istenirse
  onay gerçekleşmez, #5 `Beklemede` kalır ve "Personelin kalan izin bakiyesi yetersiz (kalan 2
  gün, talep 3 gün)." mesajı gösterilir; mesaj iç kod ya da ayrıntı içermez.
- [ ] AC-4 — **Onayda bakiye sınırı (R-2):** Kalan K iken talep edilen gün K − 1, K ve K + 1 olan
  bekleyen talepler için onay sonucu sırasıyla onaylandı / onaylandı / yetersiz bakiye olur
  (bakiyeyi tam kullanan onay kabul edilir). Servis ve ekran aynı kararı verir.
- [ ] AC-5 — **Red bakiyeye bakmaz (R-3):** AC-3 durumundaki #5 reddedilebilir ve `Reddedildi` olur.
- [ ] AC-6 — **Son durumlar değişmez (R-1, R-5):** Onaylanmış (#1) ya da reddedilmiş (#6) bir
  talebe onay veya red gönderilirse kayıt değişmez ve "Bu talep zaten sonuçlandırılmış." mesajı
  gösterilir. Aynı bekleyen talebe art arda iki kez onay gönderilirse ikincisi bu mesajı verir ve
  Kullanılan bir kez artar.
- [ ] AC-7 — **Bulunamayan talep (R-5):** Var olmayan bir talep numarasına (ör. 99) ya da sayı
  olmayan bir numaraya yapılan işlem hiçbir kaydı değiştirmez ve "Talep bulunamadı." mesajı
  gösterilir.
- [ ] AC-8 — **Beklenmeyen hata:** İşlem sırasında beklenmeyen bir hata olursa "İşlem
  tamamlanamadı. Lütfen daha sonra tekrar deneyin." mesajı gösterilir, hata stack trace'iyle
  loga yazılır, kullanıcıya istisna metni gösterilmez ve başarı mesajı görünmez.
- [ ] AC-9 — **Ekran durumları (UX):** Talepler ekranında yalnızca `Beklemede` satırlarda
  "Onayla" ve "Reddet" düğmeleri vardır; sonuçlanmış satırlarda düğme yoktur. Düğmeler klavyeyle
  erişilebilir ve metinleri görünürdür. Talepler ekranını ya da ana sayfayı açmak (yalnızca
  görüntüleme) hiçbir talebin durumunu değiştirmez (R-6).
- [ ] AC-10 — **Geçmiş tarih ve domain sözleşmesi (R-4, R-5):** Başlangıcı bugünden önce olan
  bekleyen bir talep onaylanabilir. Servisi doğrudan çağıran da AC-3/6/7'deki durumlarda tipli
  istisna alır; başarısızlık dönüş değeriyle bildirilmez. Belgeler güncellenir:
  - `docs/domain.md`: OD-7 "Bu sürümde IK onaylar; Yönetici onayı auth spec'inde
    değerlendirilir" diye kapanır (K-2); durum geçişleri ve onayda bakiye kontrolü iş kuralı
    olarak yazılır.
  - `docs/security.md`: "Bugün" notuna onay/red'in herkese açık olduğu eklenir; hedef rol modeli
    değişmez (K-2).

## Definition of Done
- [ ] Every acceptance criterion mapped to proof (test or reproducible observation)
- [ ] `scripts/check` green
- [ ] Independent review done; real findings fixed, noise rejected with written rationale
- [ ] Docs / ADRs updated if behavior or architecture changed
- [ ] Spec moved to `specs/done/` (it becomes immutable there)

## Kararlar (clarify, İbrahim Gürhan, 2026-11-04)
- **S1:** Auth beklenmez; onay/red herkese açık, risk `docs/security.md`'ye yazılır; "yalnızca IK"
  auth spec'iyle gelir.
- **S2:** Yalnızca `Beklemede → Onaylandi | Reddedildi`; son durumlar değişmez.
- **S3:** Onayda BR-6 yeniden kontrol edilir; yetmezse talep `Beklemede` kalır. Redde kontrol yok.
- **S4:** Red gerekçesi yok.
- **S5:** Talepler ekranında satır düğmeleri; ek onay adımı yok; işlem sonrası listeye dönüş ve mesaj.
- **S6:** Zaten sonuçlanmış → "Bu talep zaten sonuçlandırılmış."; yok → "Talep bulunamadı."
- **S7:** Geçmiş tarihli bekleyen talep onaylanabilir.

## Kararlar (self-critique, spec onayında, İbrahim Gürhan, 2026-11-04)
- **K-1:** Onaydaki bakiye mesajı IK'ya göre yazılır: "Personelin kalan izin bakiyesi yetersiz
  (kalan X gün, talep Y gün)." (AC-3).
- **K-2:** OD-7 "bu sürümde IK onaylar" diye kapanır; `docs/security.md` hedef rol modeli
  (Yönetici) değişmez, auth spec'inde değerlendirilir (AC-10).
- **K-3:** CSRF kapsam dışı; tüm formlar için ayrı iş: #25.
- **K-4:** HTTP durumları 0008 ile tutarlı: 400 / 404 / 500, başarıda yönlendirme.
- **K-5:** Başarı sonrası yenileme işlemi tekrarlamaz (AC-1); tekrarlansa AC-6 korur.
- **K-6:** Başarılı her onay/red için INFO log satırı: talep numarası ve sonuç; ad ve neden yok
  (KVKK).

## Review triage (round 1, İbrahim Gürhan, 2026-11-04)
Bağımsız review (read-only reviewer subagent, HEAD `fe6c24a`): 3 bulgu, hepsi Low.
- **F-1 — real → fix-1 (`d2b6c84`):** talep numarası `int()` ile okunuyordu; `" 2"`, Unicode
  rakam ve `0_2` gerçek bir talebe eşleniyordu (AC-7). Artık yalnız ASCII rakam kabul edilir; işlem
  adresi ve başarı parametresi aynı ayrıştırıcıyı kullanır.
- **F-2 — noise → #26:** durum değerlerinin string literal olarak kalan kullanımları
  (`get_used_days`, `create_request`, dashboard, `status_badge`) bu spec'ten önce de vardı ve bu
  spec'in yazdığı satırlar değil. Fix round'u yalnız bulguya dokunur; karakterizasyonla sabit
  ekran koduna kapsam dışı dokunmamak için davranışı korunan ayrı bir refactor işi.
- **F-3 — noise:** her satırda aynı "Onayla"/"Reddet" erişilebilir adı. Spec'in Accessibility
  maddesi (klavye, görünür metin, yalnız renge dayanmama) karşılanıyor; satıra özel ad
  (`aria-label`) spec dışı bir iyileştirme, tablo revizyonuyla (plan Risk 3) ele alınır.

## Scorecard (fill at ship — honest numbers make the process improvable)
| Metric | Value |
|---|---|
| Spec revisions | |
| Fix rounds | |
| Review findings: real / noise | |
| Regressions introduced | |
| Bugs escaped to production | |
