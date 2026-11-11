"""Turkish alphabetical order for unit suggestions — spec 0028 (issue #43, 0022 G-2).

CB-1: the 29 Turkish letters in order, q, w, x in their Latin places. CB-2: case-insensitive with
Turkish case pairs (I-ı, İ-i); a tie is broken by the text itself, so the order never changes.
CB-3: non-letters (space, punctuation, digits) before every letter; letters outside the alphabet
after z. The rule is read without Flask, storage or the clock (plan 0028 Risk 1).
"""
import itertools

import pytest

from domain.collation import ALPHABET, turkish_sort_key


def ordered(*texts):
    return sorted(texts, key=turkish_sort_key)


def test_alphabet_is_turkish_with_q_w_x_in_their_latin_places():
    assert ALPHABET == "abcçdefgğhıijklmnoöpqrsştuüvwxyz"


@pytest.mark.parametrize("before, after", list(itertools.pairwise(ALPHABET)))
def test_each_letter_comes_before_the_next(before, after):
    assert ordered(after, before) == [before, after]
    upper = {"ı": "I", "i": "İ"}
    assert ordered(upper.get(after, after.upper()), upper.get(before, before.upper())) == [
        upper.get(before, before.upper()), upper.get(after, after.upper())]


def test_turkish_letters_are_not_pushed_after_z():
    assert ordered("Zemin", "Üretim", "Şube", "Özel", "İdari", "Çağrı", "Ilık", "Ğ") == [
        "Çağrı", "Ğ", "Ilık", "İdari", "Özel", "Şube", "Üretim", "Zemin"]


@pytest.mark.parametrize("upper, lower", [("I", "ı"), ("İ", "i"), ("Ç", "ç"), ("Ğ", "ğ"),
                                          ("Ö", "ö"), ("Ş", "ş"), ("Ü", "ü"), ("A", "a")])
def test_turkish_case_pairs_are_the_same_letter(upper, lower):
    assert turkish_sort_key(upper)[0] == turkish_sort_key(lower)[0]


def test_dotless_capital_i_is_not_i():
    assert turkish_sort_key("I")[0] != turkish_sort_key("i")[0]
    assert ordered("it", "IT", "İz", "ız") == ["IT", "ız", "it", "İz"]


def test_capital_dotted_i_is_one_letter():
    # "İ".lower() is two characters in Python; the rule maps it first (plan 0028 Risk 2).
    assert turkish_sort_key("İK")[0] == turkish_sort_key("ik")[0]
    assert ordered("İK", "ij", "il") == ["ij", "İK", "il"]


def test_case_only_differences_are_adjacent_capital_first_and_stable():
    texts = ["arge", "Arge", "ARGE", "Arge", "Argf", "arga"]
    assert ordered(*texts) == ["arga", "ARGE", "Arge", "Arge", "arge", "Argf"]
    for perm in itertools.permutations(["arge", "Arge", "ARGE"]):
        assert ordered(*perm) == ["ARGE", "Arge", "arge"]
    # Review F-1: the tie is the character code, and U+0130 (İ) is above i (U+0069).
    assert ordered("İzmir", "izmir") == ["izmir", "İzmir"]


def test_non_letters_come_before_letters():
    assert ordered("ITA", "IT Destek") == ["IT Destek", "ITA"]
    assert ordered("arge", "ar-ge", "ar ge", "ar2ge") == ["ar ge", "ar-ge", "ar2ge", "arge"]
    assert ordered("a", "2. Bölge", "-", " ") == [" ", "-", "2. Bölge", "a"]


def test_letters_outside_the_alphabet_come_after_z():
    assert ordered("Éclair", "zz", "äpfel", "ß", "ab") == ["ab", "zz", "ß", "äpfel", "Éclair"]
    assert turkish_sort_key("É")[0] == turkish_sort_key("é")[0]


@pytest.mark.parametrize("text", ["", " ", "ç", "i̇", "🙂", " ", "Ǆ", "\x00"])
def test_any_text_gets_a_key(text):
    key = turkish_sort_key(text)
    assert key[1] == text
    assert sorted([text, "a", ""], key=turkish_sort_key)[0] == ""


def test_decomposed_accent_is_not_the_turkish_letter():
    # No normalization (plan 0028 Risk 3): c + U+0327 sorts as c followed by a non-letter.
    assert ordered("ç", "ç", "d") == ["ç", "ç", "d"]
