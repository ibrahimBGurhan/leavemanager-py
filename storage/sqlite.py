# SQLite deposu (ADR-0001, spec 0017): storage/contract.py LeaveStorage sozlesmesini uygular.
# SQL yalniz bu dosyada (docs/architecture.md kural 4); tum sorgular parametreli (spec 0017 R-9).
# Tek baglanti + kilit: Flask istekleri is parcaciklarinda islenir; tek sunucu, tek surec
# varsayimi (ADR-0001). sqlite3 hatalari StorageUnavailable olarak disari cikar; app.py
# sqlite3 import etmez.
import sqlite3
import threading
from datetime import date, datetime

# Sema adimlari: _MIGRATIONS[n], surum n-1'den n'ye gecer. Eksik adimlar acilista tek islemde
# uygulanir; yarida kalan gecis veritabanini eski surumunde birakir (spec 0018 G-5).
_SCHEMA_V1 = """
CREATE TABLE employees (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    id INTEGER NOT NULL UNIQUE,
    name TEXT NOT NULL,
    department TEXT NOT NULL,
    hire_date TEXT NOT NULL
);
CREATE TABLE requests (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    id INTEGER NOT NULL UNIQUE,
    employee_id INTEGER NOT NULL,
    start TEXT NOT NULL,
    "end" TEXT NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL
);
"""

_SCHEMA_V2 = """
CREATE TABLE accounts (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    employee_id INTEGER UNIQUE,
    active INTEGER NOT NULL,
    failed_attempts INTEGER NOT NULL,
    locked_until TEXT
);
"""

_MIGRATIONS = {1: _SCHEMA_V1, 2: _SCHEMA_V2}
SCHEMA_VERSION = max(_MIGRATIONS)


class StorageUnavailable(Exception):
    """Veritabani acilamadi ya da bu surum onu tanimiyor (spec 0017 R-3, S-4); ya da bir yazma
    reddedildi: tekillik cakismasi ya da kilitli veritabani (add_account, spec 0018 review F-1)."""


class SqliteStorage:

    def __init__(self, path, seed_records=None):
        # seed_records: (personel, talepler); yalniz veritabani bossa yuklenir (R-5, S-3)
        self._lock = threading.Lock()
        try:
            self._db = sqlite3.connect(str(path), check_same_thread=False)
        except sqlite3.Error as e:
            raise StorageUnavailable(str(e)) from e
        try:
            version = self._db.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION:
                # Daha yeni sema: dosyaya hicbir sey yazilmaz (S-4)
                raise StorageUnavailable(
                    "şema sürümü %d, bu uygulama %d'i biliyor" % (version, SCHEMA_VERSION))
            # Yazilabilirlik yoklamasi (review F-1, R-3): salt-okunur dosyada uygulama acilmaz.
            # Gecici bir yazma kilidi alinir ve geri alinir; dosyaya kalici bir sey yazilmaz.
            self._db.execute("BEGIN IMMEDIATE")
            self._db.execute("PRAGMA user_version = %d" % version)
            self._db.rollback()
            self._db.execute("PRAGMA journal_mode=WAL")
            if version < SCHEMA_VERSION:
                # Tek islem: eksik adimlar ve surum birlikte ya da hic (0017 review F-2, 0018 G-5;
                # executescript kendi BEGIN/COMMIT'ini calistirir, disaridaki "with" onu sarmaz).
                # Hata olursa COMMIT calismaz; baglanti asagida kapanir ve islem geri alinir.
                steps = "".join(_MIGRATIONS[n] for n in range(version + 1, SCHEMA_VERSION + 1))
                self._db.executescript("BEGIN;" + steps + "PRAGMA user_version = %d; COMMIT;"
                                       % SCHEMA_VERSION)
            if seed_records is not None and self._is_empty():
                employees, requests = seed_records
                for record in employees:
                    self._insert_employee(record)
                for record in requests:
                    self._insert_request(record)
                self._db.commit()
            # Numara en buyuk numaradan devam eder (K-4); bu nesnede yeniden verilmez (0016)
            self._next_id = (self._db.execute("SELECT MAX(id) FROM requests").fetchone()[0] or 0) + 1
        except sqlite3.Error as e:
            self._db.close()
            raise StorageUnavailable(str(e)) from e
        except StorageUnavailable:
            self._db.close()
            raise

    def close(self):
        with self._lock:
            self._db.close()

    def _is_empty(self):
        employees = self._db.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
        requests = self._db.execute("SELECT COUNT(*) FROM requests").fetchone()[0]
        return employees == 0 and requests == 0

    def _insert_employee(self, record):
        self._db.execute(
            "INSERT INTO employees (id, name, department, hire_date) VALUES (?, ?, ?, ?)",
            (record["id"], record["name"], record["department"], record["hire_date"].isoformat()))

    def _insert_request(self, record):
        self._db.execute(
            'INSERT INTO requests (id, employee_id, start, "end", reason, status) '
            "VALUES (?, ?, ?, ?, ?, ?)",
            (record["id"], record["employee_id"], record["start"].isoformat(),
             record["end"].isoformat(), record["reason"], record["status"]))

    def employees(self):
        with self._lock:
            rows = self._db.execute(
                "SELECT id, name, department, hire_date FROM employees ORDER BY seq").fetchall()
        return [{"id": r[0], "name": r[1], "department": r[2],
                 "hire_date": date.fromisoformat(r[3])} for r in rows]

    def requests(self):
        with self._lock:
            rows = self._db.execute(
                'SELECT id, employee_id, start, "end", reason, status FROM requests '
                "ORDER BY seq").fetchall()
        return [{"id": r[0], "employee_id": r[1], "start": date.fromisoformat(r[2]),
                 "end": date.fromisoformat(r[3]), "reason": r[4], "status": r[5]} for r in rows]

    def add_employee(self, record):
        with self._lock, self._db:
            self._insert_employee(record)

    def add_request(self, record):
        with self._lock, self._db:
            self._insert_request(record)

    def set_request_status(self, request_id, status):
        # is kurali bilmez; bilinmeyen numarada hicbir satir degismez (0016 sozlesmesi)
        with self._lock, self._db:
            self._db.execute("UPDATE requests SET status = ? WHERE id = ?", (status, request_id))

    def accounts(self):
        with self._lock:
            rows = self._db.execute(
                "SELECT email, password_hash, role, employee_id, active, failed_attempts, "
                "locked_until FROM accounts ORDER BY seq").fetchall()
        return [{"email": r[0], "password_hash": r[1], "role": r[2], "employee_id": r[3],
                 "active": bool(r[4]), "failed_attempts": r[5],
                 "locked_until": datetime.fromisoformat(r[6]) if r[6] is not None else None}
                for r in rows]

    def add_account(self, record):
        # E-posta ve personel tekilligi veritabaninda da korunur (review F-1: ayni anda iki
        # hesap-ac); ihlal ya da kilitli veritabani StorageUnavailable olarak cikar.
        locked_until = record["locked_until"]
        try:
            with self._lock, self._db:
                self._insert_account(record, locked_until)
        except sqlite3.Error as e:
            raise StorageUnavailable(str(e)) from e

    def _insert_account(self, record, locked_until):
        self._db.execute(
            "INSERT INTO accounts (email, password_hash, role, employee_id, active, "
            "failed_attempts, locked_until) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (record["email"], record["password_hash"], record["role"], record["employee_id"],
             1 if record["active"] else 0, record["failed_attempts"],
             locked_until.isoformat() if locked_until is not None else None))

    def next_request_id(self):
        with self._lock:
            request_id = self._next_id
            self._next_id += 1
        return request_id
