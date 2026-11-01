"""Free UPCitemdb retail suggestions; fixed endpoint, no credentials or writes."""
import json
import logging
import re
import threading
import time
from urllib.parse import urlencode
import httpx
from relicrat.barcodes import barcode_variants
from relicrat.barcode_errors import LookupBusy, LookupTimeout, LookupUnavailable

logger = logging.getLogger(__name__)
_gate = threading.Lock()
_last_request = float('-inf')


def clean(value, maximum):
    if not isinstance(value, str): return ''
    value = value.strip()
    return value if value and len(value) <= maximum and not any(ord(c) < 32 for c in value) else ''


def parse_items(data, reading, limit):
    if not isinstance(data, dict) or data.get('code') != 'OK' or not isinstance(data.get('items'), list):
        raise LookupUnavailable()
    results = []; seen = set(); variants = barcode_variants(reading)
    for row in data['items'][:100]:
        if not isinstance(row, dict): continue
        codes = [row[key] for key in ('ean', 'upc') if row.get(key) not in (None, '')]
        # Reject conflicting identifiers as well as fuzzy matches. GTIN-14 can
        # describe multipacks, so it is never used to identify an individual copy.
        if not codes or any(not isinstance(code, str) or not re.fullmatch(r'(?:[0-9]{8}|[0-9]{12,13})', code) or code not in variants for code in codes): continue
        ident = '0'+codes[0] if len(codes[0]) == 12 else codes[0]; title = clean(row.get('title'), 500)
        if not title or ident in seen: continue
        seen.add(ident)
        description = ['Retail product match; confirm the movie and edition.']
        for key in ('brand', 'category'):
            value = clean(row.get(key), 250)
            if value: description.append(key.capitalize()+': '+value)
        results.append({'id': ident, 'title': title, 'description': ' · '.join(description),
                        'source_url': 'https://www.upcitemdb.com/upc/'+ident, 'fields': {'title': title}})
        if len(results) == limit: break
    return results


def fetch(reading):
    """Bound wire bytes/time; no redirects, compression, user URLs or images."""
    url = 'https://api.upcitemdb.com/prod/trial/lookup?'+urlencode({'upc': reading.value})
    deadline = time.monotonic()+12
    with httpx.Client(timeout=httpx.Timeout(8, connect=3, write=3, pool=1), follow_redirects=False, trust_env=False,
                      headers={'User-Agent':'RelicRat/0.1 (https://github.com/bclark/relicrat)', 'Accept':'application/json', 'Accept-Encoding':'identity'}) as client:
        with client.stream('GET', url) as response:
            if time.monotonic() >= deadline: raise LookupTimeout()
            if response.status_code == 429: raise LookupBusy(retry_after=60)
            if response.status_code in (408, 504): raise LookupTimeout()
            # The documented NOT_FOUND body is parsed separately from an invalid
            # endpoint/proxy 404; neither becomes an invented match.
            if response.status_code not in (200, 404): raise LookupUnavailable()
            if response.headers.get('content-encoding', 'identity').lower() != 'identity': raise LookupUnavailable()
            if response.headers.get('content-type', '').split(';')[0].strip().lower() != 'application/json': raise LookupUnavailable()
            content = bytearray()
            for chunk in response.iter_bytes(16384):
                content.extend(chunk)
                if len(content) > 1024*1024: raise LookupUnavailable()
                if time.monotonic() >= deadline: raise LookupTimeout()
            data = json.loads(content)
            if response.status_code == 404:
                if isinstance(data, dict) and data.get('code') == 'NOT_FOUND': return {'code':'OK', 'items':[]}
                raise LookupUnavailable()
            return data


def search(reading, limit):
    global _last_request
    # One API process today; coordinate across workers before scaling. The free
    # provider plan permits one sustained lookup per ten seconds, 100 per day.
    if not _gate.acquire(blocking=False): raise LookupBusy(retry_after=10)
    try:
        now = time.monotonic()
        if now-_last_request < 10: raise LookupBusy(retry_after=10)
        _last_request = now
        return parse_items(fetch(reading), reading, limit)
    except LookupBusy as error:
        if error.retry_after == 60: _last_request = time.monotonic()+50
        raise
    except (httpx.TimeoutException, LookupTimeout) as error:
        logger.warning('Retail catalog search timeout')
        raise LookupTimeout() from error
    except (httpx.HTTPError, ValueError, TypeError, RecursionError, OSError, LookupUnavailable) as error:
        logger.warning('Retail catalog search unavailable')
        raise LookupUnavailable() from error
    finally:
        _gate.release()
