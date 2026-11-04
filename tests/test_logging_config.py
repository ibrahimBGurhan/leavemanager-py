"""Log configuration — spec 0009.

Logging is process-wide and pytest installs its own handlers, so the app's configuration is
checked in a separate Python process: it loads the app (as a WSGI server would, or as
`python app.py`), serves two real requests through Werkzeug and reports nothing on stdout.
GET / produces Werkzeug's INFO request line; POST /new with a broken storage produces the
ERROR record with its stack trace (spec 0008, CB-5).
"""
import inspect
import os
import pathlib
import re
import runpy
import subprocess
import sys

import flask
import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP_PY = ROOT / "app.py"
TIMESTAMP = r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d{3}"
ERROR_LINE = re.compile(rf"^{TIMESTAMP} ERROR web\.routes: izin talebi kaydedilemedi$")
REQUEST_LINE = re.compile(rf'^{TIMESTAMP} INFO werkzeug: .*"GET / HTTP/1\.1" 200')
DEBUG_LINE = re.compile(rf"^{TIMESTAMP} DEBUG web\.routes: debug kaydi$")

SCRIPT = r'''
import logging, sys, threading, urllib.error, urllib.parse, urllib.request

import flask
from werkzeug.serving import make_server

from storage.memory import MemoryStorage

entry, app_py = sys.argv[1], sys.argv[2]


def broken(self, record):
    raise RuntimeError("gizli ayrinti")


def serve(flask_app):
    # the app writes no DEBUG record of its own; this one shows whether DEBUG is let through
    logging.getLogger("web.routes").debug("debug kaydi")
    server = make_server("127.0.0.1", 0, flask_app)
    worker = threading.Thread(target=lambda: [server.handle_request() for _ in range(2)],
                              daemon=True)
    worker.start()
    base = "http://127.0.0.1:%d" % server.server_port
    urllib.request.urlopen(base + "/", timeout=10).read()
    form = urllib.parse.urlencode({"employee_id": "2", "start": "2026-11-16",
                                   "end": "2026-11-16", "reason": "x"}).encode()
    try:
        urllib.request.urlopen(base + "/new", data=form, timeout=10)
        status = 200
    except urllib.error.HTTPError as err:
        status = err.code
    worker.join(10)
    if status != 500:
        sys.exit(3)


MemoryStorage.add_request = broken
if entry == "import":
    import app
    serve(app.app)
else:
    flask.Flask.run = lambda self, *args, **kwargs: serve(self)
    import runpy
    runpy.run_path(app_py, run_name="__main__")
'''


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    """run(entry, level) -> (process, working dir); one process per (entry, level)."""
    cache = {}

    def _run(entry="import", level=None):
        if (entry, level) not in cache:
            workdir = tmp_path_factory.mktemp("run")
            env = {k: v for k, v in os.environ.items() if k not in ("LOG_LEVEL", "FLASK_DEBUG")}
            env.update(PYTHONPATH=str(ROOT), PYTHONIOENCODING="utf-8")
            if level is not None:
                env["LOG_LEVEL"] = level
            proc = subprocess.run(
                [sys.executable, "-c", SCRIPT, entry, str(APP_PY)], cwd=workdir, env=env,
                capture_output=True, encoding="utf-8", timeout=30)
            assert proc.returncode == 0, proc.stderr
            cache[entry, level] = (proc, workdir)
        return cache[entry, level]

    return _run


ENTRIES = pytest.mark.parametrize("entry", ["import", "main"])


@ENTRIES
def test_log_line_has_time_level_logger_and_message(run, entry):
    """CB-1, CB-6: zaman, seviye, logger adı, mesaj; stack trace hemen altında."""
    lines = run(entry)[0].stderr.splitlines()
    at = [i for i, line in enumerate(lines) if ERROR_LINE.match(line)]
    assert len(at) == 1, lines
    assert lines[at[0] + 1].startswith("Traceback")


def test_logs_go_to_stderr_only(run):
    """CB-2: loglar stderr'de; stdout boş; log dosyası oluşmaz."""
    proc, workdir = run()
    assert proc.stdout == ""
    assert any(ERROR_LINE.match(line) for line in proc.stderr.splitlines())
    assert list(workdir.iterdir()) == []


@ENTRIES
@pytest.mark.parametrize(
    "level, debug_line, request_line, error_line",
    [(None, False, True, True), ("", False, True, True), ("  ", False, True, True),
     ("debug", True, True, True), ("WARNING", False, False, True), ("error", False, False, True),
     ("ERROR", False, False, True), ("CRITICAL", False, False, False)],
    ids=["unset", "empty", "blank", "debug-lower", "warning", "error-lower", "error", "critical"],
)
def test_level_from_env(run, entry, level, debug_line, request_line, error_line):
    """CB-3, CB-6: varsayılan INFO; büyük/küçük harf fark etmez; altındaki kayıtlar yazılmaz;
    geçerli ya da boş değer uyarı üretmez (CB-4 yalnızca tanınmayan değer içindir)."""
    lines = run(entry, level)[0].stderr.splitlines()
    assert any(DEBUG_LINE.match(line) for line in lines) is debug_line
    assert any(REQUEST_LINE.match(line) for line in lines) is request_line
    assert any(ERROR_LINE.match(line) for line in lines) is error_line
    assert not [line for line in lines if " WARNING app: " in line]


@pytest.mark.parametrize("level", ["verbose", "WARN", "10"])
def test_invalid_level_falls_back_to_info_with_one_warning(run, level):
    """CB-4 (S-2, R-3): uygulama başlar, seviye INFO, bir WARNING satırı."""
    lines = run("import", level)[0].stderr.splitlines()
    warnings = [line for line in lines if re.match(rf"^{TIMESTAMP} WARNING app: ", line)]
    assert len(warnings) == 1, lines
    assert repr(level) in warnings[0]
    assert "INFO" in warnings[0]
    assert any(REQUEST_LINE.match(line) for line in lines)


@ENTRIES
def test_each_event_is_logged_once(run, entry):
    """CB-5, CB-6: istek satırı ve beklenmeyen hata birer kez, CB-1 biçiminde."""
    proc = run(entry)[0]
    requests = [line for line in proc.stderr.splitlines() if '"GET / HTTP/1.1"' in line]
    assert len(requests) == 1, requests
    assert REQUEST_LINE.match(requests[0])
    assert proc.stderr.count("izin talebi kaydedilemedi") == 1


def test_shell_log_level_does_not_reach_the_suite(tmp_path):
    """S-6, PB-4: LOG_LEVEL=CRITICAL in the shell; the caplog test of spec 0008 still sees ERROR."""
    env = dict(os.environ, LOG_LEVEL="CRITICAL", PYTHONIOENCODING="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--rootdir", str(ROOT),
         "-c", str(ROOT / "pytest.ini"),
         str(ROOT / "tests" / "test_request_errors.py::test_screen_unexpected_error_is_logged_not_shown")],
        cwd=tmp_path, env=env, capture_output=True, encoding="utf-8", timeout=60)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_log_level_debug_does_not_enable_debug_mode(monkeypatch):
    """PB-2: LOG_LEVEL=DEBUG Werkzeug debugger'ını ya da Flask debug modunu açmaz."""
    run_signature = inspect.signature(flask.Flask.run)
    calls = []

    def fake_run(self, *args, **kwargs):
        calls.append((self, run_signature.bind(self, *args, **kwargs).arguments))

    monkeypatch.setattr(flask.Flask, "run", fake_run)
    monkeypatch.delenv("FLASK_DEBUG", raising=False)
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    runpy.run_path(str(APP_PY), run_name="__main__")

    assert len(calls) == 1
    flask_app, arguments = calls[0]
    assert not arguments.get("debug")
    assert not arguments.get("options", {}).get("use_debugger")
    assert not flask_app.debug
