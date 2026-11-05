# Depo sozlesmesi (spec 0016, ADR-0001): her depo uygulamasi (MemoryStorage; 0017'de
# SqliteStorage) bunu saglar ve tests/test_storage_contract.py'den gecer. Yalniz domain'in
# guvendigi davranis yazilidir; bir uygulamaya ozgu ayrintilar (canli liste nesnesi, acilis
# verisi) sozlesme degildir. reset() sozlesmede yok: testlerin acilis verisine donme yardimcisi.
from typing import Protocol, runtime_checkable


@runtime_checkable
class LeaveStorage(Protocol):
    """Personel ve izin talebi kayitlari.

    Kayitlar sozluktur:
    - personel: {id: int, name: str, department: str, hire_date: date}
    - talep: {id: int, employee_id: int, start: date, end: date, reason: str, status: str}

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
        """Talep kaydini numarasiyla listenin sonuna ekler. Sayaca dokunmaz: numarayi yalniz
        next_request_id() verir."""
        ...

    def next_request_id(self) -> int:
        """Yeni talep numarasi: var olan tum numaralardan buyuk, her cagrida artan; verilen bir
        numara (kullanilmasa da) yeniden verilmez."""
        ...

    def set_request_status(self, request_id: int, status: str) -> None:
        """Yalniz o talebin durumunu degistirir. Bilinmeyen numarada sessizce hicbir sey yapmaz
        (gecis karari domain'de, spec 0010)."""
        ...
