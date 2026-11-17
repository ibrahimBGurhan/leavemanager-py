# Spec 0036 — sablon-altcizgi-erisim-yasagi (mini)

- Status: Shipped
- Mode: lite
- Plan: `specs/plans/0036-plan.md`
- Source: spec 0033 review round 1 F-1 (`specs/plans/0033-plan.md`, "Triage (review round 1)":
  "**Takip işi (sonra):** şablonlarda `__` (dunder öznitelik erişimi) yasağı — `__class__`,
  `__globals__`, `__html__` yollarını tek kuralla kapatır; yeni kriter, ayrı spec."); istek:
  İbrahim Gürhan, 2026-11-17 (`/analyze`, 0033 F-1 takibi)
- Design: — (arayüz yok)
- Supersedes: — (0033 ve 0032 kriterleri aynen sürer; bu spec yanlarına yeni bir kural ekler)

## Intent
Ekranlardaki kullanıcı verisi yalnız otomatik kaçış sayesinde zararsız basılır
(`docs/security.md`, spec 0032). 0033 kaçışı kapatan kelimeleri yasakladı; ama bir şablon yasaklı
kelime kullanmadan altçizgili iç adlar (`__class__` vb.) üzerinden kaçışı yine kapatabiliyor ya da
Python'un iç yapısına uzanabiliyor. Bu iş davranışı değiştirmez, kuralı sıkılaştırır: şablonlar
altçizgiyle başlayan hiçbir ada hiçbir yolla erişemez ve erişilen ad şablonda sabit yazılmış olur;
ihlal `scripts/check`'te dosya ve satırı adlandırarak kırmızıya düşer. Bu spec yalnız altçizgi
yolunu kapatır; altçizgisiz iki kaçış yolu (review round 1 F-1: `indent` ve `.translate`) takip
spec'i 0037'nin konusudur.

Spec türü (S-6): gözlenebilir davranış değişmiyor, tek yapısal kural sıkılaşıyor, mevcut bir
kaynağın (0033 F-1) takibi → CHANGE lane, mini-spec (0029, 0031, 0033 kalıbı).

### Gözlem (ANALYZE, 2026-11-17, HEAD `af2c649`; Jinja 3.1.6, MarkupSafe 3.0.4, Flask 3.1.3)
Repo dışı bir betikte, otomatik kaçışı açık bir Jinja ortamında `x = "<b>"` ile denendi.

| Yazım | Kaçış kapanır mı | 0033 kelime yasağı yakalar mı | Metinde `__` yasağı yakalar mı |
|---|---|---|---|
| `{{ (''\|e).__class__(x) }}` | evet | hayır | evet |
| `{% set m = ''\|e %}{{ m.__class__(x) }}` | evet | hayır | evet |
| `{{ ((''\|e)\|attr('__class__'))(x) }}` | evet | hayır | evet |
| `{{ (''\|e)['__class__'](x) }}` | evet | hayır | evet |
| `{{ ([''\|e]\|map(attribute='__class__')\|first)(x) }}` | evet | hayır | evet |
| `attr('\x5f\x5fclass\x5f\x5f')` | evet | hayır | **hayır** |
| `attr('_'*2 ~ 'class' ~ '_'*2)` | evet | hayır | **hayır** |
| `attr(['_','_class_','_']\|join)` | evet | hayır | **hayır** |
| `(''\|e)['_'*2 ~ 'class' ~ '_'*2]` | evet | hayır | **hayır** |
| `map(attribute='_'*2 ~ 'class' ~ '_'*2)` | evet | hayır | **hayır** |
| `{{ lipsum.__globals__['__builtins__']['len'](x) }}` | hayır — ama Python iç yapısına erişir | hayır | evet |
| `'%s'\|format`, `replace`, `string`, `xmlattr`, `urlize`, `x\|indent`, `center`, `wordwrap`, `striptags`, `unescape()`, `namespace` | hayır (kaçışlı) | — | — |
| `{{ '{0.__class__.__mro__}'.format(''\|e) }}` | hayır — çıktı kaçışlı, ama iç yapıyı metin olarak okur | hayır | evet |
| `{{ ('a'\|e)\|indent(x, true) }}` (review round 1 F-1) | **evet** (`'<b>a'`) | hayır | hayır |
| `{{ ('a'\|e).translate({97: x}) }}` (review round 1 F-1) | **evet** (`'<b>'`) | hayır | hayır |

- Altçizgili ada erişim, kaçışı kapatan yolların bir ailesidir. **Düzeltme (review round 1 F-1,
  2026-11-17):** ANALYZE'daki "altçizgisiz yollar kaçışlı" sonucu yanlıştı — `indent` yalnız
  `x|indent` biçiminde (girdi olarak) denenmişti. Girdi `Markup` iken metin olarak verilen girinti
  genişliği ve Markup'ın `.translate()` metoduna verilen sözlük değerleri kaçışsız basılır; ikisi
  altçizgi kullanmaz, bu spec'in kuralının dışındadır (Out of scope, takip spec'i 0037). S-1 ve
  PB-3'teki "10 yol/yazım", tablonun altçizgili ilk 10 satırıdır; F-1'in iki satırı VERIFY'da
  kırmızı beklenmez (0037) (review round 2 R2-F-1).
- Metinde `__` aramak altçizgili yollardan beşini kaçırıyor: ad, çalışma anında hesaplanıyor ve
  metinde `__` geçmiyor.
- Jinja'nın sandbox ortamı altçizgili yolların hepsini çalışma anında `SecurityError` ile
  reddediyor; F-1'deki iki yolu (`indent`, `.translate`) reddetmiyor, ikisi sandbox'ta da kaçışsız
  basıyor (karşılaştırma için; S-4 gereği kapsam dışı; review round 2 R2-F-1).
- Bugün `web/templates/` altındaki 7 şablonun hiçbirinde `__`, `attr`, `format` ya da köşeli
  parantezle erişim yok; köşeli parantez yalnız `base.html:17-18`'de liste yazımı olarak geçiyor.

## Decisions (ANALYZE; onay: İbrahim Gürhan, 2026-11-17 — S-1…S-6 önerildiği gibi)
- **S-1 Kural erişimi ve hesaplanan adı yasaklar:** Altçizgiyle başlayan bir ada hiçbir yolla
  erişilmez (nokta, köşeli parantez, `attr` süzgeci, süzgeç/testlerin öznitelik adı argümanı) ve
  erişilen ad şablonda sabit yazılmış olur; adı çalışma anında hesaplanan erişim yasaktır. Gözlemdeki
  10 yolun 10'unu kapatan tek seçenek; metin yasağı 5'ini, yalnız-altçizgi kuralı hesaplanan adları
  kaçırır.
- **S-2 Tek altçizgi:** Yasak `_` ile başlayan her ada uygulanır (yalnız `__` değil) — Jinja'nın
  kendi sandbox kuralıyla aynı; bugün hiçbir şablon böyle bir ad kullanmıyor.
- **S-3 Erişim kuralı, metin kuralı değil:** Görünen metinde ya da `{# … #}` yorumunda geçen `__`
  serbesttir; yasak yalnız erişimdir. Yanlış alarm olmaz.
- **S-4 Çalışma anı koruması yok:** Sandbox ortamı kapsam dışı — üretim kodunu değiştirir, ihlali
  `check` yerine çalışma anında 500'e çevirir; şablonları yalnız geliştiriciler yazar. İstenirse
  ayrı ADR konusu.
- **S-5 0033 aynen kalır:** Kelime yasağı (`autoescape`, `safe`, `Markup`) ve 0032 kuralları
  değişmez, zayıflamaz (kural 5); yeni kural yanlarına eklenir. Supersedes yok. `docs/security.md`
  "Çıktı" maddesine tek cümle eklenir: şablonlar altçizgiyle başlayan adlara erişemez.
- **S-6 Mini spec, CHANGE lane;** numara 0036.

## Changed behavior
none — no observable behavior change (ekranlar, HTTP, loglar aynı). Değişen yalnız yapısal kural;
kanıtı aşağıdaki Preserved behavior kriterleri taşır.

## Preserved behavior
- [x] PB-1 — **Altçizgili ada erişim yok:** `web/templates/` altındaki hiçbir şablon `_` ile
  başlayan bir ada erişmez: noktayla (`x._a`, `x.__class__`), köşeli parantezle (`x['_a']`),
  `attr` süzgeciyle ve bir süzgecin ya da testin öznitelik adı argümanıyla (`map(attribute=…)`,
  `selectattr`, `rejectattr`, `sort`, `groupby`, `sum`, `unique`, `min`, `max` gibi). Metnin içinden
  alan okuyan `.format(…)` ve `.format_map(…)` metot çağrıları da yasaktır (G-1; `|format`
  süzgeci serbest). İhlalde test dosyayı ve satırı adlandırarak kırmızıya düşer; ayrıştırılamayan
  bir şablon atlanmaz, dosyayı adlandırarak kırmızıya düşer (G-2).
- [x] PB-2 — **Hesaplanan ad yok:** Köşeli parantezle erişimin anahtarı, `attr` süzgecinin adı ve
  süzgeç/testlerin öznitelik adı argümanı şablonda sabit yazılmış bir değerdir; adı çalışma anında
  hesaplanan (değişken, birleştirme, `join`, kaçış dizisi içeren ifade) erişim kırmızıya düşer.
  Sabit anahtar ya da sıra numarasıyla erişim (`x['ad']`, `x[0]`) ve liste yazımı (`base.html`
  menüsü) serbesttir.
- [x] PB-3 — **Gözlemdeki her yol yakalanır:** Gözlem tablosundaki kaçışı kapatan 10 yazımın her
  biri ve `lipsum.__globals__` erişimi bir şablona eklenince test kırmızı (VERIFY'da repo dışı
  kopyada mutantla).
- [x] PB-4 — **Yanlış alarm yok:** Bugünkü 7 şablon yeşil; görünen metinde ya da `{# … #}`
  yorumunda geçen `__` ve altçizgisiz erişimler (`row.name`, `config.get(…)`, `loop.index`,
  `x['ad']`, `x[0]`) testi kırmızıya düşürmez (VERIFY'da zararsız mutantlarla).
- [x] PB-5 — **0033 ve 0032 kuralları aynen sürer:** Şablonlarda `autoescape`, `safe`, `Markup`
  kelime yasağı; her şablon `.html`; `web/*.py`'de HTML sabiti, `render_template_string`, `Markup`,
  `markupsafe` yasağı değişmez. 0033 ve 0032 VERIFY mutantları yine kırmızı; hiçbir test silinmez,
  atlanmaz, zayıflatılmaz.
- [x] PB-6 — **Başka hiçbir şey değişmez:** Üretim kodu ve şablonlar değişmez
  (`git diff main...HEAD -- web app.py domain storage` boş); `docs/security.md`'de yalnız S-5'teki
  tek cümle; `scripts/check` full yeşil.

## Out of scope
- Altçizgi kullanmadan kaçışsız sonuç üreten süzgeç/metot argümanları — `('a'|e)|indent(x, true)`,
  `('a'|e).translate({97: x})` (review round 1 F-1): takip spec'i 0037. Bugün hiçbir şablon
  `indent` ya da `translate` kullanmıyor.
- Çalışma anı koruması (Jinja sandbox ortamı) — S-4.
- Python'dan şablona geçen nesneler: `web/*.py`'deki `Markup` / `markupsafe` yasağı (0032) bunu
  kapsar; ek bir şey yapılmaz.
- Şablon adları (`{% extends %}`, `{% include %}`, `{% import %}`/`{% from … import %}`) — bunlar
  erişim değildir; `_macros.html` gibi altçizgiyle başlayan dosya adı serbesttir.
- Görünen metin ve yorumlardaki `__` — S-3.
- Üretim kodu, şablonlar, ekranlar.

## Self-critique (ANALYZE; G-1…G-6 önerildiği gibi — onay: İbrahim Gürhan, 2026-11-17)
- **G-1 `.format()` biçim alanı:** `'{0.__class__.__mro__}'.format(x)` altçizgili adı bir metin
  sabitinin içinden okur; S-3 gereği metin serbest olduğundan erişim kuralı bunu görmez. Çıktı
  kaçışlı (kaçış atlatması değil, iç yapının metin olarak okunması). *Karar:* `.format()` ve
  `.format_map()` metot çağrısı yasak (PB-1); `|format` süzgeci `%` biçimlendirmesi kullanır, alan
  erişimi yoktur, serbest. Bugün hiçbir şablon `format` kullanmıyor.
- **G-2 Ayrıştırılamayan şablon:** Kural şablonun yapısına bakar. *Karar:* ayrıştırılamayan dosya
  atlanmaz, adlandırılarak kırmızıya düşer (PB-1) — sessiz atlama açık bırakır.
- **G-3 Gelecekte değişkenle erişim ihtiyacı** (ör. `bakiyeler[row.id]`) PB-2'de kırmızıdır.
  *Karar: kabul edilen risk* — değer Python'da hazırlanıp verilir ya da kural yeni spec'le bilinçli
  gevşetilir; sessiz açıktan yanlış alarm iyidir (0033 G-1 ile aynı yaklaşım).
- **G-4 Öznitelik adı alan süzgeç/test listesi** PB-1'de örneklerle verilir, kapalı liste değildir.
  *Karar:* Jinja 3.1.6'daki tam listeyi plan çıkarır; VERIFY her biri için mutant koşar. Jinja
  yükseltmesinde gelen yeni süzgeç ayrı takip işidir.
- **G-5 Test edilebilirlik:** PB-1…PB-4 repo dışı kopyada mutantlarla (0033 kalıbı); PB-5 0033 ve
  0032 mutant listeleriyle; PB-6 `git diff` ve full check ile. Kanıtsız kriter yok.
- **G-6 Boyut:** Tek kural, 6 kriter, bir test ve bir doküman cümlesi — bölme gerekmez.

## Verification (VERIFY, 2026-11-17, HEAD `83e1bb7`)
PB-1…PB-6 Pass; full `CHECK GREEN (full, 3 steps, 57 s)` (793 passed, 5 skipped). Mutantlar repo
dışı kopyalarda (`git archive`), `test_templates_never_reach_underscore_names`: Gözlemin altçizgili
10 yolu ve `lipsum.__globals__` `main`'de yeşil, dalda kırmızı; `.format`/`.format_map` her yoldan,
noktalı/virgüllü adlar, tek altçizgi, `ns._a`, dilim, değişkenle anahtar/ad ve ayrıştırılamayan
şablon dalda kırmızı (25/25); zararsız 11 yazım (`__` metin/yorumda, `x['ad']`, `x[0]`, `x[-1]`,
`'%s'|format`, `_macros.html` importu…) yeşil; 0033 ve 0032 mutantları (19) eski testle kırmızı.
Üretim diff'i boş; `tests/` diff'i yalnız ekleme. Review round 1: F-1 real (spec düzeltmesi, kod
düzeltmesi yok — takip 0037: `indent(x, true)`, `.translate`), F-2 real (fixed `b100a6b`), F-3
kısmen real (`x[-1]` fixed `7c07127`; `join`/`default` kabul edilen risk); round 2: R2-F-1 real
(fixed `ae3bb78`); round 3 temiz. UI değişmedi; ekran görüntüsü gerekmez. Ayrıntı:
`specs/plans/0036-plan.md` "Triage" ve "Verify".

## Definition of Done
- [x] `scripts/check` green
- [x] Independent review done; real findings fixed, noise rejected with written rationale
- [x] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots)
- [x] Spec moved to `specs/done/` (immutable there)
