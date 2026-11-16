# Spec 0033 — sablon-kacis-kelime-yasagi (mini)

- Status: In progress
- Mode: lite
- Plan: `specs/plans/0033-plan.md`
- Source: spec 0032 review round 2 I-1 (`specs/plans/0032-plan.md`, "Triage (review round 2)":
  "**Takip işi (sonra):** şablonda `autoescape` kelimesinin herhangi bir biçimde geçmesini
  yasaklamak"); istek: İbrahim Gürhan, 2026-11-16 (`/change`, I-1 takibi)
- Design: — (arayüz yok)
- Supersedes: 0032/PB-4 (yalnız şablon kuralı: "`autoescape false` yok" → "`autoescape` hiç yok";
  `specs/done/` düzenlenmez)

## Intent
Ekranlardaki kullanıcı verisi yalnız Jinja'nın otomatik kaçışı sayesinde zararsız basılır
(`docs/security.md`, spec 0032). Bugünkü mimari testi kaçışı kapatan yazımların bir kısmını
yakalıyor ama bazı biçimler testten kaçıyor. Bu iş davranışı değiştirmez; kuralı sıkılaştırır:
şablonlarda kaçışı kapatmaya yarayan kelimeler hiçbir biçimde geçemez, böylece kaçışın kazara ya
da bilerek kapatılması `scripts/check`'te kırmızıya düşer.

Triage kaydı (2026-11-16, İbrahim Gürhan onayı: "onaylıyorum"): (a) hata değil — bugünkü
şablonlar 0032 PB-4'e uyuyor, kalan atlatmalar 0032 round 2'de I-1 olarak "noise + takip işi"
kaydedildi; (b) kabul kriteri değişiyor (0032/PB-4 sıkılaşıyor) ve mevcut bir test düzenleniyor —
trivial lane'in "test değişirse yeniden triage" kuralı; (c) ortak üretim kodu yok (yalnız
`tests/test_architecture.py`) → CHANGE lane, mini-spec (0029, 0031 kalıbı).

### Gözlem (ANALYZE, 2026-11-16, HEAD `9ff2fc9`; Jinja 3.1.6, Flask 3.1.3)
Repo dışı bir betikte, otomatik kaçışı açık bir Jinja ortamında `x = "<b>"` ile denendi; "bugünkü
test" sütunu `test_web_html_lives_only_in_templates`'in satır satır uyguladığı desen
(`\|\s*safe\b|\bMarkup\b|\bautoescape\s+(?!true\b)`):

| Yazım | Çıktı kaçışsız mı | Bugünkü test yakalar mı |
|---|---|---|
| `{% autoescape(false) %}` | evet | hayır |
| `{% autoescape true and false %}` | evet | hayır |
| `{% autoescape` + satır sonu + `false %}` | evet | hayır |
| `{{ [x]\|map('safe')\|join }}` | evet | hayır |
| `{{ x \|` + satır sonu + `safe }}` | evet | hayır |
| `{% filter safe %}…{% endfilter %}` | hayır (yine kaçışlı) | hayır |
| `{{ x\|safe }}` (kontrol) | evet | evet |

- Bugün `web/templates/` altındaki hiçbir dosyada `autoescape`, `safe` ya da `Markup` kelimesi
  geçmiyor (büyük/küçük harf duyarsız, kelime olarak).
- Test şablonları satır satır tarıyor; satır sonuyla bölünen yazımları bu yüzden göremiyor.

## Changed behavior
none — no observable behavior change (ekranlar, HTTP, loglar aynı). Değişen yalnız yapısal kural;
kanıtı aşağıdaki Preserved behavior kriterleri taşır.

## Preserved behavior
- [ ] PB-1 — **Kelime kuralı:** `web/templates/` altındaki hiçbir şablonda `autoescape` ve `safe`
  kelimeleri hiçbir biçimde geçmez (büyük/küçük harf duyarsız, kelime olarak; parantezli, ifadeli,
  satır sonuyla bölünmüş, yorum içinde de). `Markup` yasağı aynen sürer. İhlalde test dosyayı ve
  satırı adlandırarak kırmızıya düşer.
- [ ] PB-2 — **Gözlemdeki her atlatma yakalanır:** Gözlem tablosundaki beş kaçışsız yazımın her
  biri (ve `|safe`, `autoescape false`, `autoescape off`) bir şablona eklenince test kırmızı
  (VERIFY'da repo dışı kopyada mutantla).
- [ ] PB-3 — **0032 kuralının geri kalanı aynen sürer:** `web/*.py`'de HTML etiketli string sabiti,
  `render_template_string`, `Markup` adı ve `markupsafe` importu yasak; `web/templates/` altındaki
  her dosya `.html`; en az bir şablon bulunmalı. 0032 VERIFY'daki mutantlar (HTML sabiti,
  `render_template_string`, `.txt` şablon, `markupsafe`, `Markup = str`) yine kırmızı.
- [ ] PB-4 — **Bugünkü kod yeşil, başka hiçbir şey değişmez:** üretim kodu ve şablonlar değişmez
  (`git diff main...HEAD -- web app.py domain storage` boş); `tests/` altında yalnız
  `test_web_html_lives_only_in_templates` ve onun deseni değişir, başka test değişmez, silinmez,
  zayıflatılmaz; `scripts/check` full yeşil.

## Out of scope
- Şablonlarda kaçışı kapatabilecek başka yollar (ör. Python'dan şablona `Markup` nesnesi geçirmek):
  `web/*.py`'deki `Markup` / `markupsafe` yasağı bunu zaten kapatır; ek bir şey yapılmaz.
- `{% filter safe %}`: bu Jinja sürümünde kaçışı kapatmıyor; yine de PB-1'in kelime kuralı onu da
  yasaklar (yan etki, amaç değil).
- Üretim kodu, şablonlar, `docs/security.md` metni (kural zaten "otomatik kaçış açık" diyor; test
  adı ve atfı değişmez).

## Decisions (ANALYZE; onay: İbrahim Gürhan, 2026-11-16 — S-1…S-4 ve G-1…G-4 önerildiği gibi)
- **S-1 Kelime yasağı, desen değil:** Şablonlarda `\bautoescape\b` ve `\bsafe\b` (büyük/küçük harf
  duyarsız) hiç geçemez; `Markup` yasağı sürer. *Öneri: kabul* — tüm şablonlar `.html` ve zaten
  otomatik kaçışlı; hiçbir şablon bu kelimelere ihtiyaç duymaz. Parantez, ifade, `map('safe')`
  gibi her biçimi tek kuralla kapatır; desen inceltmek her yeni yazımda yeniden açık bırakırdı
  (I-1'in dersi).
- **S-2 Dosyanın tamamı taranır:** Desen satır satır değil dosya metninin tamamında aranır;
  ihlal satırı eşleşmenin konumundan hesaplanıp raporlanır. *Öneri: kabul* — satır sonuyla bölünen
  yazımları kapatmanın tek yolu; kelime yasağıyla birlikte bölünmüş `autoescape\nfalse` zaten
  `autoescape` kelimesiyle yakalanır, ama `|` + satır sonu + `safe` gibi gelecekteki çok satırlı
  kalıplar için de doğru taban.
- **S-3 Mevcut testin içinde değişiklik, yeni test değil:** `UNESCAPED` deseni ve şablon döngüsü
  `test_web_html_lives_only_in_templates` içinde değişir; docstring ve yorum yeni kurala göre
  güncellenir. *Öneri: kabul* — aynı kuralın iki testte bölünmesi okuyanı yanıltır. Bu bir
  sıkılaştırma: eski desenin yakaladığı her şeyi yeni kural da yakalar (PB-2, PB-3 mutantlarla
  kanıtlar), dolayısıyla AGENTS.md kural 5 ("zayıflatma yok") korunur.
- **S-4 Dal:** `test/0033-sablon-kacis-kelime-yasagi` (`docs/git.md`, Branching; 0029/0031 kalıbı).
  *Öneri: kabul.*

## Self-critique (ANALYZE)
- **G-1 Yanlış pozitif:** Gelecekte bir şablonda düz metin olarak "safe" kelimesi (ör. İngilizce bir
  ileti) geçerse test kırmızı olur. Bugün tüm metinler Türkçe; olursa kural bilinçli gevşetilir
  (yeni spec). *Öneri: kabul edilen risk* — sessiz bir atlatmadan iyidir.
- **G-2 Yorumlar da taranır:** `{# … autoescape … #}` yorumu da kırmızı yapar. *Öneri: kabul* —
  yorumları ayıklamak testi karmaşıklaştırır ve yorumla gizlenen bir ifade riskini doğurur; bugün
  hiçbir yorumda bu kelimeler yok.
- **G-3 Test edilebilirlik:** PB-1/PB-2 mutantlarla (repo dışı kopya, 0025–0032 kalıbı), PB-3
  0032'nin mutant listesiyle, PB-4 `git diff` ve full check ile. Kanıtsız kriter yok.
- **G-4 Boyut:** Tek kural, 4 kriter, tek dosya — bölme gerekmez.

## Definition of Done
- [ ] `scripts/check` green
- [ ] Independent review done; real findings fixed, noise rejected with written rationale
- [ ] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots)
- [ ] Spec moved to `specs/done/` (immutable there)
