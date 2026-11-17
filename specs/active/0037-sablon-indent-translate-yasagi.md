# Spec 0037 — sablon-indent-translate-yasagi (mini)

- Status: Approved
- Mode: lite
- Plan: `specs/plans/0037-plan.md`
- Source: spec 0036 review round 1 F-1 (`specs/plans/0036-plan.md`, "Triage (review round 1)":
  "**Takip spec'i 0037** (sıradaki iş): kaçışsız sonuç üreten süzgeç/metot argümanları — izin
  listesi mi dar yasak mı orada karar."); istek: İbrahim Gürhan, 2026-11-17 (`/analyze`, 0036 F-1
  takibi)
- Design: — (arayüz yok)
- Supersedes: — (0036, 0033 ve 0032 kriterleri aynen sürer; bu spec yanlarına yeni bir kural ekler)

## Intent
Ekranlardaki kullanıcı verisi yalnız otomatik kaçış sayesinde zararsız basılır
(`docs/security.md`, spec 0032). 0033 kaçışı kapatan kelimeleri, 0036 altçizgili adlara erişimi
yasakladı; ama iki yerleşik araç — `indent` süzgeci ve `translate` metodu — altçizgi kullanmadan
kullanıcı metnini kaçışsız sayfaya basabiliyor. Bugün hiçbir şablon bunları kullanmıyor; bir
geliştiricinin ileride bilmeden kullanması saklı bir XSS açığı olur. Bu iş davranışı değiştirmez,
kuralı sıkılaştırır: iki yol hangi yazımla şablona girerse girsin `scripts/check` dosya ve satırı
adlandırarak kırmızıya düşer, zararsız kullanım (`indent(4)`) serbest kalır; Jinja ya da MarkupSafe
yükseltmesi yeni bir süzgeç ya da metot getirirse bu da `check`'te görünür olur.

Spec türü (S-6): gözlenebilir davranış değişmiyor, tek yapısal kural sıkılaşıyor, mevcut bir
kaynağın (0036 F-1) takibi → CHANGE lane, mini-spec (0033, 0036 kalıbı).

### Gözlem (ANALYZE, 2026-11-17, HEAD `e272d00`; Jinja 3.1.6, MarkupSafe 3.0.4, Flask 3.1.3)
Repo dışı betiklerle, Flask'in şablon ortamında otomatik kaçış açıkken `x = "<b>"` ile denendi.
Tarama: 54 süzgecin hepsi ve `Markup`'ın 50 açık metodunun hepsi, 0–3 konumsal argümanla
(kullanıcı metni, tek karakter, sayı, `true`/`false`, sözlük, liste) üç girdi türünde (`Markup`, düz
metin, `Markup` listesi); ardından anahtar sözcüklü argümanlar ve dolaylı yollar.

| Yazım | Sonuç | Kaçış kapanır mı |
|---|---|---|
| `{{ ('a'\|e)\|indent(x, true) }}` | `'<b>a'` | **evet** |
| `{{ ('a\nb'\|e)\|indent(x) }}` — çok satırlı girdide `first` gerekmez | `'a\n<b>b'` | **evet** |
| `{{ ('a\n\nb'\|e)\|indent(x, blank=true) }}` | `'a\n<b>\n<b>b'` | **evet** |
| `{{ m()\|indent(x) }}` — makro çıktısı `Markup`'tır (`decision_buttons(row)` da) | `'a\n<b>b'` | **evet** |
| `{% filter indent(x) %}a↵b{% endfilter %}` | `'a\n<b>b'` | **evet** |
| `{{ [('a\nb'\|e)]\|map('indent', x)\|join }}` | `'a\n<b>b'` | **evet** |
| `{{ ('a'\|e).translate({97: x}) }}`, `.translate(t)` (tablo değişkende) | `'<b>'` | **evet** |
| `{{ ('a'\|e).translate({97: 60}) }}` — sabit tablo | `'<'` | **evet** |
| `\|attr('translate')`, `map(attribute='translate')` ile çağrı | `'<b>'` | **evet** |
| `indent(4, true)`, `indent(n)` (`n = 60`), `indent(true)` | girinti boşluk | hayır |
| `('a'\|e)\|indent(x)` tek satır, `x\|indent(…)` (girdi düz metin) | kaçışlı | hayır |
| `wordwrap(wrapstring=x)`, `truncate(end=x)`, `replace`, `join`, `default`, `urlize(target/rel=x)`, `tojson(indent=x)`, `trim(x)`, `.replace`, `.join`, `.format`, `.split`, `.partition`, `.removeprefix` | kaçışlı | hayır |
| `center(x)`, `.center/.ljust(5, '<')`, `.expandtabs(x)`, `'…'\|format(x)` | hata | hayır |

- Kaçışı kapatan **yalnız iki giriş noktası** var: `indent` süzgecine metin olarak verilen
  genişlik (girinti metni olarak `Markup`'ın içine kaçışsız girer) ve `translate` metoduna verilen
  tablonun değerleri. Diğer 53 süzgeç ve 49 metot, denenen argümanlarla kaçışlı ya da hata veriyor.
- Bugün `web/templates/` altındaki 7 şablonda hiç süzgeç ve `{% filter %}` bloğu yok; kullanılan
  yalnız `is none` testi ve `config.get()`, `csrf_token()`, `url_for()`, makro çağrıları.
- Tarama bugünkü sürümlerin fotoğrafıdır; bir yükseltme yeni süzgeç ya da metot getirebilir (S-4).

## Decisions (ANALYZE; onay: İbrahim Gürhan, 2026-11-17 — S-1…S-6 önerildiği gibi)
- **S-1 Dar yasak, izin listesi değil:** Kural yalnız `indent` ve `translate`'i hedefler. Tarama
  104 giriş noktasında tam iki sızıntı gösteriyor; kapalı izin listesi `|length`, `|default` gibi
  zararsız her yeni kullanımı spec değişikliğine bağlardı (0033, 0036 ile aynı yaklaşım).
  Yükseltmede yeni sızıntı riski S-4'le karşılanır.
- **S-2 `indent` yalnız sabit tam sayı genişlikle:** Genişlik ya hiç verilmez ya da şablonda sabit
  yazılmış bir tam sayıdır. Metin, değişken, ifade ve `true`/`false` genişlik kırmızıdır (bool,
  "sabit tam sayı" kuralını yorumsuz ve dar tutmak için). `first` ve `blank` serbesttir.
- **S-3 `translate` tamamen yasak:** Her yoldan — nokta, köşeli parantez, `attr`, öznitelik adı
  alan süzgeçler — 0036'daki `.format` gibi. Sabit tablo bile ham `<` üretiyor; Türkçe arayüzde
  `replace` varken kullanım alanı yok.
- **S-4 Yükseltme bekçisi:** Bir test, yüklü sürümde şablonlara açık süzgeç adlarının ve `Markup`
  metot adlarının kümesini repoda kayıtlı bugünkü listeyle karşılaştırır; küme değişirse kırmızıya
  düşer, biri gözlem taramasını yeniden koşup listeyi bilinçli günceller. Tarama değil, ad
  karşılaştırması — hızlı. (a) yalnız doküman notu unutulur, (c) hiçbir şey bu spec'in açığını
  gelecekte yeniden açar.
- **S-5 Dolaylı yollar aynı kurala girer:** `{% filter indent(…) %}` bloğu `|indent` ile aynı
  kurala tabidir; `map('indent', …)` argümanlarına bakılmadan kırmızıdır (bugün kullanılmıyor; basit
  kural — sessiz açıktan yanlış alarm iyidir, 0036 G-3); `map(attribute='translate')` S-3 kapsamında.
- **S-6 Mini spec, CHANGE lane;** numara 0037. `docs/security.md` "Çıktı" maddesine, 0036
  cümlesinin yanına tek cümle eklenir.

## Changed behavior
none — no observable behavior change (ekranlar, HTTP, loglar aynı). Değişen yalnız yapısal kural;
kanıtı aşağıdaki Preserved behavior kriterleri taşır.

## Preserved behavior
- [ ] PB-1 — **`indent` yalnız sabit tam sayı genişlikle:** `web/templates/` altındaki hiçbir
  şablonda `indent` süzgecinin genişliği — konumsal ya da `width=` ile — metin, değişken, ifade ya da
  `true`/`false` değildir; genişlik ya hiç verilmez ya da şablonda sabit yazılmış bir tam sayıdır.
  Kural `|indent(…)` ve `{% filter indent(…) %}` için aynıdır; genişliği görülemeyen çağrı
  (`*args`, `**kwargs`) kırmızıdır. İhlalde test dosyayı ve satırı adlandırarak kırmızıya düşer.
- [ ] PB-2 — **`translate` yok:** Hiçbir şablon `translate` adına hiçbir yolla erişmez: noktayla
  (`x.translate(…)`), köşeli parantezle (`x['translate']`), `attr` süzgeciyle ve bir süzgecin
  öznitelik adı argümanıyla (`map(attribute='translate')` vb., noktalı/virgüllü ad parçaları dahil).
  Tablo sabit olsa da kırmızıdır.
- [ ] PB-3 — **`map('indent', …)` yok:** `map` süzgecine süzgeç adı olarak `indent` verilmesi,
  diğer argümanlara bakılmadan kırmızıdır.
- [ ] PB-4 — **Gözlemdeki her yol yakalanır:** Gözlem tablosunda "evet" yazan 9 satırın her yazımı
  bir şablona eklenince test kırmızı (VERIFY'da repo dışı kopyada mutantla).
- [ ] PB-5 — **Yanlış alarm yok:** Bugünkü 7 şablon yeşil; `indent`, `indent(4)`, `indent(4, true)`,
  `indent(width=2, blank=true)`, `{% filter indent(2) %}`, `replace`, görünen metinde ya da
  `{# … #}` yorumunda geçen `indent`/`translate` kelimesi testi kırmızıya düşürmez (VERIFY'da
  zararsız mutantlarla).
- [ ] PB-6 — **Yükseltme bekçisi:** Yüklü Jinja + Flask ortamında şablonlara açık süzgeç adlarının
  kümesi ve `Markup`'ın açık metot adlarının kümesi repoda kayıtlı listeyle birebir aynıdır; bir ad
  eklenir ya da çıkarsa test kırmızıya düşer ve farkı (eklenen/çıkan adlar) adlandırır. Bugünkü
  sürümlerde yeşil.
- [ ] PB-7 — **0036, 0033 ve 0032 kuralları aynen sürer:** Altçizgi/hesaplanan ad/`.format`
  yasağı, `autoescape`/`safe`/`Markup` kelime yasağı, `.html` uzantısı, `web/*.py` kuralları
  değişmez; 0036 ve 0033/0032 VERIFY mutantları yine kırmızı; hiçbir test silinmez, atlanmaz,
  zayıflatılmaz.
- [ ] PB-8 — **Başka hiçbir şey değişmez:** Üretim kodu ve şablonlar değişmez
  (`git diff main...HEAD -- web app.py domain storage` boş); `docs/security.md`'de yalnız S-6'daki
  tek cümle; `scripts/check` full yeşil.

## Out of scope
- İzin listesi (kapalı süzgeç/metot listesi) — S-1.
- Çalışma anı koruması (Jinja sandbox ortamı) — 0036 S-4 ile aynı gerekçe; sandbox `indent` ve
  `translate`'i zaten reddetmiyor.
- Şablon global'leri (`lipsum`, `range`, `dict`, `cycler`, `joiner`, `namespace`, Flask'in
  `url_for`, `config`, `request`…) ve Jinja testleri (`is …`) için yükseltme bekçisi — S-4 kararı
  süzgeç ve `Markup` metot adlarıyla sınırlı; testler mantıksal değer döndürür.
- Python'dan şablona geçen nesnelerin metotları — 0032'nin `Markup` / `markupsafe` yasağı kapsar.
- Görünen metin ve yorumlardaki `indent`/`translate` kelimesi — erişim kuralı, metin kuralı değil
  (0036 S-3 ile aynı).
- Üretim kodu, şablonlar, ekranlar.

## Self-critique (ANALYZE; G-1…G-6 önerildiği gibi — onay: İbrahim Gürhan, 2026-11-17)
- **G-1 Bekçinin "şablonlara açık süzgeç" kümesi hangi ortamdan?** Bugün Flask 3.1.3 Jinja'nın 54
  süzgecine ad eklemiyor (`tojson` Jinja'nın kendi varsayılanı; gözlendi), ama ileride ekleyebilir.
  *Önerim:* `flask.Flask(…)` ile kurulan boş bir uygulamanın şablon ortamındaki süzgeçler — Jinja
  ve Flask yükseltmesini birlikte görür; uygulamanın kendisi (`app.py`) import edilmez (mimari
  testleri üretim kodunu import etmez). Uygulama kendi süzgecini eklerse bu bekçinin değil, kod
  değişikliğinin ve review'un konusudur.
- **G-2 Bekçi eşitlik mi, kapsama mı?** *Önerim:* eşitlik — çıkan ad da sürüm değişikliğinin
  işaretidir ve listeyi güncel tutar; maliyeti aynı.
- **G-3 Listeyi güncelleyen kişi ne yapar?** Bekçi kırmızıya düşünce yalnız listeyi güncellemek
  kuralı boşa çıkarır. *Önerim:* test mesajı ve `docs/security.md` cümlesi "gözlem taramasını yeniden
  koş" der; tarama betiği repoya alınmaz (kapsam dışı, 4 dakika sürüyor), yöntemi bu spec'in
  Gözlem bölümünde kayıtlı.
- **G-4 `indent` genişliği eksi ya da sıfır tam sayı:** `indent(-1)`, `indent(0)` kaçışlıdır (girinti
  boş). *Önerim:* serbest — "sabit tam sayı" kuralının içinde, işaret sorgulanmaz (0036'da `x[-1]`
  sabit sayıldı).
- **G-5 Test edilebilirlik:** PB-1…PB-5 repo dışı kopyada mutantlarla; PB-6 kopyada kayıtlı listeye
  bir ad ekleyip/çıkararak; PB-7 0036 ve 0033/0032 mutant listeleriyle; PB-8 `git diff` ve full
  check ile. Kanıtsız kriter yok.
- **G-6 Boyut:** Tek kural ailesi + bekçi, 8 kriter, bir yetenek — bölme gerekmez.

## Definition of Done
- [ ] `scripts/check` green
- [ ] Independent review done; real findings fixed, noise rejected with written rationale
- [ ] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots)
- [ ] Spec moved to `specs/done/` (immutable there)
