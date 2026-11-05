# Bellek deposu: testler ve LEAVEMANAGER_STORAGE=memory icin (spec 0017). Uretim deposu SQLite.
from storage.demo import demo_employees, demo_requests


class MemoryStorage:
    # storage/contract.py LeaveStorage sozlesmesini uygular (spec 0016).
    # Kayitlar sozluk: personel {id, name, department, hire_date};
    # talep {id, employee_id, start, end, reason, status}
    def __init__(self):
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

    def reset(self):
        # acilis verisi (storage/demo.py, SEED_DEMO_DATA ile ayni kayitlar)
        self._employees = demo_employees()
        self._requests = demo_requests()
        self._next_id = 9
