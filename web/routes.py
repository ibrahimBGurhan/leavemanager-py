# HTTP: route'lar, form girdisi, sayfa ve durum rozeti. Veriye yalniz servis uzerinden erisir.
import logging
from datetime import datetime

from flask import request, redirect, render_template_string
from markupsafe import escape

from domain.errors import EmployeeNotFound, InsufficientBalance, InvalidDateRange

logger = logging.getLogger(__name__)

# Kullaniciya giden hata mesajlari (spec 0008); ic kod ve ayrinti icermez.
MSG_INVALID_INPUT = "Lütfen personeli ve geçerli başlangıç ve bitiş tarihlerini girin."
MSG_EMPLOYEE_NOT_FOUND = "Seçilen personel bulunamadı."
MSG_INVALID_DATE_RANGE = "Bitiş tarihi başlangıç tarihinden önce olamaz."
MSG_INSUFFICIENT_BALANCE = "Kalan izin bakiyeniz yetersiz (kalan %d gün, talep %d gün)."
MSG_UNEXPECTED = "Talep kaydedilemedi. Lütfen daha sonra tekrar deneyin."

PAGE = """
<html><head><meta charset="utf-8"><title>LeaveManager</title>
<style>body{font-family:Arial;margin:30px} table{border-collapse:collapse}
td,th{border:1px solid #ccc;padding:6px 10px} .kutu{display:inline-block;border:1px solid #ccc;padding:10px 20px;margin-right:10px}</style>
</head><body>
<h2>LeaveManager</h2>
<p><a href="/">Ana Sayfa</a> | <a href="/requests">Talepler</a> | <a href="/new">Yeni Talep</a></p>
{{ body|safe }}
</body></html>
"""


def status_badge(status):
    # renkler: UI isi
    color = "#999"
    if status == "Onaylandi":
        color = "green"
    if status.lower() == "beklemede":
        color = "orange"
    if status == "Reddedildi":
        color = "red"
    return "<b style='color:%s'>%s</b>" % (color, status)


def register_routes(app, svc):

    @app.route("/")
    def dashboard():
        bekleyen = len([r for r in svc.requests() if r["status"] == "Beklemede"])
        onaylanan = len([r for r in svc.requests() if r["status"] == "Onaylandi"])
        reddedilen = len([r for r in svc.requests() if r["status"] == "Reddedildi"])
        body = "<div class='kutu'>Bekleyen: <b>%d</b></div><div class='kutu'>Onaylanan: <b>%d</b></div><div class='kutu'>Reddedilen: <b>%d</b></div>" % (bekleyen, onaylanan, reddedilen)
        body += "<h3>Personel Bakiyeleri</h3><table><tr><th>Ad</th><th>Birim</th><th>Hak</th><th>Kullanilan</th><th>Kalan</th></tr>"
        for e in svc.employees():
            body += "<tr><td>%s</td><td>%s</td><td>%d</td><td>%d</td><td>%d</td></tr>" % (
                escape(e["name"]), escape(e["department"]), svc.get_entitlement(e), svc.get_used_days(e["id"]), svc.get_remaining(e))
        body += "</table>"
        return render_template_string(PAGE, body=body)

    @app.route("/requests")
    def list_requests():
        body = "<h3>Izin Talepleri</h3><table><tr><th>Personel</th><th>Baslangic</th><th>Bitis</th><th>Gun</th><th>Neden</th><th>Durum</th></tr>"
        for r in svc.requests():
            emp = [e for e in svc.employees() if e["id"] == r["employee_id"]][0]
            body += "<tr><td>%s</td><td>%s</td><td>%s</td><td>%d</td><td>%s</td><td>%s</td></tr>" % (
                escape(emp["name"]), r["start"], r["end"], svc.calc_days(r["start"], r["end"]), escape(r["reason"]), status_badge(r["status"]))
        body += "</table>"
        return render_template_string(PAGE, body=body)

    def new_request_form(message=None):
        options = "".join("<option value='%d'>%s</option>" % (e["id"], escape(e["name"])) for e in svc.employees())
        body = """<h3>Yeni Talep</h3><form method="post">
    Personel: <select name="employee_id">%s</select><br><br>
    Baslangic: <input type="date" name="start"><br><br>
    Bitis: <input type="date" name="end"><br><br>
    Neden: <input type="text" name="reason"><br><br>
    <input type="submit" value="Kaydet"></form>""" % options
        if message is not None:
            body = "<p style='color:red'>%s</p>" % escape(message) + body
        return render_template_string(PAGE, body=body)

    @app.route("/new", methods=["GET", "POST"])
    def new_request():
        if request.method == "POST":
            # Ihlal sirasi: bozuk girdi -> personel -> tarih araligi -> bakiye (spec 0008, S-4)
            try:
                emp_id = int(request.form["employee_id"])
                start = datetime.strptime(request.form["start"], "%Y-%m-%d").date()
                end = datetime.strptime(request.form["end"], "%Y-%m-%d").date()
            except (KeyError, ValueError):
                return new_request_form(MSG_INVALID_INPUT), 400
            try:
                svc.create_request(emp_id, start, end, request.form.get("reason", ""))
            except EmployeeNotFound:
                return new_request_form(MSG_EMPLOYEE_NOT_FOUND), 400
            except InvalidDateRange:
                return new_request_form(MSG_INVALID_DATE_RANGE), 400
            except InsufficientBalance as e:
                return new_request_form(MSG_INSUFFICIENT_BALANCE % (e.remaining, e.requested)), 400
            except Exception:
                # beklenmeyen hata: ayrinti loga, kullaniciya genel mesaj (docs/conventions.md)
                logger.exception("izin talebi kaydedilemedi")
                return new_request_form(MSG_UNEXPECTED), 500
            return redirect("/requests")
        return new_request_form()
