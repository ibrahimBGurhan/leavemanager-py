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

## Review triage (round 2, İbrahim Gürhan, 2026-11-04)
Bağımsız review, fix diff `fe6c24a..940fb70`: fix-1 F-1'i karşılıyor (testler fix öncesi kopyada
5/5 kırmızı); 1 yeni bulgu.
- **F-4 — real → fix-2 (`3a2299a`):** fix-1'in getirdiği regresyon. 4300 haneden uzun numara
  `int()`'te `ValueError` fırlatıyordu ve `try` dışındaydı; işlem adresi ve salt görüntüleme
  olan `?talep=` parametresi 500 veriyordu. Artık bulunamadı (404) / mesaj yok sayılır.

Round 3 (fix diff `940fb70..53faa69`): clean, triage edilecek bulgu yok.

## Verification (VERIFY, 2026-11-04, HEAD `53faa69`, bağımsız QA subagent)
Mutantlar ve ekran görüntüleri repo dışında, scratch'teki `git archive` kopyalarında üretildi;
hiçbiri commit'lenmedi. Gerçek süreç `python app.py` ile koşuldu (`Debug mode: off`). Suite
kanıtı: HEAD `53faa69` için `162 passed, 5 skipped`, `CHECK GREEN (full)`.

| Kriter | Kanıt | Durum |
|---|---|---|
| AC-1 | `test_approve_pending_request_updates_status_and_balance`, `test_screen_approve_redirects_with_message_and_updates_dashboard`, `test_screen_reload_after_success_does_not_repeat`, `test_decision_logs_info_without_personal_data[approve]`. Gerçek süreç: 302 → `?sonuc=onaylandi&talep=2`, mesaj; iki F5'te yeni log yok; Mehmet 20/3/17; log satırında ad/neden yok | Pass |
| AC-2 | `test_reject_pending_request_keeps_balance`, `test_screen_reject_shows_message_and_counts`, `…logs_info…[reject]`. Gerçek süreç: 302, mesaj, Ahmet 20/0/20 | Pass |
| AC-3 | `test_approve_after_intervening_approval_is_refused`, `test_screen_approve_insufficient_shows_message`. Gerçek süreç: Ayse 12 gün onay → Kalan 2; #5 → 400 ve tam mesaj; `ERR-`/`Traceback` yok | Pass |
| AC-4 | `test_approve_balance_boundary[K-1/K/K+1]`, `test_screen_and_service_agree_on_approval[K-1/K/K+1]`; `<`→`<=` mutantı ikisini de kırdı | Pass |
| AC-5 | `test_reject_ignores_balance`, `test_screen_reject_ignores_balance`; gerçek süreçte 302 | Pass |
| AC-6 | `test_decided_request_cannot_change[×4]`, `test_screen_decided_request_shows_message[×4]`, `test_double_approve_counts_once`; gerçek süreçte 400 ve mesaj | Pass |
| AC-7 | `test_unknown_request_raises_not_found[×2]`, `test_screen_unknown_or_non_numeric_request[99/abc/%202/%D9%A2/0_2/4301-digits]`; gerçek süreçte 404 ve mesaj | Pass |
| AC-8 | `test_screen_unexpected_error_is_logged_not_shown`; ilgili iki mutant kırıldı. Gerçek süreçte repo değişmeden tetiklenemez (G-3) | Pass (yalnız test) |
| AC-9 | `test_buttons_only_on_pending_rows`, `test_get_never_changes_status`, `test_success_message_requires_matching_state`; gerçek süreçte düğmeler yalnız 4 bekleyen satırda, GET → 405 | Pass (klavye: G-2) |
| AC-10 | `test_approve_past_dated_pending_request`; başarıda `None`, başarısızlıkta tipli istisna (mutantlarla gösterildi); `docs/domain.md` BR-10 + OD-7, `docs/security.md` "Bugün" notu | Pass |
| Kısıtlar | `requirements*.txt`, `app.py`, `scripts/`, `tools/` değişmedi; `test_security.py`, `test_architecture.py`, baseline testleri ve `conftest.py` blob'ları `main` ile aynı | Pass |

Kayıtlar:
- Mutantlar: 23'ün 22'si kırıldı. Hayatta kalan M23 (başarı mesajı için yalnız "Beklemede değil") → G-1, fix-3 ile kapandı.
- Ters kontrol: HEAD'in `tests/test_approval.py` testleri `main`'in kodu üzerinde `40 failed, 9 passed` (geçen 9, mesaj olmadığını söyleyen negatif durumlar).
- UI ekran görüntüleri: 8 durum (başlangıç listesi, onay başarısı, onay sonrası ana sayfa, red başarısı, yetersiz bakiye, zaten sonuçlanmış, bulunamadı, bekleyen talep yok) headless Chrome ile çekildi; repoda değiller, PR'a eklenir.

### VERIFY triage (İbrahim Gürhan, 2026-11-04)
- **G-1 — real → fix-3 (`c0e5f65`, yalnız test):** `test_success_message_requires_matching_state`'e ters sonuçla sonuçlanmış iki durum eklendi (`onaylandi&talep=6`, `reddedildi&talep=1`). M23 mutantı scratch kopyada artık `2 failed`.
- **G-2 — kabul:** klavye erişiminin kanıtı yapısal. Düğmeler form içinde yerel `<input type=submit>`; `tabindex`/`disabled` yok. Yerel submit öğesi tanım gereği odaklanabilir ve Enter ile gönderilir.
- **G-3 — kabul:** AC-8 yalnız testle kanıtlı; test ayırt edici (iki mutant kırıldı).
- **G-4 — düzeltildi:** plandaki criterion↔test haritası gerçek test adlarıyla hizalandı (log testleri tek parametreli test, AC-5 servis + ekran, AC-7 ve AC-9 yeni durumlar).
- **I-1 — kabul, #25'e not:** iki ekran testi yönlendirme adresinin tam sorgu biçimini sabitliyor; #25'te flash'a geçilirse "302 + /requests + hedefte mesaj" iddiasına gevşetilir.
- **I-2, I-3 — kabul:** monkeypatch, sanctioned storage seam'inden; form `action` adresleri route sözleşmesi.

## Scorecard (fill at ship — honest numbers make the process improvable)
| Metric | Value |
|---|---|
| Spec revisions | |
| Fix rounds | |
| Review findings: real / noise | |
| Regressions introduced | |
| Bugs escaped to production | |
