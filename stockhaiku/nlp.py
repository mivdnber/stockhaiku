from typing import List, Optional
from nltk.corpus import cmudict

cmu = cmudict.dict()


def _cmu_syllables(word):
    desc: List[List[str]] = cmu[word.lower()]
    return len([x for x in desc[0] if x[-1].isdigit()])


def count_syllables(sentence: str) -> Optional[int]:
    return sum(_cmu_syllables(word) for word in sentence.split())
