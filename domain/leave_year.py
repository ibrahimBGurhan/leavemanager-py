# Izin yili (docs/domain.md BR-1, BR-2; spec 0040 K-1, K-2, K-7). Hak her ise giris yil
# donumunde, o gun tamamlanan kidemin kademesi kadar dogar; dogan hak yanmaz (K-3). 29 Subat'ta
# ise girenin yil donumu artik olmayan yillarda 28 Subat. Bu modul saati, Flask'i ve depoyu bilmez.
import calendar
from datetime import date


def tier(years):
    # Kidem -> yillik hak (BR-1, Is Kanunu md. 53): 0 -> 0, 1-5 -> 14, 6-14 -> 20, 15+ -> 26
    if years < 1:
        return 0
    if years <= 5:
        return 14
    if years < 15:
        return 20
    return 26


def anniversary(hire, year):
    # O yilin yil donumu; 29 Subat artik olmayan yilda 28 Subat (BR-2)
    if (hire.month, hire.day) == (2, 29) and not calendar.isleap(year):
        return date(year, 2, 28)
    return date(year, hire.month, hire.day)


def last_anniversary(hire, today):
    # Bugun ya da once gelen son yil donumu; ilk yil dolmadiysa None
    year = today.year if anniversary(hire, today.year) <= today else today.year - 1
    return anniversary(hire, year) if year > hire.year else None


def next_anniversary(hire, today):
    # Bugunden sonraki ilk yil donumu (bugun yil donumuyse bir sonraki yilinki)
    year = max(today.year, hire.year + 1)
    if anniversary(hire, year) <= today:
        year += 1
    return anniversary(hire, year)


def rights_born(hire, after, until):
    # (after, until] araliginda dogan haklarin toplami; after None ise ise giristen beri
    total = 0
    for year in range(hire.year + 1, until.year + 1):
        day = anniversary(hire, year)
        if day <= until and (after is None or day > after):
            total += tier(year - hire.year)
    return total
