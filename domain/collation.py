# Turkce alfabe sirasi (docs/domain.md BR-11, spec 0028). Locale/ICU kullanilmaz: sonuc sunucunun
# dil ayarina bagli degildir (S-4). Bu modul saati, Flask'i ve depoyu bilmez.
#
# Her karakter bir siraya cevrilir:
#   grup 0 - harf olmayanlar (bosluk, noktalama, rakam): karakter koduna gore, her harften once;
#   grup 1 - alfabedeki harfler (q, w, x Latin yerinde): alfabe sirasiyla;
#   grup 2 - alfabe disi harfler (e-akut, a-umlaut...): karakter koduna gore, z'den sonra.
# Buyuk/kucuk harf ayrilmaz, Turkce kuralla: I -> dotless i, I-dot -> i. Esitlikte metnin kendisi
# karsilastirilir (karakter kodu: genelde buyuk harf once; I-dot/i'de i once, cunku I-dot'un
# kodu buyuktur), boylece sira her zaman aynidir.
ALPHABET = "abcçdefgğhıijklmnoöpqrsştuüvwxyz"
_RANK = {letter: index for index, letter in enumerate(ALPHABET)}
# "İ".lower() iki karakter dondurur (i + birlesik nokta); I ve İ lower()'dan once eslenir.
_TURKISH_LOWER = {"I": "ı", "İ": "i"}


def _char_rank(char):
    lower = _TURKISH_LOWER.get(char) or char.lower()
    if lower in _RANK:
        return (1, _RANK[lower])
    if char.isalpha():
        return (2, ord(lower) if len(lower) == 1 else ord(char))
    return (0, ord(char))


def turkish_sort_key(text):
    """Sort key for `text` in Turkish alphabetical order, case-insensitive (spec 0028 CB-1…CB-3)."""
    return (tuple(_char_rank(char) for char in text), text)
