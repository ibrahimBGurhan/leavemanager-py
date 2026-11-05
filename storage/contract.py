# Depo sozlesmesi (spec 0016, ADR-0001): her depo uygulamasi (MemoryStorage; 0017'de
# SqliteStorage) bunu saglar ve tests/test_storage_contract.py'den gecer. Yalniz domain'in
# guvendigi davranis yazilidir; bir uygulamaya ozgu ayrintilar (canli liste nesnesi, acilis
# verisi) sozlesme degildir. reset() sozlesmede yok: testlerin acilis verisine donme yardimcisi.
from typing import Protocol, runtime_checkable


@runtime_checkable
class LeaveStorage(Protocol):
    """Personel, izin talebi ve kullanici hesabi kayitlari.

    Kayitlar sozluktur:
    - personel: {id: int, name: str, department: str, hire_date: date}
    - talep: {id: int, employee_id: int, start: date, end: date, reason: str, status: str}
    - hesap (spec 0018): {email: str, password_hash: str, role: str, employee_id: int | None,
      active: bool, failed_attempts: int, locked_until: datetime | None}

    Donen kayitlari cagiran degistirmez; degisiklik yalniz asagidaki metotlarla yapilir.
    Depo is kurali bilmez: gecis, bakiye ve dogrulama kararlari domain'dedir.
    """

    def employees(self) -> list:
        """Tum personel kayitlari, eklenme sirasiyla."""
        ...

    def requests(self) -> list:
        """Tum talep kayitlari, eklenme sirasiyla; bir durum degisikligi sonraki okumada gorunur."""
        ...

    def add_employee(self, record: dict) -> None:
        """Personel kaydini listenin sonuna ekler."""
        ...

    def add_request(self, record: dict) -> None:
        """Talep kaydini verilen numarayla listenin sonuna ekler. Numarayi depo atamaz: cagiran
        onu next_request_id()'den alir. Numaralar tekildir (cagiranin sorumlulugu). Depo
        acildiktan sonra next_request_id() disindan numara verilen kayitlarda sayacin davranisi
        tanimsizdir."""
        ...

    def next_request_id(self) -> int:
        """Yeni talep numarasi: depo acildiginda var olan ve bu depodan daha once verilmis tum
        numaralardan buyuk (var olan kayitlarla cakismaz), her cagrida artan; ayni depo nesnesi
        icinde verilen bir numara (kullanilmasa da) yeniden verilmez. Yeniden baslatmadan sonraki
        davranis kalici depo spec'inde (0017 K-4) belirlenir."""
        ...

    def set_request_status(self, request_id: int, status: str) -> None:
        """Yalniz o talebin durumunu degistirir. Bilinmeyen numarada sessizce hicbir sey yapmaz
        (gecis karari domain'de, spec 0010)."""
        ...

    def accounts(self) -> list:
        """Tum hesap kayitlari, eklenme sirasiyla (spec 0018)."""
        ...

    def add_account(self, record: dict) -> None:
        """Hesap kaydini listenin sonuna ekler. E-postanin tekil ve normallestirilmis olmasi,
        rol ve personel kurallari cagiranin (domain) sorumlulugudur."""
        ...
