import sqlite3
from pathlib import Path
from typing import Sequence, Dict, Tuple
import random

from pony.orm import *

from itertools import groupby
from functools import reduce

db = Database()
db.bind(
    provider='sqlite',
    filename=str(Path('./data/database.sqlite').absolute()),
    create_db=True,
)

Haiku = Tuple['Verse', 'Verse', 'Verse']

class Verse(db.Entity):
    id = PrimaryKey(str)
    tags = Required(StrArray)
    syllable_count = Required(int)
    used = Required(bool)
    raw_json = Required(Json)

    @classmethod
    def find_suitable_tags(cls) -> Sequence[str]:
        tag_arrays = select(
            (v.tags, v.syllable_count)
            for v in cls
            if 'photo' not in v.raw_json['alt_description']
        )
        tag_syllable_count_occurrences: Dict[str, Dict[int, int]] = {}
        for tag_array, syllable_count in tag_arrays:
            for tag in tag_array:
                occurrences = tag_syllable_count_occurrences.setdefault(tag, {})
                occurrences.setdefault(syllable_count, 0)
                occurrences[syllable_count] += 1

        return [
            tag
            for tag, occurrences in tag_syllable_count_occurrences.items()
            if occurrences.get(5, 0) >= 2 and occurrences.get(7, 0) >= 1
        ]

    @property
    def alt_description(self):
        return self.raw_json['alt_description']

    @property
    def url(self):
        return self.raw_json['urls']['regular']

    @classmethod
    def find_haiku_by_tag(cls, tag: str) -> Haiku:
        five_first, five_last = select(
            v for v in cls
            if tag in v.tags
            and 'photo' not in v.alt_description
            and not v.used
            and v.syllable_count == 5
        ).random(2)
        seven = select(
            v for v in cls
            if tag in v.tags
            and 'photo' not in v.alt_description
            and not v.used
            and v.syllable_count == 7
        ).random(1)[0]
        return five_first, seven, five_last

    @classmethod
    def find_haiku(cls, tag=None) -> Haiku:
        if tag is None:
            suitable_tags = cls.find_suitable_tags()
            tag = random.choice(suitable_tags)
        return cls.find_haiku_by_tag(tag)


db.generate_mapping()
