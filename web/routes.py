# HTTP: route'lar, form girdisi, sablona verilen veri. Veriye yalniz servis uzerinden erisir.
import logging
import re
from datetime import datetime

from flask import g, request, redirect, render_template
from flask_wtf.csrf import CSRFError

from domain.errors import (BeforeOpeningBalance, EmployeeNotFound, InsufficientBalance,
                           InvalidDateRange, InvalidEmployee, InvalidOpeningBalance, NoWorkingDays,
                           NotAuthorized, RequestAlreadyDecided, RequestNotFound)
from domain.access import parse_request_id
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
# Acilis Bakiyesi (spec 0041 K-3, K-4, K-6, K-9). Anahtar: InvalidOpeningBalance.reason
OPENING_PATH = "/acilis-bakiyesi"
MSG_OPENING_SAVED = "Personel #%d açılış bakiyesi kaydedildi: %s, %d gün."
MSG_OPENING_WARNING = ("Açılış tarihinden önce başlayan bekleyen talepler: %s. Bunlar onaylanırsa "
                       "bakiyeden düşmez.")
OPENING_ERRORS = {
    "employee-missing": "Personel seçin.",
    "employee-not-found": "Personel bulunamadı.",
    "date-invalid": "Geçerli bir açılış tarihi girin.",
    "date-before-hire": "Açılış tarihi işe giriş tarihinden (%s) önce olamaz.",
    "date-in-future": "Açılış tarihi bugünden sonra olamaz.",
    "days-invalid": "Gün 0 ile 365 arasında bir tam sayı olmalı.",
}
MSG_OPENING_UNEXPECTED = "Açılış bakiyesi kaydedilemedi. Lütfen daha sonra tekrar deneyin."
MSG_BEFORE_OPENING = ("Bu personelin açılış bakiyesi %s tarihli; daha önce başlayan izin açılış "
                      "bakiyesine dahildir.")
# Gun: bosluklar atilir, yalniz ASCII rakam (basta istege bagli "-"); int()'in kabul ettigi Unicode
# rakam, "_" ve "+" tam sayi sayilmaz (plan 0041 Risk 1)
_DAYS = re.compile(r"-?[0-9]+")


def parse_days(text):
    # Gun metni -> tam sayi; ayrismazsa None. int()'in hane siniri (4300) asilirsa da None: ayni
    # ileti, 500 yok (review 0041 F-1; review 0010 F-4 / parse_request_id emsali)
    text = (text or "").strip()
    if not _DAYS.fullmatch(text):
        return None
    try:
        return int(text)
    except ValueError:
        return None

# Sayfalar web/templates/ altinda, otomatik kacisla (ADR-0003, spec 0032): burada HTML yok, yalniz
# sablona verilen veri. Menu iskelette (base.html); "Yeni Personel" bayragi gorunumden (spec 0022
# R-7, plan Risk 3).

# Basari parametresi (PRG): sonuc -> (beklenen gercek durum, mesaj)
RESULTS = {"onaylandi": (APPROVED, MSG_APPROVED), "reddedildi": (REJECTED, MSG_REJECTED)}


def status_kind(status):
    # Durum rozetinin turu (UI isi); renk degil, gorunum Bootstrap'ta (spec 0035 R-6, plan Risk 5)
    kind = "secondary"
    if status == APPROVED:
        kind = "success"
    if status.lower() == PENDING.lower():  # harfe duyarsiz (karakterizasyon, 0012 PB-4)
        kind = "warning"
    if status == REJECTED:
        kind = "danger"
    return kind


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


def register_routes(app, svc):

    def view():
        # Veri ve islemler yalniz hesabin gorunumunden (spec 0020 R-1; plan 0020 Risk 1, 5).
        # Kapi her kapali endpoint'te g.account'u kurar (spec 0019).
        return svc.for_account(g.account)

    @app.context_processor
    def menu_flags():
        # Giris ekraninda hesap yok: bayrak yok, baglanti yok
        account = g.get("account")
        return {"can_add_employees": account is not None and view().can_add_employees(),
                "can_set_opening_balances": (account is not None
                                             and view().can_set_opening_balances())}

    @app.route("/")
    def dashboard():
        v = view()
        reqs = v.requests()
        # Uc kutu talep sayisidir, gun degil; Personel icin yalniz kendi talepleri (R-2, G-5)
        rows = [{"name": e["name"], "department": e["department"], "balance": v.balance(e)}
                for e in v.employees()]
        return render_template(
            "dashboard.html", rows=rows,
            pending=len([r for r in reqs if r["status"] == PENDING]),
            approved=len([r for r in reqs if r["status"] == APPROVED]),
            rejected=len([r for r in reqs if r["status"] == REJECTED]))

    def requests_page(message=None, success=False):
        # Hata ve CSRF sayfalari da buradan: her yolda suzulmus liste (R-3, R-8)
        v = view()
        employees = v.employees()
        # Dugme yalniz sonuclandirabilecegi talepte (0020 R-3, 0021 R-4); asil engel domain'de
        rows = []
        for r in v.requests():
            emp = [e for e in employees if e["id"] == r["employee_id"]][0]
            rows.append({"id": r["id"], "name": emp["name"], "start": r["start"], "end": r["end"],
                         "days": v.calc_days(r["start"], r["end"]), "reason": r["reason"],
                         "status": r["status"], "kind": status_kind(r["status"]),
                         "can_decide": v.can_decide_request(r)})
        return render_template("requests.html", rows=rows, message=message,
                               message_kind="success" if success else "danger")

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

    def decide(request_id, action_name, authorize_name, result):
        # Hata: yonlendirme yok, liste mesajla yeniden gosterilir (spec 0010, K-4)
        v = view()
        action = getattr(v, action_name)
        authorize = getattr(v, authorize_name)
        try:
            # Yetki her seyden once: numara ayristirilmadan, ham degerle; olmayan ya da
            # sonuclanmis talep de ayni iletiyi alir (R-6; plan 0020 Risk 4, review F-1). Log adini
            # domain secer, web bilmez (spec 0030).
            authorize(request_id)
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

    @app.route("/requests/<request_id>/approve", methods=["POST"])
    def approve_request(request_id):
        return decide(request_id, "approve_request", "authorize_approve", "onaylandi")

    @app.route("/requests/<request_id>/reject", methods=["POST"])
    def reject_request(request_id):
        return decide(request_id, "reject_request", "authorize_reject", "reddedildi")

    def new_request_form(message=None, values=None):
        v = values or {}
        acc = view()
        employees = own_name = None
        no_employee = False
        if acc.sees_everyone():
            employees = acc.employees()
        else:
            own = acc.own_employee()
            if own is None:
                # Bagli personel kaydi yok: form yok, yalniz bilgi (R-7, G-1)
                no_employee = True
            else:
                # Secim yok, kendi adi sabit metin; talep her zaman kendi adina (R-4)
                own_name = own["name"]
        return render_template(
            "new_request.html", message=message, no_employee=no_employee,
            no_employee_text=MSG_NO_EMPLOYEE, employees=employees,
            selected=v.get("employee_id"), own_name=own_name,
            start=v["start"].isoformat() if v.get("start") else "",
            end=v["end"].isoformat() if v.get("end") else "",
            reason=v.get("reason", ""))

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
            # Ihlal sirasi: bozuk girdi -> personel -> tarih araligi -> acilis oncesi -> is gunu
            # yok -> bakiye (spec 0008 S-4, spec 0014 K-5, spec 0041 K-6)
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
            except BeforeOpeningBalance as e:
                # Acilis oncesi donem acilis bakiyesinin icinde (spec 0041 K-6)
                return new_request_form(MSG_BEFORE_OPENING % e.opening_date.isoformat(), values), 400
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
        if not v.can_add_employees():
            # Ustte yalniz yetki iletisinden farkli bir ileti (ör. CSRF), kirmizi
            return render_template(
                "new_employee.html", forbidden=True, forbidden_text=MSG_FORBIDDEN,
                message=message if message != MSG_FORBIDDEN else None, message_kind="danger")
        values = values or {}
        # Oneri listesi: kayitli birimler, her biri bir kez, yazildigi gibi, Turkce alfabe sirasiyla
        # (G-4, spec 0028)
        units = sorted({e["department"] for e in v.employees() if e["department"].strip()},
                       key=turkish_sort_key)
        hire = values.get("hire_date")
        return render_template(
            "new_employee.html", forbidden=False, message=message,
            message_kind="success" if success else "danger", units=units,
            name=values.get("name", ""), department=values.get("department", ""),
            hire_date=hire.isoformat() if hire else "")

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

    def opening_form(message=None, values=None, message_kind="danger", warning=None):
        # Acilis Bakiyesi ekrani (spec 0041 K-3). Yetkisiz hesaba form ve liste cizilmez, yalniz
        # ileti (R-7). Personel secimi ve gun ham metinle geri basilir (kacisla); bozuk tarih
        # geri basilmaz (spec 0015 K-3).
        v = view()
        if not v.can_set_opening_balances():
            return render_template(
                "opening_balance.html", forbidden=True, forbidden_text=MSG_FORBIDDEN,
                message=message if message != MSG_FORBIDDEN else None, message_kind="danger",
                warning=None)
        values = values or {}
        rows = []
        for e in v.employees():
            o = v.opening_balance(e["id"])
            rows.append({"name": e["name"], "department": e["department"],
                         "hire_date": e["hire_date"].isoformat(),
                         "opening_date": o["date"].isoformat() if o else "",
                         "opening_days": o["days"] if o else ""})
        on = values.get("date")
        return render_template(
            "opening_balance.html", forbidden=False, message=message, message_kind=message_kind,
            warning=warning, employees=v.employees(), rows=rows,
            selected=values.get("employee_id", ""), on=on.isoformat() if on else "",
            days=values.get("days", ""))

    def opening_saved():
        # Ileti ve uyari URL'deki numaradan degil kayittan kurulur; uyari her acilista yeniden
        # hesaplanir (plan 0041 Risk 6, G-3). Eslesmeyen numara: ileti yok.
        v = view()
        emp_id = parse_request_id(request.args.get("kaydedildi", ""))
        if emp_id is None or not any(e["id"] == emp_id for e in v.employees()):
            return None, None
        o = v.opening_balance(emp_id)
        if o is None:
            return None, None
        pending = v.pending_before_opening(emp_id)
        warning = (MSG_OPENING_WARNING % ", ".join("#%d" % rid for rid in pending)
                   if pending else None)
        return MSG_OPENING_SAVED % (emp_id, o["date"].isoformat(), o["days"]), warning

    @app.route(OPENING_PATH, methods=["GET", "POST"])
    def opening_balance():
        v = view()
        try:
            v.authorize_set_opening_balance()  # yetki girdiden once (R-7); ret log'a WARNING
        except NotAuthorized:
            return opening_form(), 403
        if request.method == "GET":
            message, warning = opening_saved()
            return opening_form(message, message_kind="success", warning=warning)
        raw_emp = request.form.get("employee_id", "").strip()
        raw_days = request.form.get("days", "")
        values = {"employee_id": raw_emp, "date": parse_date(request.form.get("date")),
                  "days": raw_days}
        # Ayristirilamayan deger domain'e None (tarih, gun) ya da eslesmeyen metin (personel)
        # olarak gider; ihlal sirasini domain verir (plan 0041 Risk 2, 3)
        emp_id = None if raw_emp == "" else parse_request_id(raw_emp)
        if raw_emp != "" and emp_id is None:
            emp_id = raw_emp
        days = parse_days(raw_days)
        try:
            record = v.set_opening_balance(emp_id, values["date"], days)
        except NotAuthorized:
            return opening_form(), 403
        except InvalidOpeningBalance as e:
            message = OPENING_ERRORS[e.reason]
            if e.reason == "date-before-hire":
                message = message % e.hire_date.isoformat()
            return opening_form(message, values), 400
        except Exception:
            logger.exception("acilis bakiyesi kaydedilemedi")
            return opening_form(MSG_OPENING_UNEXPECTED, values), 500
        # PRG: yenileme kaydi tekrarlamaz, form bos acilir
        return redirect("%s?kaydedildi=%d" % (OPENING_PATH, record["employee_id"]))

    @app.errorhandler(CSRFError)
    def csrf_failed(e):
        # Token yok / bozuk / baska oturumun: hicbir sey degismez, 400 + Turkce mesaj (spec 0011
        # CB-2). Kontrol view'dan once calisir; istisna metni ve token loga da yazilmaz.
        logger.warning("CSRF dogrulamasi basarisiz: %s %r", request.method, request.path)
        if request.path == "/new":
            return new_request_form(MSG_CSRF), 400  # degerler geri basilmaz (0015 K-2)
        if request.path == NEW_EMPLOYEE_PATH:
            return employee_form(MSG_CSRF), 400  # degerler geri basilmaz; yetkisize form yok
        if request.path == OPENING_PATH:
            return opening_form(MSG_CSRF), 400  # degerler geri basilmaz; yetkisize form yok
        if request.path == "/giris":
            return login_page(MSG_CSRF, error=True), 400  # kimse girmez (spec 0019 R-10)
        return requests_page(MSG_CSRF), 400
