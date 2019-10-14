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
def populate():
    tokenizer = SyllableTokenizer()
    with open('data/5.jsonl', 'w') as f5, open('data/7.jsonl', 'w') as f7:
        for result in get_results('dark'):
            desc = result.get('alt_description')
            url = result['urls']['regular']
            words = desc.split(' ')
            try:
                syllables = stockhaiku.nlp.count_syllables(desc)
            except KeyError:
                print(f'Skipping {desc} (unknown words)')
                continue
            # syllables = sum(len(tokenizer.tokenize(word)) for word in words)
            data = {"desc": desc, "url": url}
            if syllables == 5:
                print(5, desc, url)
                f5.write(json.dumps(result) + '\n')
            elif syllables == 7:
                print(7, desc, url)
                f7.write(json.dumps(result) + '\n')


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
def generate():
    with open('data/5.jsonl') as f5, open('data/7.jsonl') as f7:
        s5 = [json.loads(x) for x in f5.readlines()]
        s7 = [json.loads(x) for x in f7.readlines()]
    first, last = random.sample(s5, 2)
    second = random.choice(s7)
    lines = [first, second, last]
    images = [Image.open(io.BytesIO(requests.get(l['urls']['regular']).content)) for l in lines]
    width = 600
    height = sum(int(i.size[1] * width / i.size[0]) for i in images)
    font = ImageFont.truetype("fonts/Rokkitt-Medium.ttf", 24)
    out_image = Image.new('RGB', (width, height))
    y_offset = 0
    for image in images:
        image.thumbnail((600, int(image.size[1] * width / image.size[0])), Image.ANTIALIAS)
        out_image.paste(image, (0, y_offset))
        y_offset += image.size[1]
    draw = ImageDraw.Draw(out_image)
    haiku = '\n'.join(l['alt_description'] for l in lines)
    draw.multiline_text((10, 10), haiku, font=font)
    for line in [first, second, last]:
        print(line['alt_description'])
        print(line['urls']['regular'])
    out_image.save('out.png')
    image_as_bytesio = io.BytesIO()
    out_image.save(image_as_bytesio, format='PNG')
    image_as_bytesio.seek(0)
    stockhaiku.facebook.post_update(image_as_bytesio, caption=_get_caption(lines))
    # out_image.show()


if __name__ == '__main__':
    cli()
