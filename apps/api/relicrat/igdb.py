"""Opt-in title suggestions; credentials and transport stay on the API server."""
import json
import os
import re
import threading
import time

import httpx

from relicrat.barcode_errors import LookupBusy, LookupUnavailable

TOKEN_URL = 'https://id.twitch.tv/oauth2/token'
GAMES_URL = 'https://api.igdb.com/v4/games'
_gate = threading.Lock()
_token = None
_expires = 0.0
_last_search = float('-inf')


def enabled():
    return bool(os.getenv('RELICRAT_IGDB_CLIENT_ID') and os.getenv('RELICRAT_IGDB_CLIENT_SECRET'))


def request(client, url, **kwargs):
    with client.stream('POST', url, **kwargs) as response:
        if response.status_code == 429:
            raise LookupBusy(retry_after=10)
        response.raise_for_status()
        if response.headers.get('content-encoding', 'identity') != 'identity':
            raise LookupUnavailable()
        body = bytearray()
        deadline = time.monotonic() + 6
        for chunk in response.iter_raw(chunk_size=16384):
            body.extend(chunk)
            if len(body) > 256 * 1024 or time.monotonic() > deadline:
                raise LookupUnavailable()
        return json.loads(body)


def search(title, limit):
    global _token, _expires, _last_search
    if not enabled():
        raise LookupUnavailable()
    if not _gate.acquire(blocking=False):
        raise LookupBusy(retry_after=2)
    try:
        now = time.monotonic()
        if now - _last_search < 2:
            raise LookupBusy(retry_after=2)
        _last_search = now
        client_id = os.environ['RELICRAT_IGDB_CLIENT_ID']
        with httpx.Client(timeout=6, trust_env=False, follow_redirects=False,
                          headers={'Accept-Encoding': 'identity', 'Accept': 'application/json'}) as client:
            if not _token or now >= _expires:
                auth = request(client, TOKEN_URL, data={
                    'client_id': client_id, 'client_secret': os.environ['RELICRAT_IGDB_CLIENT_SECRET'],
                    'grant_type': 'client_credentials',
                })
                if not isinstance(auth, dict):
                    raise LookupUnavailable()
                token, expires_in = auth.get('access_token'), auth.get('expires_in')
                if not isinstance(token, str) or not token.isascii() or not token.isalnum() or len(token) > 256 or type(expires_in) is not int or not 0 < expires_in <= 10**9:
                    raise LookupUnavailable()
                _token, _expires = token, now + max(0, expires_in - 60)
            # Quote and backslash are removed before embedding text in the provider's query grammar.
            term = ' '.join(title.replace('"', ' ').replace(chr(92), ' ').split())
            rows = request(client, GAMES_URL,
                           headers={'Client-ID': client_id, 'Authorization': f'Bearer {_token}'},
                           content=f'search {json.dumps(term, ensure_ascii=False)}; fields name,slug; limit {limit};')
    except httpx.HTTPStatusError as error:
        if error.response.status_code == 401:
            _token = None
        raise LookupUnavailable() from None
    except (httpx.HTTPError, ValueError, OverflowError):
        raise LookupUnavailable() from None
    finally:
        _gate.release()
    if not isinstance(rows, list):
        raise LookupUnavailable()
    candidates = []
    seen = set()
    for row in rows[:limit]:
        if not isinstance(row, dict):
            continue
        ident, name, slug = row.get('id'), row.get('name'), row.get('slug')
        if (type(ident) is not int or ident <= 0 or ident in seen
                or not isinstance(name, str) or not name.strip() or len(name) > 500
                or any(ord(c) < 32 or 0xd800 <= ord(c) <= 0xdfff for c in name)
                or not isinstance(slug, str) or not re.fullmatch(r'[a-z0-9-]{1,200}', slug)):
            continue
        seen.add(ident)
        candidates.append({
            'id': str(ident), 'title': name.strip(), 'description': 'Catalog title; verify your physical release separately.',
            'source_url': f'https://www.igdb.com/games/{slug}', 'cover_url': None,
            'fields': {'title': name.strip()},
        })
    return candidates
