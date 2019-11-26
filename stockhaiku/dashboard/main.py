from flask import render_template
from pony.orm import db_session

from .app import app


@app.route('/')
@db_session
def home():
    from stockhaiku.crawler import UrlQueue
    from stockhaiku.database import Verse
    queue = UrlQueue()
    verse_count = Verse.select().count()
    crawl_queue_length = len(queue)
    return render_template(
        'layout.html.j2',
        verse_count=verse_count,
        crawl_queue_length=crawl_queue_length,
    )
