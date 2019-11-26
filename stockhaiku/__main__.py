"""
Main entry point for the StockHaiku CLI
"""
import time
import json
import re
import random
import json
import io
from typing import List
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

import click
import requests
from nltk.tokenize.sonority_sequencing import SyllableTokenizer
from pony.orm import db_session, commit, select

import stockhaiku.config as config
import stockhaiku.nlp
import stockhaiku.facebook
import stockhaiku.crawler as crawler
import stockhaiku.rendering as rendering
from stockhaiku.database import Verse, db as database


@click.group('stockhaiku')
def cli():
    pass


@cli.group(help='Photo database related operations')
def db():
    pass


def _fetch(**params):
    return requests.get(
        url='https://api.unsplash.com/search/photos',
        params=params,
        headers={
            'Authorization': f'Client-ID {config.UNSPLASH_ACCESS_KEY}',
        }
    )

def _urls(response):
    raw_links = response.headers['Link']
    link_regex = re.compile(r'<(.*?)>; rel="(.*?)"')
    links = {
        match.group(2): match.group(1)
        for match in link_regex.finditer(raw_links)
    }
    return [links['next']] if 'next' in links else []

def get_results(search_query):
    next_page = 1
    while next_page:
        response = _fetch(query=search_query, page=next_page)
        next_page = _next_page(response)
        links = response.headers['Link']
        print(response.headers)
        data = response.json()
        for result in data['results']:
            if result.get('alt_description'):
                yield result
        time.sleep(1)


@db.command()
def init():
    database.generate_mapping(create_tables=True)


@cli.command()
def crawl():
    for result in crawler.crawl():
        desc = result['alt_description']
        if desc is None:
            continue
        try:
            syllable_count = stockhaiku.nlp.count_syllables(desc)
        except KeyError:
            continue
        if syllable_count not in (5, 7):
            continue
        print(f'{syllable_count}: {desc}')
        with db_session():
            if not Verse.exists(id=result['id']):
                verse = Verse(
                    id=result['id'],
                    tags=[t['title'] for t in result['tags']],
                    used=False,
                    raw_json=result,
                    syllable_count=syllable_count,
                )

@cli.command()
@click.argument('query')
def queue(query: str) -> None:
    queue = crawler.UrlQueue()
    base_url = 'https://api.unsplash.com/search/photos'
    url = f'{base_url}?query={query}'
    queue.push(url)


def _get_caption(lines: List[dict]) -> str:
    haiku = '\n'.join(l['alt_description'] for l in lines)
    attribution = '\n'.join(
        f'{l["user"]["name"]} ({l["user"]["links"]["html"]})'
        for l in lines
    )
    return f'{haiku}\n\n{attribution}\nhttps://unsplash.com'


@cli.command()
@click.option('--tag', '-t', help='Optional tag for which to generate a haiku')
@click.option('--out', '-o', help='Output filename')
@db_session
def generate(tag, out):
    filename = out or f"{time.time()}-movie.mp4"
    haiku = Verse.find_haiku(tag)
    rendering.render_video(haiku, filename=filename)
    # image, image_as_bytesio = rendering.render_image(haiku)
    # image.show()


@cli.command()
def dashboard():
    from stockhaiku.dashboard.main import app
    app.run(debug=True, use_reloader=True)


if __name__ == '__main__':
    cli()
