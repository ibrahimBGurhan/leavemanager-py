# HTTP: route'lar, form girdisi, sayfa ve durum rozeti. Veriye yalniz servis uzerinden erisir.
import logging
from datetime import datetime

from flask import current_app, g, request, redirect, render_template_string
from flask_wtf.csrf import CSRFError, generate_csrf
from markupsafe import escape

from domain.errors import (EmployeeNotFound, InsufficientBalance, InvalidDateRange,
                           InvalidEmployee, NoWorkingDays, NotAuthorized, RequestAlreadyDecided,
                           RequestNotFound)
from domain.access import ACTION_APPROVE, ACTION_REJECT, parse_request_id
from domain.collation import turkish_sort_key
from domain.leave_service import APPROVED, PENDING, REJECTED
from web.auth import login_page

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
# Yetki (spec 0020 R-6, R-7 / G-1)
MSG_FORBIDDEN = "Bu işlem için yetkiniz yok."
MSG_NO_EMPLOYEE = "Hesabınız bir personel kaydına bağlı değil; talep açmak için İK ile görüşün."
# Yeni Personel (spec 0022 R-2, R-6 / G-2). Anahtar: InvalidEmployee.reason
MSG_EMPLOYEE_ADDED = "Personel #%d eklendi: %s (%s)."
EMPLOYEE_ERRORS = {
    "name-missing": "Ad girin.",
    "unit-missing": "Birim girin.",
    "name-too-long": "Ad en fazla 100 karakter olabilir.",
    "unit-too-long": "Birim en fazla 50 karakter olabilir.",
    "date-invalid": "Geçerli bir işe giriş tarihi girin.",
    "date-too-early": "İşe giriş tarihi 1950-01-01'den önce olamaz.",
}
MSG_EMPLOYEE_UNEXPECTED = "Personel kaydedilemedi. Lütfen daha sonra tekrar deneyin."
NEW_EMPLOYEE_PATH = "/personel/yeni"

# Menu (spec 0019): kullanicinin e-postasi Jinja kacisiyla (G-5); cikis formu sayfanin sonunda,
# dugmesi menude (form= ozniteligi), boylece ekranlardaki formlarin sirasi degismez (plan 0019 Risk 2).
# "Yeni Personel" yalniz personel ekleyebilen hesaba (spec 0022 R-7; bayrak gorunumden, plan Risk 3).

# Basari parametresi (PRG): sonuc -> (beklenen gercek durum, mesaj)
RESULTS = {"onaylandi": (APPROVED, MSG_APPROVED), "reddedildi": (REJECTED, MSG_REJECTED)}

PAGE = """
<html><head><meta charset="utf-8"><title>LeaveManager</title>
<style>body{font-family:Arial;margin:30px} table{border-collapse:collapse}
td,th{border:1px solid #ccc;padding:6px 10px} .kutu{display:inline-block;border:1px solid #ccc;padding:10px 20px;margin-right:10px}</style>
</head><body>
<h2>LeaveManager</h2>
<p><a href="/">Ana Sayfa</a> | <a href="/requests">Talepler</a> | <a href="/new">Yeni Talep</a>
{%- if can_add_employees %} | <a href="/personel/yeni">Yeni Personel</a>{% endif %}
{%- if g.account %} | {{ g.account.email }} <button type="submit" form="cikis-formu">Çıkış</button>{% endif %}</p>
{{ body|safe }}
{%- if g.account %}
<form id="cikis-formu" method="post" action="/cikis">
{%- if config.get("WTF_CSRF_ENABLED", True) %}<input type='hidden' name='csrf_token' value='{{ csrf_token() }}'>{% endif %}</form>
{%- endif %}
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

    def view():
        # Veri ve islemler yalniz hesabin gorunumunden (spec 0020 R-1; plan 0020 Risk 1, 5).
        # Kapi her kapali endpoint'te g.account'u kurar (spec 0019).
        return svc.for_account(g.account)

    @app.context_processor
    def menu_flags():
        # Giris ekraninda hesap yok: bayrak yok, baglanti yok
        account = g.get("account")
        return {"can_add_employees": account is not None and view().can_add_employees()}

    @app.route("/")
    def dashboard():
        v = view()
        reqs = v.requests()
        # Uc kutu talep sayisidir, gun degil; Personel icin yalniz kendi talepleri (R-2, G-5)
        bekleyen = len([r for r in reqs if r["status"] == PENDING])
        onaylanan = len([r for r in reqs if r["status"] == APPROVED])
        reddedilen = len([r for r in reqs if r["status"] == REJECTED])
        body = "<div class='kutu'>Bekleyen: <b>%d</b></div><div class='kutu'>Onaylanan: <b>%d</b></div><div class='kutu'>Reddedilen: <b>%d</b></div>" % (bekleyen, onaylanan, reddedilen)
        body += "<h3>Personel Bakiyeleri</h3><table><tr><th>Ad</th><th>Birim</th><th>Hak</th><th>Kullanilan</th><th>Kalan</th><th>Bekleyen</th></tr>"
        for e in v.employees():
            body += "<tr><td>%s</td><td>%s</td><td>%d</td><td>%d</td><td>%d</td><td>%d</td></tr>" % (
                (escape(e["name"]), escape(e["department"])) + v.balance(e))
        body += "</table>"
        return render_template_string(PAGE, body=body)

    def requests_page(message=None, success=False):
        # Hata ve CSRF sayfalari da buradan: her yolda suzulmus liste (R-3, R-8)
        v = view()
        employees = v.employees()
        # Dugme yalniz sonuclandirabilecegi talepte (0020 R-3, 0021 R-4); asil engel domain'de
        body = "<h3>Izin Talepleri</h3><table><tr><th>Personel</th><th>Baslangic</th><th>Bitis</th><th>Gun</th><th>Neden</th><th>Durum</th></tr>"
        for r in v.requests():
            emp = [e for e in employees if e["id"] == r["employee_id"]][0]
            body += "<tr><td>%s</td><td>%s</td><td>%s</td><td>%d</td><td>%s</td><td>%s</td></tr>" % (
                escape(emp["name"]), r["start"], r["end"], v.calc_days(r["start"], r["end"]), escape(r["reason"]),
                status_badge(r["status"]) + (decision_buttons(r["id"]) if v.can_decide_request(r) else ""))
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
        # Yalniz gorunur talepler: baskasinin talebi hakkinda ileti yok (R-3, AC-9)
        if any(r["id"] == talep and r["status"] == expected for r in view().requests()):
            return message % talep
        return None

    @app.route("/requests")
    def list_requests():
        message = success_message()
        return requests_page(message, success=True)

    def decide(request_id, action_name, result):
        # Hata: yonlendirme yok, liste mesajla yeniden gosterilir (spec 0010, K-4)
        v = view()
        action = getattr(v, action_name)
        try:
            # Yetki her seyden once: numara ayristirilmadan, ham degerle; olmayan ya da
            # sonuclanmis talep de ayni iletiyi alir (R-6; plan 0020 Risk 4, review F-1)
            v.authorize_decide(ACTION_LABELS[action_name], request_id)
            rid = parse_request_id(request_id)
            if rid is None:
                return requests_page(MSG_REQUEST_NOT_FOUND), 404
            action(rid)
        except NotAuthorized:
            return requests_page(MSG_FORBIDDEN), 403
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

    ACTION_LABELS = {"approve_request": ACTION_APPROVE, "reject_request": ACTION_REJECT}

    @app.route("/requests/<request_id>/approve", methods=["POST"])
    def approve_request(request_id):
        return decide(request_id, "approve_request", "onaylandi")

    @app.route("/requests/<request_id>/reject", methods=["POST"])
    def reject_request(request_id):
        return decide(request_id, "reject_request", "reddedildi")

    def new_request_form(message=None, values=None):
        v = values or {}
        acc = view()
        if acc.sees_everyone():
            options = "".join("<option value='%d'%s>%s</option>" % (
                e["id"], " selected" if e["id"] == v.get("employee_id") else "", escape(e["name"]))
                for e in acc.employees())
            employee_field = "<select name=\"employee_id\">%s</select>" % options
        else:
            own = acc.own_employee()
            if own is None:
                # Bagli personel kaydi yok: form yok, yalniz bilgi (R-7, G-1)
                body = "<h3>Yeni Talep</h3><p>%s</p>" % escape(MSG_NO_EMPLOYEE)
                if message is not None:
                    body = "<p style='color:red'>%s</p>" % escape(message) + body
                return render_template_string(PAGE, body=body)
            # Secim yok, kendi adi sabit metin; talep her zaman kendi adina (R-4)
            employee_field = escape(own["name"])
        start = v["start"].isoformat() if v.get("start") else ""
        end = v["end"].isoformat() if v.get("end") else ""
        body = """<h3>Yeni Talep</h3><form method="post">%s
    Personel: %s<br><br>
    Baslangic: <input type="date" name="start" value="%s"><br><br>
    Bitis: <input type="date" name="end" value="%s"><br><br>
    Neden: <input type="text" name="reason" value="%s"><br><br>
    <input type="submit" value="Kaydet"></form>""" % (csrf_field(), employee_field, start, end,
                                                       escape(v.get("reason", "")))
        if message is not None:
            body = "<p style='color:red'>%s</p>" % escape(message) + body
        return render_template_string(PAGE, body=body)

    @app.route("/new", methods=["GET", "POST"])
    def new_request():
        if request.method == "POST":
            values = form_values(request.form)
            acc = view()
            if not acc.sees_everyone():
                # Personel / Yonetici: alan yoksa kendi kaydi; varsa ve kendi numarasi degilse
                # (baska personel, olmayan numara, bozuk deger) yetki hatasi, tarihlerden once
                # (R-4, R-6; plan 0020 Risk 3). Form kendi adiyla, tarih ve neden geri basili (G-2).
                own = acc.own_employee()
                raw = request.form.get("employee_id")
                if raw is None and own is not None:
                    emp_id = own["id"]
                else:
                    try:
                        emp_id = int(raw)
                    except (TypeError, ValueError):
                        emp_id = raw
                try:
                    acc.authorize_create(emp_id)  # kural domain'de, tek yerde (review F-1)
                except NotAuthorized:
                    return new_request_form(MSG_FORBIDDEN, values), 403
            # Ihlal sirasi: bozuk girdi -> personel -> tarih araligi -> is gunu yok -> bakiye
            # (spec 0008 S-4, spec 0014 K-5)
            try:
                emp_id = int(request.form["employee_id"]) if acc.sees_everyone() else emp_id
                start = datetime.strptime(request.form["start"], "%Y-%m-%d").date()
                end = datetime.strptime(request.form["end"], "%Y-%m-%d").date()
            except (KeyError, ValueError):
                return new_request_form(MSG_INVALID_INPUT, values), 400
            try:
                acc.create_request(emp_id, start, end, request.form.get("reason", ""))
            except NotAuthorized:
                return new_request_form(MSG_FORBIDDEN, values), 403
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

    def employee_form(message=None, values=None, success=False):
        # Yeni Personel ekrani (spec 0022 R-1). Yetkisiz hesaba form cizilmez, yalniz ileti
        # (plan Risk 4). Ad ve birim geri basilirken kacislanir (R-6, G-6); bozuk tarih geri
        # basilmaz (spec 0015 K-3).
        v = view()
        body = "<h3>Yeni Personel</h3>"
        if not v.can_add_employees():
            body += "<p style='color:red'>%s</p>" % escape(MSG_FORBIDDEN)
            if message is not None and message != MSG_FORBIDDEN:
                body = "<p style='color:red'>%s</p>" % escape(message) + body
            return render_template_string(PAGE, body=body)
        values = values or {}
        # Oneri listesi: kayitli birimler, her biri bir kez, yazildigi gibi, Turkce alfabe sirasiyla
        # (G-4, spec 0028)
        units = sorted({e["department"] for e in v.employees() if e["department"].strip()},
                       key=turkish_sort_key)
        options = "".join("<option value=\"%s\"></option>" % escape(u) for u in units)
        hire = values.get("hire_date")
        body += """<form method="post">%s
    <label for="ad">Ad</label>: <input type="text" id="ad" name="name" value="%s"><br><br>
    <label for="birim">Birim</label>: <input type="text" id="birim" name="department" list="birimler" value="%s">
    <datalist id="birimler">%s</datalist><br><br>
    <label for="ise-giris">İşe giriş tarihi</label>: <input type="date" id="ise-giris" name="hire_date" value="%s"><br><br>
    <input type="submit" value="Kaydet"></form>""" % (
            csrf_field(), escape(values.get("name", "")), escape(values.get("department", "")),
            options, hire.isoformat() if hire else "")
        if message is not None:
            color = "green" if success else "red"
            body = "<p style='color:%s'>%s</p>" % (color, escape(message)) + body
        return render_template_string(PAGE, body=body)

    def employee_added_message():
        # Ileti URL'deki numaradan degil kayittan kurulur; gorunur bir personele eslesmezse ileti
        # yok (plan Risk 5; spec 0010 Risk 2 kalibi)
        emp_id = parse_request_id(request.args.get("eklendi", ""))
        if emp_id is None:
            return None
        emp = next((e for e in view().employees() if e["id"] == emp_id), None)
        if emp is None:
            return None
        return MSG_EMPLOYEE_ADDED % (emp["id"], emp["name"], emp["department"])

    @app.route(NEW_EMPLOYEE_PATH, methods=["GET", "POST"])
    def new_employee():
        v = view()
        try:
            v.authorize_add_employee()  # yetki girdiden once (R-7); ret log'a WARNING
        except NotAuthorized:
            return employee_form(), 403
        if request.method == "GET":
            message = employee_added_message()
            return employee_form(message, success=message is not None)
        values = {"name": request.form.get("name", ""),
                  "department": request.form.get("department", ""),
                  "hire_date": parse_date(request.form.get("hire_date"))}
        try:
            # Ayristirilamayan tarih None gider: ad ve birim hatalari once gelir (G-1, plan Risk 2)
            record = v.add_employee(values["name"], values["department"], values["hire_date"])
        except NotAuthorized:
            return employee_form(), 403
        except InvalidEmployee as e:
            return employee_form(EMPLOYEE_ERRORS[e.reason], values), 400
        except Exception:
            logger.exception("personel kaydedilemedi")
            return employee_form(MSG_EMPLOYEE_UNEXPECTED, values), 500
        # PRG: yenileme kaydi tekrarlamaz, form bos acilir (G-3)
        return redirect("%s?eklendi=%d" % (NEW_EMPLOYEE_PATH, record["id"]))

    @app.errorhandler(CSRFError)
    def csrf_failed(e):
        # Token yok / bozuk / baska oturumun: hicbir sey degismez, 400 + Turkce mesaj (spec 0011
        # CB-2). Kontrol view'dan once calisir; istisna metni ve token loga da yazilmaz.
        logger.warning("CSRF dogrulamasi basarisiz: %s %r", request.method, request.path)
        if request.path == "/new":
            return new_request_form(MSG_CSRF), 400  # degerler geri basilmaz (0015 K-2)
        if request.path == NEW_EMPLOYEE_PATH:
            return employee_form(MSG_CSRF), 400  # degerler geri basilmaz; yetkisize form yok
        if request.path == "/giris":
            return login_page(MSG_CSRF, error=True), 400  # kimse girmez (spec 0019 R-10)
        return requests_page(MSG_CSRF), 400
