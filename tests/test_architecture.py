"""Architecture rules (docs/architecture.md, Forbidden dependencies) — spec 0006 PB-5, spec 0007.

The production code is read with ast, never imported: every import (absolute and relative) and,
for the domain, every string constant and every access to the real clock is checked. A failure
names the file and the line.
"""
import ast
import pathlib
import re

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
