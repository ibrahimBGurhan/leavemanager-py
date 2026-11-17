"""Architecture rules (docs/architecture.md, Forbidden dependencies) — spec 0006 PB-5, spec 0007.

The production code is read with ast, never imported: every import (absolute and relative) and,
for the domain, every string constant and every access to the real clock is checked. A failure
names the file and the line.
"""
import ast
import pathlib
import re

import jinja2

ROOT = pathlib.Path(__file__).resolve().parent.parent
LAYERS = ("domain", "storage", "web")
WEB_FRAMEWORKS = {"flask", "werkzeug", "jinja2"}
SQL_LIBRARIES = {"sqlite3", "sqlalchemy", "psycopg", "psycopg2", "pymysql"}
HTML_TAG = re.compile(r"<[A-Za-z/]")
CLOCK_READS = {"datetime.date": {"today"}, "datetime.datetime": {"now", "utcnow", "today"}}


def layer_files(layer):
    files = sorted((ROOT / layer).rglob("*.py"))
    assert files, f"no Python files under {layer}/"
    return files


def production_files():
    return [ROOT / "app.py"] + [f for layer in LAYERS for f in layer_files(layer)]


def parse(path):
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def imports(path):
    """(line, dotted module name) for every import in the file; relative imports are resolved."""
    package = list(path.relative_to(ROOT).with_suffix("").parts[:-1])
    found = []
    for node in ast.walk(parse(path)):
        if isinstance(node, ast.Import):
            found += [(node.lineno, alias.name) for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = package[:len(package) - node.level + 1] if node.level else []
            module = base + (node.module.split(".") if node.module else [])
            if node.module:
                found.append((node.lineno, ".".join(module)))
            else:
                found += [(node.lineno, ".".join(module + [alias.name])) for alias in node.names]
    return found


def top(module):
    return module.split(".")[0]


def where(path, line):
    return f"{path.relative_to(ROOT).as_posix()}:{line}"


def datetime_names(path):
    """Local name -> "datetime", "datetime.date" or "datetime.datetime", from the file's imports."""
    names = {}
    for node in ast.walk(parse(path)):
        if isinstance(node, ast.Import):
            names.update({alias.asname or alias.name: alias.name
                          for alias in node.names if alias.name == "datetime"})
        elif isinstance(node, ast.ImportFrom) and node.module == "datetime" and not node.level:
            for alias in node.names:
                if alias.name == "*":
                    names.update({"date": "datetime.date", "datetime": "datetime.datetime"})
                elif alias.name in ("date", "datetime"):
                    names[alias.asname or alias.name] = f"datetime.{alias.name}"
    return names


def resolve(node, names):
    """What an expression names in the datetime module, or None."""
    if isinstance(node, ast.Name):
        return names.get(node.id)
    if isinstance(node, ast.Attribute) and resolve(node.value, names) == "datetime":
        return f"datetime.{node.attr}"
    return None


def test_domain_does_not_import_the_web_framework():
    """Rule 1: domain imports no flask, werkzeug or jinja2."""
    bad = [f"{where(f, line)} {m}" for f in layer_files("domain")
           for line, m in imports(f) if top(m) in WEB_FRAMEWORKS]
    assert bad == []


def test_domain_produces_no_html():
    """Rule 2: no string in the domain contains an HTML tag — presentation belongs to web."""
    bad = [f"{where(f, node.lineno)} {node.value!r}" for f in layer_files("domain")
           for node in ast.walk(parse(f))
           if isinstance(node, ast.Constant) and isinstance(node.value, str)
           and HTML_TAG.search(node.value)]
    assert bad == []


def test_web_reaches_storage_only_through_the_domain():
    """Rule 3: web never imports storage."""
    bad = [f"{where(f, line)} {m}" for f in layer_files("web")
           for line, m in imports(f) if top(m) == "storage"]
    assert bad == []


def test_sql_lives_only_in_storage():
    """Rule 4: SQL libraries are imported only inside storage."""
    bad = [f"{where(f, line)} {m}" for f in production_files()
           if f.relative_to(ROOT).parts[0] != "storage"
           for line, m in imports(f) if top(m) in SQL_LIBRARIES]
    assert bad == []


def test_domain_does_not_read_the_real_clock():
    """Rule 5: the domain never reads the real clock (date.today, datetime.now...); it is injected."""
    bad = []
    for f in layer_files("domain"):
        names = datetime_names(f)
        bad += [f"{where(f, node.lineno)} {ast.unparse(node)}" for node in ast.walk(parse(f))
                if isinstance(node, ast.Attribute)
                and node.attr in CLOCK_READS.get(resolve(node.value, names), ())]
    assert bad == []


def test_routes_reach_data_only_through_for_account():
    """Spec 0020 (plan Risk 5): every screen and action goes through the account view, so a later
    route cannot read or change data unscoped. In web/, the leave service is only ever called as
    svc.for_account(...); its data, calculation and action functions are not called directly."""
    bad = []
    for f in layer_files("web"):
        for node in ast.walk(parse(f)):
            if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                    and node.value.id == "svc" and node.attr != "for_account"):
                bad.append(f"{where(f, node.lineno)} svc.{node.attr}")
    assert bad == []


def parents(tree):
    """Node -> its parent node, for every node in the tree."""
    return {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}


def is_g_account(node):
    return (isinstance(node, ast.Attribute) and node.attr == "account"
            and isinstance(node.value, ast.Name) and node.value.id == "g")


def test_for_account_gets_the_logged_in_account():
    """Spec 0025 (issue #43, 0020 G-3): the account view is always opened for the account the gate
    set up (g.account, spec 0019). In web/, every use of svc.for_account is a call with exactly one
    positional argument, g.account, and no keyword arguments; at least one such call exists."""
    bad, calls = [], 0
    for f in layer_files("web"):
        tree = parse(f)
        up = parents(tree)
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                    and node.value.id == "svc" and node.attr == "for_account"):
                continue
            call = up.get(node)
            if (isinstance(call, ast.Call) and call.func is node and len(call.args) == 1
                    and not call.keywords and is_g_account(call.args[0])):
                calls += 1
            else:
                bad.append(f"{where(f, node.lineno)} {ast.unparse(call or node)}")
    assert bad == []
    assert calls >= 1, "no svc.for_account(g.account) call found under web/"


ACCESS = "domain.access"
LOG_PREFIX = "ACTION_"


def log_names():
    """Module-level ACTION_ names in domain/access.py: the decision log names (spec 0030)."""
    names = []
    for node in parse(ROOT / "domain" / "access.py").body:
        targets = node.targets if isinstance(node, ast.Assign) else (
            [node.target] if isinstance(node, ast.AnnAssign) else [])
        names += [t.id for t in targets if isinstance(t, ast.Name) and t.id.startswith(LOG_PREFIX)]
    return names


def from_module(path, node):
    """Dotted module an ast.ImportFrom imports from; relative imports are resolved."""
    package = list(path.relative_to(ROOT).with_suffix("").parts[:-1])
    base = package[:len(package) - node.level + 1] if node.level else []
    return ".".join(base + (node.module.split(".") if node.module else []))


def test_web_does_not_use_the_decision_log_names():
    """Spec 0031 (spec 0030 G-2): only the access layer knows the log names of refused actions;
    web/ asks by name (authorize_approve, ...) and never uses domain.access's ACTION_ names — not
    by name, alias or star import, nor as an attribute of the imported module. Written access
    only: text constants ("onay"), dynamic access and a module re-bound by assignment are left
    to review (spec Out of scope, plan Risk 2)."""
    assert log_names(), "domain/access.py: no ACTION_ log name found"
    bad = []
    for f in layer_files("web"):
        tree = parse(f)
        bound = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                bound |= {alias.asname or alias.name for alias in node.names
                          if alias.name == ACCESS}
            elif isinstance(node, ast.ImportFrom):
                module = from_module(f, node)
                if module == ACCESS:
                    bad += [f"{where(f, node.lineno)} import {alias.name}" for alias in node.names
                            if alias.name == "*" or alias.name.startswith(LOG_PREFIX)]
                bound |= {alias.asname or alias.name for alias in node.names
                          if f"{module}.{alias.name}" == ACCESS}
        for node in ast.walk(tree):
            if (isinstance(node, ast.Attribute) and node.attr.startswith(LOG_PREFIX)
                    and ast.unparse(node.value) in bound):
                bad.append(f"{where(f, node.lineno)} {ast.unparse(node)}")
    assert bad == []


TEMPLATES = ROOT / "web" / "templates"
# Kacisi kapatan kelimeler hicbir bicimde gecmez (spec 0033): autoescape(false), map('safe'), satir
# sonuyla bolunmus "| safe" … Hicbir sablon bunlara ihtiyac duymaz; desen inceltmek yeniden acik birakir.
UNESCAPED = re.compile(r"\b(?:autoescape|safe|Markup)\b", re.IGNORECASE)


def test_web_html_lives_only_in_templates():
    """Spec 0032 (ADR-0003, docs/security.md Input & output): page HTML lives only in
    web/templates/, autoescaped. web/*.py holds no string constant with an HTML tag and never
    names render_template_string; Flask route rules ("/requests/<request_id>/approve") are URL
    patterns, not HTML. web/*.py neither names Markup nor imports markupsafe. Every file under
    web/templates/ is .html (Flask autoescapes by extension) and never names autoescape, safe or
    Markup in any form; the whole file is scanned, so a line break does not hide one (spec 0033)."""
    bad = []
    for f in layer_files("web"):
        tree = parse(f)
        rules = {id(node.args[0]) for node in ast.walk(tree)
                 if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                 and node.func.attr == "route" and node.args}
        for node in ast.walk(tree):
            if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                    and id(node) not in rules and HTML_TAG.search(node.value)):
                bad.append(f"{where(f, node.lineno)} HTML {node.value[:40]!r}")
            name = (node.id if isinstance(node, ast.Name) else node.attr
                    if isinstance(node, ast.Attribute) else node.name
                    if isinstance(node, ast.alias) else None)
            if name in ("render_template_string", "Markup"):
                bad.append(f"{where(f, getattr(node, 'lineno', 0))} {name}")
        bad += [f"{where(f, line)} import {module}" for line, module in imports(f)
                if top(module) == "markupsafe"]
    bad += [f"{t.relative_to(ROOT).as_posix()} not .html (no autoescape)"
            for t in sorted(TEMPLATES.rglob("*")) if t.is_file() and t.suffix != ".html"]
    templates = sorted(TEMPLATES.rglob("*.html"))
    if not templates:
        bad.append("no templates under web/templates/")
    for t in templates:
        text = t.read_text(encoding="utf-8")
        lines = text.split("\n")  # satir numarasiyla ayni ayirici: splitlines \x0c'de de boler (F-2)
        for m in UNESCAPED.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            bad.append(f"{t.relative_to(ROOT).as_posix()}:{line} {lines[line - 1].strip()[:60]!r}")
    assert bad == []


SHELL_TEMPLATES = ("base.html", "login.html")  # spec 0034; spec 0035 ile kural tum sablonlara genisledi
# <style>, style=, on…= olay ozniteligi, src'siz <script> ya da src'li ama ici dolu <script> (CSP'ye hazirlik)
INLINE = re.compile(r"<style\b|\sstyle\s*=|\son[a-z]+\s*=|<script\b(?![^>]*\bsrc\s*=)[^>]*>"
                    r"|<script\b[^>]*>\s*[^<\s]", re.IGNORECASE)


def test_templates_have_no_inline_style_or_script():
    """Spec 0034 AC-9, widened by spec 0035 AC-11 (ADR-0003 ilke 3-4): no template carries an
    inline <style>, style= attribute, inline <script> or on…= event attribute — styling lives in
    web/static/app.css and Bootstrap's classes, behaviour in Bootstrap's vendored bundle. Every
    file under web/templates/ is scanned whole; the shell templates must be among them."""
    paths = sorted(TEMPLATES.rglob("*.html"))
    names = {p.relative_to(TEMPLATES).as_posix() for p in paths}
    assert set(SHELL_TEMPLATES) <= names and len(names) >= 7, names
    bad = []
    for path in paths:
        name = path.relative_to(TEMPLATES).as_posix()
        text = path.read_text(encoding="utf-8")
        lines = text.split("\n")
        for m in INLINE.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            bad.append(f"web/templates/{name}:{line} {lines[line - 1].strip()[:60]!r}")
    assert bad == []


# Spec 0036: sablon `_` ile baslayan hicbir ada hicbir yolla erismez, eristigi ad sablonda sabit
# yazilir: (''|e).__class__(x), |attr('_'*2 ~ 'class' ~ '_'*2), x[ad], map(attribute='__class__.x')
# kacisi kapatir ya da Python'un ic yapisina uzanir. Sablonlar calistirilmaz, duz bir Jinja
# ortaminda yalniz ayristirilir (plan 0036 Risk 2); metin ve yorumdaki "__" serbest (S-3).
NAME_FILTERS = ("attr", "map", "selectattr", "rejectattr", "groupby", "sort", "unique", "min",
                "max", "sum", "join")  # Jinja 3.1.6: oznitelik adi alan suzgecler (plan Risk 3)
FIELD_READERS = ("format", "format_map")  # '{0.__class__}'.format(x) metinden alan okur (G-1)


def name_parts(value):
    """The attribute names in a dotted or comma list (map(attribute='a.__class__'),
    sort(attribute='x,__class__')); nothing for a non-string."""
    return [part.strip() for part in re.split(r"[.,]", value)] if isinstance(value, str) else []


def underscore_name(value):
    """True when a string names an underscore attribute in any part of a dotted or comma list."""
    return any(part.startswith("_") for part in name_parts(value))


def field_reader_name(value):
    """True when a string names .format / .format_map in any part (review 0036 F-2:
    map(attribute='format') reaches it as well as attr('format'))."""
    return any(part in FIELD_READERS for part in name_parts(value))


def negative_index(arg):
    """True for a negative whole number written as a constant (x[-1] parses as Neg(Const))."""
    return (isinstance(arg, jinja2.nodes.Neg) and isinstance(arg.node, jinja2.nodes.Const)
            and type(arg.node.value) is int)


def template_access_violations(source):
    """(line, what) for every forbidden access in one template (spec 0036 PB-1, PB-2)."""
    try:
        tree = jinja2.Environment().parse(source)
    except jinja2.TemplateSyntaxError as e:  # G-2: never skipped silently
        return [(e.lineno, f"not parseable: {e.message}")]
    bad = []
    for node in tree.find_all((jinja2.nodes.Getattr, jinja2.nodes.NSRef, jinja2.nodes.Getitem,
                               jinja2.nodes.Filter)):
        if isinstance(node, (jinja2.nodes.Getattr, jinja2.nodes.NSRef)):
            if node.attr.startswith("_") or node.attr in FIELD_READERS:
                bad.append((node.lineno, f"attribute {node.attr!r}"))
        elif isinstance(node, jinja2.nodes.Getitem):
            if negative_index(node.arg):  # x[-1] is an index written as a constant (review F-3)
                continue
            if not isinstance(node.arg, jinja2.nodes.Const):
                bad.append((node.lineno, "computed key"))
            elif isinstance(node.arg.value, str) and (node.arg.value.startswith("_")
                                                     or node.arg.value in FIELD_READERS):
                bad.append((node.lineno, f"key {node.arg.value!r}"))
        elif node.name in NAME_FILTERS:
            if node.dyn_args is not None or node.dyn_kwargs is not None:
                bad.append((node.lineno, f"{node.name}: computed arguments"))
            for arg in node.args + [kw.value for kw in node.kwargs]:
                if not isinstance(arg, jinja2.nodes.Const):
                    bad.append((node.lineno, f"{node.name}: computed name"))
                elif underscore_name(arg.value) or field_reader_name(arg.value):
                    bad.append((node.lineno, f"{node.name}: {arg.value!r}"))
    return bad


def test_templates_never_reach_underscore_names():
    """Spec 0036 (follow-up of 0033 F-1; docs/security.md Input & output): no template reaches a
    name starting with "_" by any path — dot, brackets, the attr filter, or a filter's attribute
    argument (dotted and comma lists too) — and every name it reaches is written as a constant:
    computed keys and names are refused. Reading fields through .format / .format_map is refused.
    A template that does not parse is reported, not skipped. Plain text and comments may hold
    "__"; template file names (_macros.html) are not accesses."""
    paths = sorted(TEMPLATES.rglob("*.html"))
    assert len(paths) >= 7
    bad = [f"web/templates/{p.relative_to(TEMPLATES).as_posix()}:{line} {what}"
           for p in paths
           for line, what in template_access_violations(p.read_text(encoding="utf-8"))]
    assert bad == []


# Spec 0037 (0036 F-1 takibi): altcizgi kullanmadan kacisi kapatan iki yol. indent'e metin olarak
# verilen genislik ve translate'e verilen tablonun degerleri Markup'in icine kacissiz girer:
# ('a\nb'|e)|indent(x) -> 'a\n<b>b', ('a'|e).translate({97: x}) -> '<b>'. 0036'nin yardimcilari
# yalniz okunur; 0036/0033/0032 kurallari degismez (PB-7).
NO_ESCAPE_METHODS = ("translate",)  # spec 0037 S-3: tablo sabit olsa da ham '<' uretir


def constant_whole_number(arg):
    """True for a whole number written in the template (4, -1); a bool is not one (S-2)."""
    return ((isinstance(arg, jinja2.nodes.Const) and type(arg.value) is int)
            or negative_index(arg))


def indent_width(node):
    """The width argument of an indent filter node, positional or width=; None when absent."""
    if node.args:
        return node.args[0]
    return next((kw.value for kw in node.kwargs if kw.key == "width"), None)


def indent_translate_violations(source):
    """(line, what) for every indent with a non-constant width, every translate access and every
    map('indent', ...) in one template (spec 0037 PB-1, PB-2, PB-3)."""
    try:
        tree = jinja2.Environment().parse(source)
    except jinja2.TemplateSyntaxError as e:  # 0036 G-2 ile ayni: sessizce atlanmaz
        return [(e.lineno, f"not parseable: {e.message}")]
    bad = []
    for node in tree.find_all((jinja2.nodes.Getattr, jinja2.nodes.NSRef, jinja2.nodes.Getitem,
                               jinja2.nodes.Filter)):  # Filter: |indent ve {% filter indent %}
        if isinstance(node, (jinja2.nodes.Getattr, jinja2.nodes.NSRef)):
            if node.attr in NO_ESCAPE_METHODS:
                bad.append((node.lineno, f"attribute {node.attr!r}"))
        elif isinstance(node, jinja2.nodes.Getitem):
            if isinstance(node.arg, jinja2.nodes.Const) and node.arg.value in NO_ESCAPE_METHODS:
                bad.append((node.lineno, f"key {node.arg.value!r}"))
        elif node.name == "indent":
            width = indent_width(node)
            if node.dyn_args is not None or node.dyn_kwargs is not None:
                bad.append((node.lineno, "indent: computed arguments"))
            elif width is not None and not constant_whole_number(width):
                bad.append((node.lineno, "indent: width is not a constant whole number"))
        elif node.name in NAME_FILTERS:
            # her konum: map('map', 'indent', '<b>') indent'i ic ice map'le cagirir (review F-1)
            if node.name == "map" and any(isinstance(arg, jinja2.nodes.Const) and arg.value == "indent"
                                          for arg in node.args):
                bad.append((node.lineno, "map: filter 'indent'"))
            for arg in node.args + [kw.value for kw in node.kwargs]:
                if (isinstance(arg, jinja2.nodes.Const)
                        and any(part in NO_ESCAPE_METHODS for part in name_parts(arg.value))):
                    bad.append((node.lineno, f"{node.name}: {arg.value!r}"))
    return bad


def test_templates_never_use_indent_text_or_translate():
    """Spec 0037 (follow-up of 0036 F-1; docs/security.md Input & output): indent takes no width
    or a whole number written in the template — a text, variable, expression or true/false width
    is refused, in |indent and {% filter indent %} alike, and so are *args / **kwargs. translate
    is reached by no path (dot, brackets, attr, a filter's attribute argument), even with a
    constant table. map('indent', ...) is refused whatever its arguments. Plain text and comments
    may hold the words."""
    paths = sorted(TEMPLATES.rglob("*.html"))
    assert len(paths) >= 7
    bad = [f"web/templates/{p.relative_to(TEMPLATES).as_posix()}:{line} {what}"
           for p in paths
           for line, what in indent_translate_violations(p.read_text(encoding="utf-8"))]
    assert bad == []


# Spec 0037 S-4 (yukseltme bekcisi): ANALYZE taramasi (spec 0037 Gozlem) Jinja 3.1.6, MarkupSafe
# 3.0.4, Flask 3.1.3 ve Python 3.13'te bu adlarin her birini kullanici metniyle denedi; kacisi
# kapatan yalniz indent ve translate cikti. Kume degisirse yeni ad taranmamistir.
SCANNED_FILTERS = (
    "abs", "attr", "batch", "capitalize", "center", "count", "d", "default", "dictsort", "e",
    "escape", "filesizeformat", "first", "float", "forceescape", "format", "groupby", "indent",
    "int", "items", "join", "last", "length", "list", "lower", "map", "max", "min", "pprint",
    "random", "reject", "rejectattr", "replace", "reverse", "round", "safe", "select",
    "selectattr", "slice", "sort", "string", "striptags", "sum", "title", "tojson", "trim",
    "truncate", "unique", "upper", "urlencode", "urlize", "wordcount", "wordwrap", "xmlattr")
SCANNED_MARKUP_METHODS = (
    "capitalize", "casefold", "center", "count", "encode", "endswith", "escape", "expandtabs",
    "find", "format", "format_map", "index", "isalnum", "isalpha", "isascii", "isdecimal",
    "isdigit", "isidentifier", "islower", "isnumeric", "isprintable", "isspace", "istitle",
    "isupper", "join", "ljust", "lower", "lstrip", "maketrans", "partition", "removeprefix",
    "removesuffix", "replace", "rfind", "rindex", "rjust", "rpartition", "rsplit", "rstrip",
    "split", "splitlines", "startswith", "strip", "striptags", "swapcase", "title", "translate",
    "unescape", "upper", "zfill")
# Ad degistirmeyen ama davranis degistiren bir yukseltme de taranmamistir (review 0037 F-2);
# requirements.txt bu surumleri sabitler (plan Risk 2).
SCANNED_VERSIONS = {"jinja2": "3.1.6", "markupsafe": "3.0.4", "flask": "3.1.3"}


def name_set_difference(found, scanned):
    """'added [...], removed [...]' between the names found now and the scanned list; '' when equal."""
    added, removed = sorted(set(found) - set(scanned)), sorted(set(scanned) - set(found))
    return f"added {added}, removed {removed}" if added or removed else ""


def test_template_library_surface_is_known():
    """Spec 0037 PB-6 (S-4, G-1…G-3): the filter names in a bare Flask application's template
    environment and the public names of markupsafe.Markup equal the lists scanned in ANALYZE.
    An upgrade of Jinja, Flask, MarkupSafe or Python that adds or removes a name turns this red,
    naming the difference, and so does any installed Jinja, MarkupSafe or Flask version other
    than the scanned one, even with the same names (review F-2): re-run the observation scan of
    spec 0037 before updating the lists and versions. The application itself (app.py) is not
    imported."""
    import importlib.metadata

    import flask  # kutuphane, uretim kodu degil: mimari testleri app.py'yi import etmez
    import markupsafe

    filters = flask.Flask("bekci").jinja_env.filters
    methods = [name for name in dir(markupsafe.Markup) if not name.startswith("_")]
    bad = [f"{what}: {diff} — spec 0037 Gozlem taramasini yeniden kos"
           for what, diff in (("filters", name_set_difference(filters, SCANNED_FILTERS)),
                              ("Markup methods", name_set_difference(methods, SCANNED_MARKUP_METHODS)))
           if diff]
    bad += [f"{package} {importlib.metadata.version(package)} != scanned {scanned}"
            " — spec 0037 Gozlem taramasini yeniden kos"
            for package, scanned in SCANNED_VERSIONS.items()
            if importlib.metadata.version(package) != scanned]
    assert bad == []
