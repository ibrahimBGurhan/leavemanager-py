# Spec 0030 — refactor-karar-log-adi (mini)

- Status: Approved
- Mode: lite
- Plan: `specs/plans/0030-plan.md`
- Source: issue #43 — 0020 F2-1(b) (review 0020 round 2, `specs/plans/0020-plan.md` "Triage":
  "İşlem → log adı eşlemesi iki yerde … route'un log adını bilmesine gerek bırakmamak
  (`authorize_approve()` / `authorize_reject()` ya da işlem adı domain'e) …")
- Design: —
- Supersedes: —

## Intent
Bir talebi onaylama ya da reddetme yetkisi olmayan hesabın denemesi log'a işlem adıyla ("onay",
"red") yazılır. Bu ad bugün iki yerde tutuluyor: kuralın sahibi olan yetki katmanında ve web
katmanındaki ayrı bir eşleme tablosunda; web, yetkiyi sorarken log adını kendisi seçiyor. İş, adı
yalnız yetki katmanında bırakır; web yalnız "onay yetkisi var mı / red yetkisi var mı" diye sorar.
Davranış değişmez — bu bir refactor (`workflows/refactor.md`); kanıtı Preserved behavior taşır.

Triage kaydı (2026-11-12, İbrahim Gürhan onayı): (a) hata değil — bugünkü davranış spec 0020 /
0021'e uyuyor, log adlarını testler tam eşitlikle sabitliyor; (b) kriter değişmiyor; (c) ortak
koda dokunuyor (yetki sınıfı web, domain ve testlerce kullanılıyor; iki dosya) → CHANGE lane,
"tam çözüm" seçeneği.

### Gözlem (ANALYZE, 2026-11-12, HEAD `400c234`)
- Log adları yetki katmanında tanımlı ("onay", "red") ve onay / red işlemleri bunları kendisi
  kullanıyor.
- Web katmanı aynı adları içe aktarıyor ve işlem adından log adına ayrı bir tabloyla eşliyor;
  sonuçlandırma isteğinde yetkiyi bu adla, numarayı ayrıştırmadan, ham değerle soruyor.
- Bugünkü davranışı sabitleyen testler (değişmeyecek): `test_staff_cannot_decide`,
  `test_forbidden_is_logged` (`tests/test_authorization.py`), `test_manager_cannot_decide`,
  `test_over_long_request_id_is_refused` (`tests/test_manager_role.py`) — log satırını tam
  eşitlikle; `test_manager_authorize_decide_*` (`tests/test_access.py`) — yetki sorusunu işlem
  adıyla doğrudan.

## Changed behavior
none — no observable behavior change. Kanıtı aşağıdaki Preserved behavior kriterleri taşır.

## Preserved behavior
- [ ] PB-1 — **Yetkisiz deneme aynı yanıtı alır:** Personel ya da Yönetici, sonuçlandıramadığı bir
  talebi (kendi talebi, başka birimin talebi, sonuçlanmış, olmayan, sayı olmayan, aşırı uzun
  numara) onaylamaya ya da reddetmeye çalışınca 403 ve bugünkü ileti; hiçbir talep değişmez.
- [ ] PB-2 — **Log satırı aynı:** Her yetkisiz deneme için tek bir WARNING satırı, harfiyen
  `yetkisiz islem: <e-posta>, onay|red, hedef '<gönderilen ham değer>'` — onay için "onay", red
  için "red"; nedeni ve tarihleri yazılmaz.
- [ ] PB-3 — **Sıra aynı:** Yetki, numaranın ayrıştırılmasından, talebin varlığından ve durumundan
  önce denetlenir: yetkisiz hesap sayı olmayan / olmayan / sonuçlanmış talep için de 403 alır
  (404 / 400 değil). IK için olmayan talep 404, sonuçlanmış talep 400 kalır.
- [ ] PB-4 — **Yetkili karar aynı:** IK her bekleyen talebi, Yönetici biriminde başkasının
  bekleyen talebini onaylar / reddeder: bugünkü yönlendirme, başarı iletisi, durum değişikliği ve
  karar log'u.
- [ ] PB-5 — **Yapı hedefi:** Web katmanı onay / red log adlarını içermez — ne adları içe aktarır
  ne de işlemden log adına eşleme tutar; adlar yalnız yetki katmanında, tek yerde.
- [ ] PB-6 — Hiçbir test değişmez, zayıflatılmaz ya da silinmez (refactor kuralı: sıfır test
  düzenlemesi); `scripts/check` full yeşil.

## Out of scope
- Diğer yetki denetimlerinin log adları ("baskasi adina talep", "bakiye", "personel ekleme"):
  zaten yalnız yetki katmanında; dokunulmaz.
- Log biçiminin, iletilerin, durum kodlarının değişmesi.
- Başarılı işlem sonrası yönlendirme parametreleri (`sonuc=onaylandi|reddedildi`): log adı değil,
  web'in kendi URL sözlüğü; bu iş kapsamında değil.
- Rotalar ve URL'ler.

## Decisions (ANALYZE; onay: İbrahim Gürhan, 2026-11-12 — S-1…S-4 önerildiği gibi)
- **S-1 Biçim:** Yetki sınıfına iki dar soru eklenir — "onaylayabilir mi" ve "reddedebilir mi"
  (ör. `authorize_approve(target)` / `authorize_reject(target)`); log adını bunlar seçer. Onay /
  red işlemleri de bunları kullanır. Web, sonuçlandırma isteğinde işleme karşılık gelen soruyu
  çağırır; log adı tablosu ve adların içe aktarımı kalkar. *Öneri: kabul* — issue maddesinin ilk
  seçeneği; "işlem adını domain'e metin olarak geçirmek" web'e yine bir anahtar sözlüğü bırakır.
- **S-2 Genel soru kalır:** Bugünkü genel yetki sorusu (işlem adı + hedef) public kalır; yeni
  sorular onun ince sarmalayıcısıdır. *Öneri: kabul* — `tests/test_access.py` onu doğrudan
  çağırıyor; refactor sıfır test düzenlemesi ister (PB-6).
- **S-3 Yeni test yok:** PB-5 VERIFY'da kaynak taramasıyla (`grep`) ve mutantlarla kanıtlanır
  (adlar yer değiştirince, web yanlış soruyu çağırınca, yetki ayrıştırmadan sonraya kayınca
  mevcut testler kırmızı). *Öneri: kabul* — PB-1…PB-4'ü mevcut testler tam eşitlikle sabitliyor;
  PB-5 için bir mimari test ileride tekrar çift tanımı engellerdi ama bugünkü değeri düşük
  (bkz. Self-critique G-2).
- **S-4 Dal:** `refactor/0030-karar-log-adi-tek-yerde` (`docs/git.md`, Branching: Changed
  behavior = none). *Öneri: kabul.*

## Self-critique (ANALYZE)
- **G-1 Çift yetki sorusu:** Web yetkiyi bir kez sorar, ardından onay / red işlemi aynı soruyu
  bir daha sorar (bugün de böyle). Yetkisiz hesapta ilk soru reddeder, ikinciye gelinmez → log'da
  tek satır (PB-2). Refactor bu yapıyı değiştirmez; tek soruya indirmek davranış riski taşır
  (ayrıştırma sırası) ve kapsam dışı. *Öneri: olduğu gibi bırak, kayıt notu.*
- **G-2 PB-5'in kalıcılığı:** Yeni test olmadan ileride biri web'e yeniden bir log adı tablosu
  ekleyebilir. *Öneri: kabul edilebilir risk;* gerekirse `tests/test_architecture.py`'ye "web
  `domain.access`'ten `ACTION_` adı içe aktarmaz" kuralı ayrı bir işle eklenir.
- **G-3 Test edilebilirlik:** PB-1…PB-4 mevcut testlerle (yukarıdaki liste + IK karar testleri,
  ör. `test_hr_decides_any_request_including_own`); PB-5 tarama + mutant; PB-6 diff + check.
- **G-4 Boyut:** Tek yetenek, 6 kriter — bölme gerekmez.

## Definition of Done
- [ ] `scripts/check` green
- [ ] Independent review done; real findings fixed, noise rejected with written rationale
- [ ] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots)
- [ ] Spec moved to `specs/done/` (immutable there)
