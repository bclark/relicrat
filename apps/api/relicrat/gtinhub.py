"""Free GTINHub retail suggestions; fixed endpoint, no credentials or writes."""
import json
import logging
import re
import threading
import time
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


def parse_product(data, reading, limit):
    if not isinstance(data, dict): raise LookupUnavailable()
    product = data.get('product')
    if data.get('found') is False and product in (None, {}): return []
    if data.get('found') is not True or not isinstance(product, dict): raise LookupUnavailable()
    ident = product.get('gtin'); title = clean(product.get('name'), 500)
    # Only the documented string identifier is authoritative. Nested raw_data,
    # numeric IDs and GTIN-14 packaging codes cannot establish an exact match.
    if not isinstance(ident, str) or not re.fullmatch(r'(?:[0-9]{8}|[0-9]{12,13})', ident) or ident not in barcode_variants(reading) or not title: return []
    if len(ident) == 12: ident = '0'+ident
    description = ['Retail product match; confirm the movie and edition.']
    for key in ('brand', 'category'):
        value = clean(product.get(key), 250)
        if value: description.append(key.capitalize()+': '+value)
    return [{'id':ident, 'title':title, 'description':' · '.join(description),
             'source_url':'https://gtinhub.com/product/'+ident, 'fields':{'title':title}}]


def fetch(reading):
    """Bound wire bytes/time; no redirects, compression, user URLs or images."""
    url = 'https://gtinhub.com/api/v1/product/'+reading.value
    deadline = time.monotonic()+12
    with httpx.Client(timeout=httpx.Timeout(8, connect=3, write=3, pool=1), follow_redirects=False, trust_env=False,
                      headers={'User-Agent':'RelicRat/0.1 (https://github.com/bclark/relicrat)', 'Accept':'application/json', 'Accept-Encoding':'identity'}) as client:
        with client.stream('GET', url) as response:
            if time.monotonic() >= deadline: raise LookupTimeout()
            if response.status_code == 429: raise LookupBusy(retry_after=60)
            if response.status_code in (408, 504): raise LookupTimeout()
            if response.status_code not in (200, 404): raise LookupUnavailable()
            if response.headers.get('content-encoding', 'identity').lower() != 'identity': raise LookupUnavailable()
            if response.headers.get('content-type', '').split(';')[0].strip().lower() != 'application/json': raise LookupUnavailable()
            content = bytearray()
            for chunk in response.iter_bytes(16384):
                content.extend(chunk)
                if len(content) > 1024*1024: raise LookupUnavailable()
                if time.monotonic() >= deadline: raise LookupTimeout()
            data = json.loads(content)
            if response.status_code == 404 and (not isinstance(data, dict) or data.get('found') is not False or data.get('product') not in (None, {})): raise LookupUnavailable()
            return data


def search(reading, limit):
    global _last_request
    # One API process today; coordinate across workers before scaling. The free
    # provider trial permits only ten lookups per day. Keep a conservative
    # ten-second process gate; daily quota is enforced by the provider.
    if not _gate.acquire(blocking=False): raise LookupBusy(retry_after=10)
    try:
        now = time.monotonic()
        if now-_last_request < 10: raise LookupBusy(retry_after=10)
        _last_request = now
        return parse_product(fetch(reading), reading, limit)
    except LookupBusy as error:
        if error.retry_after == 60: _last_request = time.monotonic()+50
        raise
    except (httpx.TimeoutException, LookupTimeout) as error:
        logger.warning('GTIN catalog search timeout')
        raise LookupTimeout() from error
    except (httpx.HTTPError, ValueError, TypeError, RecursionError, OSError, LookupUnavailable) as error:
        logger.warning('GTIN catalog search unavailable')
        raise LookupUnavailable() from error
    finally:
        _gate.release()
