# HTTP: route'lar, form girdisi, sayfa ve durum rozeti. Veriye yalniz servis uzerinden erisir.
from datetime import datetime

from flask import request, redirect, render_template_string
from markupsafe import escape

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

    @app.route("/new", methods=["GET", "POST"])
    def new_request():
        if request.method == "POST":
            try:
                emp_id = int(request.form["employee_id"])
                start = datetime.strptime(request.form["start"], "%Y-%m-%d").date()
                end = datetime.strptime(request.form["end"], "%Y-%m-%d").date()
                emp = [e for e in svc.employees() if e["id"] == emp_id][0]
                days = (end - start).days + 1
                # bakiye kontrolu (serviste de var ama formda erken uyari iyi oluyor)
                if svc.get_remaining(emp) < days:
                    return render_template_string(PAGE, body="<p style='color:red'>HATA: ERR-412 NullReferenceGibi - bakiye yetersiz. IT'ye bildirin: dahili 4127</p>")
                svc.create_request(emp_id, start, end, request.form.get("reason", ""))
                return redirect("/requests")
            except Exception:
                # loglanacak
                return redirect("/requests")
        options = "".join("<option value='%d'>%s</option>" % (e["id"], escape(e["name"])) for e in svc.employees())
        body = """<h3>Yeni Talep</h3><form method="post">
    Personel: <select name="employee_id">%s</select><br><br>
    Baslangic: <input type="date" name="start"><br><br>
    Bitis: <input type="date" name="end"><br><br>
    Neden: <input type="text" name="reason"><br><br>
    <input type="submit" value="Kaydet"></form>""" % options
        return render_template_string(PAGE, body=body)
