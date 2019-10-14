from typing import Optional, NamedTuple, Union, List, Dict, Any, Tuple
import time
import re

import requests
import redis

import stockhaiku.config as config


class UrlQueue:
    def __init__(self):
       self._redis = redis.Redis()
       self._key = 'stockhaiku:crawler:queue'

    def __len__(self):
        return self._redis.llen(self._key)

    def push(self, url: str):
        self._redis.rpush(self._key, url)

    def pop(self) -> Union[str, type(...)]:
        item = self._redis.blpop(self._key)
        return item[1].decode() if item else None
    
    def __iter__(self):
        while True:
            value = self.pop()
            if value == ...:
                return
            else:
                yield value


class SearchResults(NamedTuple):
    results: List[Dict[str, Any]]
    urls: List[str]
    remaining: int


def _urls(response):
    raw_links = response.headers['Link']
    link_regex = re.compile(r'<(.*?)>; rel="(.*?)"')
    links = {
        match.group(2): match.group(1)
        for match in link_regex.finditer(raw_links)
    }
    return [links['next']] if 'next' in links else []


def _fetch(url: str) -> SearchResults:
    response = requests.get(
        url=url,
        headers={
            'Authorization': f'Client-ID {config.UNSPLASH_ACCESS_KEY}',
        }
    )
    json_body = response.json()
    return SearchResults(
        results=json_body['results'],
        urls=_urls(response),
        remaining=int(response.headers.get('X-Ratelimit-Remaining', '0'))
    )


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


# @db.command()
# def populate():
#     tokenizer = SyllableTokenizer()
#     with open('data/5.jsonl', 'w') as f5, open('data/7.jsonl', 'w') as f7:
#         for result in get_results('dark'):
#             desc = result.get('alt_description')
#             url = result['urls']['regular']
#             words = desc.split(' ')
#             try:
#                 syllables = stockhaiku.nlp.count_syllables(desc)
#             except KeyError:
#                 print(f'Skipping {desc} (unknown words)')
#                 continue
#             # syllables = sum(len(tokenizer.tokenize(word)) for word in words)
#             data = {"desc": desc, "url": url}
#             if syllables == 5:
#                 print(5, desc, url)
#                 f5.write(json.dumps(result) + '\n')
#             elif syllables == 7:
#                 print(7, desc, url)
#                 f7.write(json.dumps(result) + '\n')


def crawl():
    url_queue = UrlQueue()
    for url in url_queue:
        search_result = _fetch(url)
        for url in search_result.urls:
            url_queue.push(url)
        yield from search_result.results
        if search_result.remaining == 0:
            print('Rate limit reached; sleeping for one hour')
            time.sleep(3600)
        else:
            time.sleep(1)
