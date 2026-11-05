# HTTP: route'lar, form girdisi, sayfa ve durum rozeti. Veriye yalniz servis uzerinden erisir.
import logging
from datetime import datetime

from flask import current_app, request, redirect, render_template_string
from flask_wtf.csrf import CSRFError, generate_csrf
from markupsafe import escape

from domain.errors import (EmployeeNotFound, InsufficientBalance, InvalidDateRange,
                           NoWorkingDays, RequestAlreadyDecided, RequestNotFound)
from domain.leave_service import APPROVED, PENDING, REJECTED

logger = logging.getLogger(__name__)

# Kullaniciya giden hata mesajlari (spec 0008); ic kod ve ayrinti icermez.
MSG_INVALID_INPUT = "Lütfen personeli ve geçerli başlangıç ve bitiş tarihlerini girin."
MSG_EMPLOYEE_NOT_FOUND = "Seçilen personel bulunamadı."
MSG_INVALID_DATE_RANGE = "Bitiş tarihi başlangıç tarihinden önce olamaz."
MSG_INSUFFICIENT_BALANCE = "Kalan izin bakiyeniz yetersiz (kalan %d gün, bekleyen %d gün, talep %d gün)."  # 0013
MSG_UNEXPECTED = "Talep kaydedilemedi. Lütfen daha sonra tekrar deneyin."
MSG_NO_WORKING_DAYS = "Seçilen tarihler arasında iş günü yok."  # spec 0014 K-5
# Onay / red (spec 0010)
MSG_APPROVED = "Talep #%d onaylandı."
MSG_REJECTED = "Talep #%d reddedildi."
MSG_APPROVE_INSUFFICIENT = "Personelin kalan izin bakiyesi yetersiz (kalan %d gün, talep %d gün)."
MSG_ALREADY_DECIDED = "Bu talep zaten sonuçlandırılmış."
MSG_REQUEST_NOT_FOUND = "Talep bulunamadı."
MSG_ACTION_UNEXPECTED = "İşlem tamamlanamadı. Lütfen daha sonra tekrar deneyin."
# CSRF (spec 0011)
MSG_CSRF = "Form geçersiz ya da süresi dolmuş. Lütfen sayfayı yenileyip tekrar deneyin."

# Basari parametresi (PRG): sonuc -> (beklenen gercek durum, mesaj)
RESULTS = {"onaylandi": (APPROVED, MSG_APPROVED), "reddedildi": (REJECTED, MSG_REJECTED)}

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
    if status == APPROVED:
        color = "green"
    if status.lower() == PENDING.lower():  # harfe duyarsiz (karakterizasyon, 0012 PB-4)
        color = "orange"
    if status == REJECTED:
        color = "red"
    return "<b style='color:%s'>%s</b>" % (color, status)


def parse_request_id(text):
    # Talep numarasi yalniz ASCII rakamdir; int()'in kabul ettigi bosluk, Unicode rakam ve "_"
    # bir talebe eslenmez (spec 0010 AC-7, review F-1)
    if not (text.isascii() and text.isdigit()):
        return None
    try:
        return int(text)
    except ValueError:  # int()'in hane siniri (4300) asilirsa da talep yok (review F-4)
        return None


def csrf_field():
    # Durum degistiren her formda token (spec 0011 CB-1). Koruma kapaliyken alan uretilmez:
    # token'in anlami yok ve ortak test istemcisi korumayi kapatir (plan 0011 Risk 2)
    if not current_app.config.get("WTF_CSRF_ENABLED", True):
        return ""
    return "<input type='hidden' name='csrf_token' value='%s'>" % escape(generate_csrf())


def parse_date(text):
    # Yalniz YYYY-MM-DD; degilse None (form hatasinda ham metin geri basilmaz, spec 0015 K-3)
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def form_values(form):
    # Hata ekraninda geri basilacak degerler; her alan ayri dogrulanir (spec 0015 K-3, K-5).
    # Personel yalniz secenek listesiyle tamsayi olarak eslesir; neden kacisla basilir.
    try:
        emp_id = int(form.get("employee_id", ""))
    except ValueError:
        emp_id = None
    return {"employee_id": emp_id, "start": parse_date(form.get("start")),
            "end": parse_date(form.get("end")), "reason": form.get("reason", "")}


def decision_buttons(request_id):
    # Durum hucresinde; dugme etiketi value ozniteliginde ("Kaydet" kalibi, plan 0010 Risk 1)
    return "".join(
        " <form method='post' action='/requests/%d/%s' style='display:inline'>%s"
        "<input type='submit' value='%s'></form>" % (request_id, action, csrf_field(), label)
        for action, label in (("approve", "Onayla"), ("reject", "Reddet")))


def register_routes(app, svc):

    @app.route("/")
    def dashboard():
        bekleyen = len([r for r in svc.requests() if r["status"] == PENDING])
        onaylanan = len([r for r in svc.requests() if r["status"] == APPROVED])
        reddedilen = len([r for r in svc.requests() if r["status"] == REJECTED])
        body = "<div class='kutu'>Bekleyen: <b>%d</b></div><div class='kutu'>Onaylanan: <b>%d</b></div><div class='kutu'>Reddedilen: <b>%d</b></div>" % (bekleyen, onaylanan, reddedilen)
        body += "<h3>Personel Bakiyeleri</h3><table><tr><th>Ad</th><th>Birim</th><th>Hak</th><th>Kullanilan</th><th>Kalan</th><th>Bekleyen</th></tr>"
        for e in svc.employees():
            body += "<tr><td>%s</td><td>%s</td><td>%d</td><td>%d</td><td>%d</td><td>%d</td></tr>" % (
                escape(e["name"]), escape(e["department"]), svc.get_entitlement(e), svc.get_used_days(e["id"]), svc.get_remaining(e),
                svc.get_pending_days(e["id"]))
        body += "</table>"
        return render_template_string(PAGE, body=body)

    def requests_page(message=None, success=False):
        body = "<h3>Izin Talepleri</h3><table><tr><th>Personel</th><th>Baslangic</th><th>Bitis</th><th>Gun</th><th>Neden</th><th>Durum</th></tr>"
        for r in svc.requests():
            emp = [e for e in svc.employees() if e["id"] == r["employee_id"]][0]
            body += "<tr><td>%s</td><td>%s</td><td>%s</td><td>%d</td><td>%s</td><td>%s</td></tr>" % (
                escape(emp["name"]), r["start"], r["end"], svc.calc_days(r["start"], r["end"]), escape(r["reason"]),
                status_badge(r["status"]) + (decision_buttons(r["id"]) if r["status"] == PENDING else ""))
        body += "</table>"
        if message is not None:
            color = "green" if success else "red"
            body = "<p style='color:%s'>%s</p>" % (color, escape(message)) + body
        return render_template_string(PAGE, body=body)

    def success_message():
        # Mesaj yalniz talebin gercek durumu parametreyle eslesirse gosterilir (plan 0010 Risk 2)
        result = RESULTS.get(request.args.get("sonuc", ""))
        talep = parse_request_id(request.args.get("talep", ""))
        if result is None or talep is None:
            return None
        expected, message = result
        if any(r["id"] == talep and r["status"] == expected for r in svc.requests()):
            return message % talep
        return None

    @app.route("/requests")
    def list_requests():
        message = success_message()
        return requests_page(message, success=True)

    def decide(request_id, action, result):
        # Hata: yonlendirme yok, liste mesajla yeniden gosterilir (spec 0010, K-4)
        rid = parse_request_id(request_id)
        if rid is None:
            return requests_page(MSG_REQUEST_NOT_FOUND), 404
        try:
            action(rid)
        except RequestNotFound:
            return requests_page(MSG_REQUEST_NOT_FOUND), 404
        except RequestAlreadyDecided:
            return requests_page(MSG_ALREADY_DECIDED), 400
        except InsufficientBalance as e:
            return requests_page(MSG_APPROVE_INSUFFICIENT % (e.remaining, e.requested)), 400
        except Exception:
            logger.exception("izin talebi sonuclandirilamadi")
            return requests_page(MSG_ACTION_UNEXPECTED), 500
        return redirect("/requests?sonuc=%s&talep=%d" % (result, rid))

    @app.route("/requests/<request_id>/approve", methods=["POST"])
    def approve_request(request_id):
        return decide(request_id, svc.approve_request, "onaylandi")

    @app.route("/requests/<request_id>/reject", methods=["POST"])
    def reject_request(request_id):
        return decide(request_id, svc.reject_request, "reddedildi")

    def new_request_form(message=None, values=None):
        v = values or {}
        options = "".join("<option value='%d'%s>%s</option>" % (
            e["id"], " selected" if e["id"] == v.get("employee_id") else "", escape(e["name"]))
            for e in svc.employees())
        start = v["start"].isoformat() if v.get("start") else ""
        end = v["end"].isoformat() if v.get("end") else ""
        body = """<h3>Yeni Talep</h3><form method="post">%s
    Personel: <select name="employee_id">%s</select><br><br>
    Baslangic: <input type="date" name="start" value="%s"><br><br>
    Bitis: <input type="date" name="end" value="%s"><br><br>
    Neden: <input type="text" name="reason" value="%s"><br><br>
    <input type="submit" value="Kaydet"></form>""" % (csrf_field(), options, start, end,
                                                       escape(v.get("reason", "")))
        if message is not None:
            body = "<p style='color:red'>%s</p>" % escape(message) + body
        return render_template_string(PAGE, body=body)

    @app.route("/new", methods=["GET", "POST"])
    def new_request():
        if request.method == "POST":
            values = form_values(request.form)
            # Ihlal sirasi: bozuk girdi -> personel -> tarih araligi -> is gunu yok -> bakiye
            # (spec 0008 S-4, spec 0014 K-5)
            try:
                emp_id = int(request.form["employee_id"])
                start = datetime.strptime(request.form["start"], "%Y-%m-%d").date()
                end = datetime.strptime(request.form["end"], "%Y-%m-%d").date()
            except (KeyError, ValueError):
                return new_request_form(MSG_INVALID_INPUT, values), 400
            try:
                svc.create_request(emp_id, start, end, request.form.get("reason", ""))
            except EmployeeNotFound:
                return new_request_form(MSG_EMPLOYEE_NOT_FOUND, values), 400
            except InvalidDateRange:
                return new_request_form(MSG_INVALID_DATE_RANGE, values), 400
            except NoWorkingDays:
                return new_request_form(MSG_NO_WORKING_DAYS, values), 400
            except InsufficientBalance as e:
                return new_request_form(MSG_INSUFFICIENT_BALANCE % (e.remaining, e.pending, e.requested), values), 400
            except Exception:
                # beklenmeyen hata: ayrinti loga, kullaniciya genel mesaj (docs/conventions.md)
                logger.exception("izin talebi kaydedilemedi")
                return new_request_form(MSG_UNEXPECTED, values), 500
            return redirect("/requests")
        return new_request_form()

    @app.errorhandler(CSRFError)
    def csrf_failed(e):
        # Token yok / bozuk / baska oturumun: hicbir sey degismez, 400 + Turkce mesaj (spec 0011
        # CB-2). Kontrol view'dan once calisir; istisna metni ve token loga da yazilmaz.
        logger.warning("CSRF dogrulamasi basarisiz: %s %r", request.method, request.path)
        if request.path == "/new":
            return new_request_form(MSG_CSRF), 400  # degerler geri basilmaz (0015 K-2)
        return requests_page(MSG_CSRF), 400
