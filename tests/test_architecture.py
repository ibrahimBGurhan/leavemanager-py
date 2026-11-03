"""Architecture rules (docs/architecture.md, Forbidden dependencies) — spec 0006, PB-5.

The production code is read with ast, never imported: every import (absolute and relative) and,
for the domain, every string constant is checked. A failure names the file and the line.
"""
import ast
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
LAYERS = ("domain", "storage", "web")
WEB_FRAMEWORKS = {"flask", "werkzeug", "jinja2"}
SQL_LIBRARIES = {"sqlite3", "sqlalchemy", "psycopg", "psycopg2", "pymysql"}
HTML_TAG = re.compile(r"<[A-Za-z/]")


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
