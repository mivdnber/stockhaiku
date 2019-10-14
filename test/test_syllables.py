import pytest
import stockhaiku.nlp


@pytest.mark.parametrize('sentence, expected_count', [
    ('horse eating a frog', 5),
    ('bronze age ending', 4),
    ('Heavy clouds over mountains', 7),
    ('lunar eclipse', 4),
    ('short-coated wolf', 4),
])
def test_syllable_count(sentence: str, expected_count: int):
    assert stockhaiku.nlp.count_syllables(sentence) == expected_count


@pytest.mark.xfail(expected=KeyError)
def test_unknown_word():
    stockhaiku.nlp.count_syllables('i have a blungeerack')
