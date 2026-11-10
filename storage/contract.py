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

    def next_employee_id(self) -> int:
        """Yeni personel numarasi (spec 0022 R-2): next_request_id ile ayni sozlesme. Depo
        acildiginda var olan ve bu depodan daha once verilmis tum personel numaralarindan buyuk,
        her cagrida artan; ayni depo nesnesi icinde verilen bir numara (kullanilmasa da) yeniden
        verilmez; ayni anda gelen cagrilar ayri numara alir (G-5). Bos depoda ilk numara 1'dir.
        Depo acildiktan sonra next_employee_id() disindan numara verilen personel kayitlarinda
        sayacin davranisi tanimsizdir."""
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
        rol ve personel kurallari cagiranin (domain) sorumlulugudur. Bir depo, ayni anda
        eklenen cakisan bir kaydi (ayni e-posta ya da personel) reddedebilir; SqliteStorage bunu
        StorageUnavailable ile yapar (spec 0018 review F-1)."""
        ...

    # Giris durumu (spec 0019). Dordu de bilinmeyen e-postada sessizce hicbir sey yapmaz; kacinci
    # denemede kilitlenecegi ve kilidin suresi domain'in karari (domain/auth.py).
    def record_login_failure(self, email: str) -> int:
        """Hesabin art arda basarisiz deneme sayacini atomik olarak 1 artirir ve yeni degeri doner
        (ayni anda gelen artirmalar kaybolmaz, spec 0019 G-4). Bilinmeyen e-postada 0."""
        ...

    def lock_account(self, email: str, until) -> None:
        """Hesabin kilit bitis zamanini (datetime) yazar; sayaca dokunmaz."""
        ...

    def clear_login_failures(self, email: str) -> None:
        """Sayaci 0, kilidi yok yapar."""
        ...

    def set_account_active(self, email: str, active: bool) -> None:
        """Hesabi aktif ya da pasif yapar."""
        ...
