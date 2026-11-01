"""MusicBrainz adapter. Fixed HTTPS destinations; no credentials or inventory writes."""
import io
import logging
import json
import re
import threading
import time
from urllib.parse import urlencode, urlsplit
from uuid import UUID
import httpx
from PIL import Image, UnidentifiedImageError

USER_AGENT = 'RelicRat/0.1 (https://github.com/bclark/relicrat)'
logger = logging.getLogger(__name__)
_gate = threading.Lock()
_last_request = float('-inf')


class LookupUnavailable(Exception):
    pass


class LookupTimeout(LookupUnavailable):
    pass


class LookupBusy(Exception):
    pass


def fetch_bytes(url, maximum, *, cover=False):
    """Reject redirects except bounded, approved Cover Art Archive image redirects."""
    deadline = time.monotonic() + 12
    with httpx.Client(timeout=httpx.Timeout(8, connect=3, write=3, pool=1), follow_redirects=False, trust_env=False,
                      headers={'User-Agent': USER_AGENT, 'Accept': 'image/*' if cover else 'application/json','Accept-Encoding':'identity'}) as client:
        for _ in range(4):
            remaining = deadline - time.monotonic()
            if remaining <= 0: raise LookupTimeout()
            parsed = urlsplit(url)
            allowed = parsed.hostname == 'musicbrainz.org' if not cover else (
                parsed.hostname == 'coverartarchive.org' or parsed.hostname == 'archive.org' or
                bool(parsed.hostname and parsed.hostname.endswith('.archive.org')))
            if parsed.scheme != 'https' or parsed.port not in (None,443) or parsed.username or parsed.password or not allowed:
                raise LookupUnavailable()
            with client.stream('GET',url,timeout=httpx.Timeout(min(8,remaining), connect=min(3,remaining), write=min(3,remaining), pool=min(1,remaining))) as response:
                if time.monotonic() >= deadline: raise LookupTimeout()
                if cover and response.status_code in (301,302,303,307,308):
                    url = str(response.url.join(response.headers.get('location','')))
                    continue
                if response.headers.get('content-encoding','identity').lower()!='identity':raise LookupUnavailable()
                if response.status_code != 200:
                    logger.warning('Catalog %s HTTP failure: %s', 'cover' if cover else 'search', response.status_code)
                    if response.status_code==429 and not cover: raise LookupBusy()
                    if response.status_code in (408,504): raise LookupTimeout()
                    raise LookupUnavailable()
                content = bytearray()
                for chunk in response.iter_bytes(16384):
                    content.extend(chunk)
                    if len(content)>maximum:raise LookupUnavailable()
                    if time.monotonic()>deadline:raise LookupTimeout()
                return bytes(content)
    raise LookupUnavailable()


def barcode_variants(reading):
    values = {reading.value}
    if reading.format == 'UPC_A': values.add('0'+reading.value)
    if reading.format == 'EAN_13' and reading.value.startswith('0'): values.add(reading.value[1:])
    return values


def clean(value,maximum=500):
    if not isinstance(value,str):return ''
    value=value.strip()
    return value if value and len(value)<=maximum and not any(ord(c)<32 for c in value) else ''


def parse_releases(data,reading,limit):
    if not isinstance(data,dict) or not isinstance(data.get('releases'),list):raise LookupUnavailable()
    results=[];seen=set();variants=barcode_variants(reading)
    for row in data['releases'][:100]:
        if not isinstance(row,dict):continue
        try:ident=str(UUID(row.get('id','')))
        except (ValueError,TypeError,AttributeError):continue
        barcode=row.get('barcode','')
        if not isinstance(barcode,str) or re.sub(r'[\s-]','',barcode) not in variants:continue
        title=clean(row.get('title'))
        if not title or ident in seen:continue
        seen.add(ident)
        credits=row.get('artist-credit',[])
        artist=''
        if isinstance(credits,list) and len(credits)<=30:
            parts=[]
            for credit in credits:
                if not isinstance(credit,dict):continue
                named=credit.get('artist');fallback=named.get('name') if isinstance(named,dict) else None
                join=credit.get('joinphrase','')
                if not isinstance(join,str) or len(join)>50 or any(ord(c)<32 for c in join):join=''
                parts.append(clean(credit.get('name') or fallback)+join)
            # Join phrases may carry meaningful surrounding spaces.
            artist=clean(''.join(parts))
        media=row.get('media',[]);formats=[]
        if isinstance(media,list):
            for medium in media[:20]:
                value=clean(medium.get('format'),100) if isinstance(medium,dict) else ''
                if value and value not in formats:formats.append(value)
        labels=row.get('label-info',[]);names=[];catalog=[]
        if isinstance(labels,list):
            for entry in labels[:20]:
                if not isinstance(entry,dict):continue
                label=entry.get('label');name=clean(label.get('name')) if isinstance(label,dict) else ''
                number=clean(entry.get('catalog-number'))
                if name and name not in names:names.append(name)
                if number and number not in catalog:catalog.append(number)
        fields={k:v for k,v in {'title':title,'artist':artist,'format':clean(' / '.join(formats),100),
                'date':clean(row.get('date'),20),'country':clean(row.get('country'),80),
                'label':clean(' / '.join(names)),'catalog_number':clean(' / '.join(catalog))}.items() if v}
        description=' · '.join(fields.get(k,'') for k in ('artist','format','date','country','label','catalog_number') if fields.get(k))
        results.append({'id':ident,'title':title,'description':description[:1000],
                        'source_url':'https://musicbrainz.org/release/'+ident,'fields':fields})
        if len(results)==limit:break
    return results


def search(reading,limit):
    global _last_request
    # ponytail: one API process today; coordinate this gate before adding workers.
    if not _gate.acquire(blocking=False):raise LookupBusy()
    try:
        now=time.monotonic()
        if now-_last_request<1:raise LookupBusy()
        _last_request=now
        values=sorted(barcode_variants(reading))
        query='barcode:('+ ' OR '.join(values) +')'
        # Fetch a bounded page; enforce exact barcode equality again after parsing.
        data=json.loads(fetch_bytes('https://musicbrainz.org/ws/2/release/?'+urlencode(
            {'query':query,'fmt':'json','limit':limit}),1024*1024))
        return parse_releases(data,reading,limit)
    except LookupBusy:raise
    except (httpx.TimeoutException,LookupTimeout) as error:
        logger.warning('Catalog search timeout')
        raise LookupTimeout() from error
    except (httpx.HTTPError,ValueError,TypeError,RecursionError,OSError) as error:
        logger.warning('Catalog search failed: %s', type(error).__name__)
        raise LookupUnavailable() from error
    finally:_gate.release()


def cover(ident):
    try:
        ident=str(UUID(ident))
        content=fetch_bytes('https://coverartarchive.org/release/'+ident+'/front-250',2*1024*1024,cover=True)
        with Image.open(io.BytesIO(content)) as image:
            if image.format not in ('JPEG','PNG','WEBP') or image.width*image.height>1_000_000:raise LookupUnavailable()
            output=io.BytesIO();image.convert('RGB').save(output,format='JPEG');return output.getvalue()
    except (httpx.HTTPError,ValueError,TypeError,OSError,Image.DecompressionBombError,UnidentifiedImageError) as error:
        raise LookupUnavailable() from error
