"""Bootstrap shell and login screen — spec 0034 (ADR-0003, plan 0034).

Bootstrap is vendored under web/static/vendor/ and served by the app itself; its files are pinned
by SHA-256 (plan 0034 "Sabitlenen özetler"). Static files need no login; screens still do (G-3).
"""
import hashlib
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
VENDOR = ROOT / "web" / "static" / "vendor" / "bootstrap-5.3.8"
PINNED = {  # plan 0034, Sabitlenen özetler — doğrulandı: release zip SHA-256 + config.yml SRI
    "bootstrap.min.css": "d85327d99c7a3ee1f9b5d0500d1370acea3ad2db39c163c2f51f232baedbdede",
    "bootstrap.bundle.min.js": "e4fd49181388c48ec5040bd3fe66f57c29c8e67fcd8502b3354b96ec7ab47cc7",
}
STATIC = ["/static/vendor/bootstrap-5.3.8/bootstrap.min.css",
          "/static/vendor/bootstrap-5.3.8/bootstrap.bundle.min.js"]


@pytest.mark.parametrize("name", sorted(PINNED))
def test_vendored_bootstrap_matches_pinned_sha256(name):
    """AC-2: a single changed byte (or a line-ending conversion, plan Risk 9) turns this red."""
    assert hashlib.sha256((VENDOR / name).read_bytes()).hexdigest() == PINNED[name]


@pytest.mark.usefixtures("logged_out")
def test_static_needs_no_login_screens_do(client):
    """G-3: the login screen's CSS loads before login; screens still go to the login page."""
    for path in STATIC:
        resp = client.get(path)
        assert resp.status_code == 200, path
        assert resp.data == (VENDOR / path.rsplit("/", 1)[1]).read_bytes()
    for path in ("/", "/requests", "/new", "/personel/yeni"):
        resp = client.get(path)
        assert resp.status_code == 302 and resp.headers["Location"] == "/giris", path


@pytest.mark.usefixtures("logged_out")
def test_static_serves_only_files_under_static(client):
    """G-3: the open endpoint does not reach outside web/static/."""
    for path in ("/static/../app.py", "/static/..%2fapp.py", "/static/vendor/../../templates/base.html"):
        assert client.get(path).status_code == 404, path
