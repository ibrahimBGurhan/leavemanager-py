# Izin gunu = is gunu (docs/domain.md BR-3, spec 0014). Cumartesi ve Pazar hafta tatili; resmi
# tatiller asagidaki sabit listede (2026-2027, 2429 sayili Kanun; dini bayramlar Diyanet takvimi).
# Arife yarim gunleri tam is gunu sayilir (K-3, OD-9). Liste disindaki yillarda yalniz hafta sonu
# dusulur (K-4, OD-10). Bu modul saati, Flask'i ve depoyu bilmez.
from datetime import date

_EVERY_YEAR = ((1, 1), (4, 23), (5, 1), (5, 19), (7, 15), (8, 30), (10, 29))

HOLIDAYS = frozenset(
    [date(year, month, day) for year in (2026, 2027) for month, day in _EVERY_YEAR]
    + [date(2026, 3, d) for d in (20, 21, 22)]       # Ramazan Bayrami 2026
    + [date(2026, 5, d) for d in (27, 28, 29, 30)]   # Kurban Bayrami 2026
    + [date(2027, 3, d) for d in (9, 10, 11)]        # Ramazan Bayrami 2027
    + [date(2027, 5, d) for d in (16, 17, 18, 19)]   # Kurban Bayrami 2027 (19 Mayis ile cakisir)
)


def count_workdays(start, end):
    # Ters aralik 0 (BR-9 once yakalar). Sure araligin uzunlugundan bagimsiz (spec 0014 S-1).
    if end < start:
        return 0
    weeks, rest = divmod((end - start).days + 1, 7)
    weekdays = weeks * 5 + sum(1 for i in range(rest) if (start.weekday() + i) % 7 < 5)
    holidays = sum(1 for h in HOLIDAYS if start <= h <= end and h.weekday() < 5)
    return weekdays - holidays
