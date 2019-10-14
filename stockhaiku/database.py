import sqlite3
from pathlib import Path

from pony.orm import *


db = Database()
db.bind(
    provider='sqlite',
    filename=str(Path('./data/database.sqlite').absolute()),
    create_db=True,
)


class Verse(db.Entity):
    id = PrimaryKey(str)
    tags = Required(StrArray)
    syllable_count = Required(int)
    used = Required(bool)
    raw_json = Required(Json)


db.generate_mapping()
