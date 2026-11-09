# Bellek deposu: testler ve LEAVEMANAGER_STORAGE=memory icin (spec 0017). Uretim deposu SQLite.
import threading

from storage.demo import demo_employees, demo_requests


class MemoryStorage:
    # storage/contract.py LeaveStorage sozlesmesini uygular (spec 0016).
    # Kayitlar sozluk: personel {id, name, department, hire_date};
    # talep {id, employee_id, start, end, reason, status}; hesap (spec 0018) contract.py'de
    def __init__(self):
        self._lock = threading.Lock()  # sayac artirma atomik (spec 0019 G-4)
        self.reset()

    def employees(self):
        return self._employees

    def requests(self):
        return self._requests

    def add_employee(self, record):
        self._employees.append(record)

    def add_request(self, record):
        # sayaca dokunmaz; yeni numarayi next_request_id verir
        self._requests.append(record)

    def set_request_status(self, request_id, status):
        # is kurali bilmez; gecis karari domain'de verilir (spec 0010)
        for r in self._requests:
            if r["id"] == request_id:
                r["status"] = status

    def next_request_id(self):
        request_id = self._next_id
        self._next_id += 1
        return request_id

    def accounts(self):
        return self._accounts

    def add_account(self, record):
        self._accounts.append(record)

    def _account(self, email):
        return next((a for a in self._accounts if a["email"] == email), None)

    def record_login_failure(self, email):
        with self._lock:
            account = self._account(email)
            if account is None:
                return 0
            account["failed_attempts"] += 1
            return account["failed_attempts"]

    def lock_account(self, email, until):
        with self._lock:
            account = self._account(email)
            if account is not None:
                account["locked_until"] = until

    def clear_login_failures(self, email):
        with self._lock:
            account = self._account(email)
            if account is not None:
                account["failed_attempts"] = 0
                account["locked_until"] = None

    def set_account_active(self, email, active):
        with self._lock:
            account = self._account(email)
            if account is not None:
                account["active"] = active

    def reset(self):
        # acilis verisi (storage/demo.py, SEED_DEMO_DATA ile ayni kayitlar); demo verisinde
        # hesap yok (spec 0018 AC-9)
        self._employees = demo_employees()
        self._requests = demo_requests()
        self._accounts = []
        self._next_id = 9
