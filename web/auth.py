# Giris / cikis ve varsayilan kapali kapi (spec 0019, ADR-0002 D-4…D-6). Kurallar domain/auth.py'de;
# burada yalniz HTTP: oturum cerezi, yonlendirme, giris ekrani. HTML Jinja ile, otomatik kacisla
# (docs/security.md); kullanici girdisi sayfaya yalniz {{ }} ile girer.
from flask import g, redirect, render_template_string, request, session

from domain.errors import LoginRefused, SessionExpired

# Giris ekrani disinda her endpoint kapali; bilinmeyen adresler de (endpoint None) kapidan gecmez
OPEN_ENDPOINTS = frozenset({"login", "static"})

MSG_LOGIN_FAILED = "E-posta ya da şifre hatalı."
MSG_LOCK_NOTE = "Çok sayıda hatalı denemeden sonra hesap geçici olarak kilitlenir."
MSG_EXPIRED = "Oturumunuzun süresi doldu. Lütfen tekrar giriş yapın."
MSG_LOGGED_OUT = "Çıkış yapıldı."
# Oturumdaki giris bilgisi; kapi yalniz bunlari siler, CSRF token'i kalir (review 0019 F-1)
LOGIN_KEYS = ("hesap", "giris")
# ?durum= yalniz bu sabit eslemeden ileti secer; bilinmeyen deger yok sayilir (plan 0019 Risk 8)
STATUS_MESSAGES = {"sure": MSG_EXPIRED, "cikis": MSG_LOGGED_OUT}

LOGIN_PAGE = """
<html><head><meta charset="utf-8"><title>Giriş</title>
<style>body{font-family:Arial;margin:30px}</style>
</head><body>
<h2>LeaveManager</h2>
<h3>Giriş</h3>
{% if message %}<p{% if error %} style='color:red'{% endif %}>{{ message }}</p>{% endif %}
<form method="post" action="/giris">
{%- if config.get("WTF_CSRF_ENABLED", True) %}<input type='hidden' name='csrf_token' value='{{ csrf_token() }}'>{% endif %}
    <label for="eposta">E-posta</label>: <input type="text" id="eposta" name="eposta" value="{{ email }}" autocomplete="username"><br><br>
    <label for="sifre">Şifre</label>: <input type="password" id="sifre" name="sifre" autocomplete="current-password"><br><br>
    <input type="submit" value="Giriş Yap"></form>
<p>{{ note }}</p>
</body></html>
"""


def login_page(message=None, error=False, email=""):
    return render_template_string(LOGIN_PAGE, message=message, error=error, email=email,
                                  note=MSG_LOCK_NOTE)


def register_auth(app, logins):
    """Kapi, giris ve cikis. app.py bunu CSRFProtect'ten ONCE cagirir: giris yapmamis birinin
    istegi CSRF hata sayfasina (Talepler, veriyle) ulasmadan girise yonlenir (plan 0019 Risk 3)."""

    def current_account():
        return logins.session_account(session.get("hesap"), session.get("giris"))

    def drop_login():
        # Oturumun tamami degil: giris formunun CSRF token'i silinirse araya giren bir istek
        # (/favicon.ico, ikinci sekme) sonraki girisi "Form gecersiz" ile reddettirir (F-1).
        for key in LOGIN_KEYS:
            if key in session:
                session.pop(key)

    @app.before_request
    def require_login():
        if request.endpoint in OPEN_ENDPOINTS:
            return None
        try:
            account = current_account()
        except SessionExpired:
            drop_login()
            return redirect("/giris?durum=sure")
        if account is None:
            # Oturum yok, bozuk, hesap silinmis ya da pasif (R-8): hicbir sey degismez
            drop_login()
            return redirect("/giris")
        g.account = account
        return None

    @app.route("/giris", methods=["GET", "POST"], endpoint="login")
    def login():
        if request.method == "POST":
            email = request.form.get("eposta", "")
            try:
                account = logins.authenticate(email, request.form.get("sifre", ""))
            except LoginRefused:
                # Her neden ayni ileti ve durum kodu (R-3, G-1); sifre geri basilmaz
                return login_page(MSG_LOGIN_FAILED, error=True, email=email), 401
            # Onceki oturum verisi temizlenir (D-5, oturum sabitleme)
            session.clear()
            session["hesap"] = account["email"]
            session["giris"] = logins.session_start()
            session.permanent = True
            return redirect("/")  # her zaman Ana Sayfa; geri donus parametresi yok (S-7)
        try:
            if current_account() is not None:
                return redirect("/")
        except SessionExpired:
            pass
        return login_page(STATUS_MESSAGES.get(request.args.get("durum", "")))

    @app.route("/cikis", methods=["POST"], endpoint="logout")
    def logout():
        # Kapidan gecti: g.account var. CSRF token'i CSRFProtect sinar (R-9)
        logins.logout(g.account["email"])
        session.clear()
        return redirect("/giris?durum=cikis")
