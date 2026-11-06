# Is kurali ihlalleri (docs/conventions.md, Error handling). Turkce mesaji web kurar;
# burada yalniz ihlalin turu ve verisi tasinir.


class LeaveRequestError(Exception):
    pass


class EmployeeNotFound(LeaveRequestError):
    def __init__(self, employee_id):
        super().__init__(employee_id)
        self.employee_id = employee_id


class InvalidDateRange(LeaveRequestError):
    def __init__(self, start, end):
        super().__init__(start, end)
        self.start = start
        self.end = end


class InsufficientBalance(LeaveRequestError):
    # pending: yeni talepte hesaba katilan bekleyen gunler; onayda 0 (spec 0013, K-2/K-4)
    def __init__(self, remaining, requested, pending=0):
        super().__init__(remaining, requested, pending)
        self.remaining = remaining
        self.requested = requested
        self.pending = pending


class NoWorkingDays(LeaveRequestError):
    # Aralikta is gunu yok: yalniz hafta sonu ve/veya resmi tatil (spec 0014, K-5)
    def __init__(self, start, end):
        super().__init__(start, end)
        self.start = start
        self.end = end


class RequestNotFound(LeaveRequestError):
    def __init__(self, request_id):
        super().__init__(request_id)
        self.request_id = request_id


class RequestAlreadyDecided(LeaveRequestError):
    # Talep Beklemede degil: Onaylandi / Reddedildi son durumdur (BR-10)
    def __init__(self, request_id, status):
        super().__init__(request_id, status)
        self.request_id = request_id
        self.status = status


# --- Kullanici hesaplari (spec 0018) ---------------------------------------------------------
# Turkce iletiyi komut satiri araci (app.py) kurar; burada yalniz ihlalin turu ve verisi.

class AccountError(Exception):
    pass


class InvalidEmail(AccountError):
    pass


class EmailTaken(AccountError):
    def __init__(self, email):
        super().__init__(email)
        self.email = email


class UnknownRole(AccountError):
    def __init__(self, role):
        super().__init__(role)
        self.role = role


class EmployeeRequired(AccountError):
    # Personel ve Yonetici hesabi bir personel kaydina baglanmak zorunda (R-1)
    def __init__(self, role):
        super().__init__(role)
        self.role = role


class AccountEmployeeNotFound(AccountError):
    def __init__(self, employee_id):
        super().__init__(employee_id)
        self.employee_id = employee_id


class EmployeeAlreadyHasAccount(AccountError):
    # Bir personele en fazla bir hesap (G-2)
    def __init__(self, employee_id):
        super().__init__(employee_id)
        self.employee_id = employee_id


class PasswordMismatch(AccountError):
    pass


class PasswordTooShort(AccountError):
    def __init__(self, minimum):
        super().__init__(minimum)
        self.minimum = minimum
