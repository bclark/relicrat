"""Installed adapters. Config selects an ID, never code, URLs or secrets.

To add an API, implement search(reading, limit) and optionally cover(candidate_id),
then register its bounded field names and public source origin here. Adapters
must validate input/response, pin HTTPS destinations and keep credentials private.
"""
from uuid import UUID
from relicrat import musicbrainz, upcitemdb

PROVIDERS = {
    'upcitemdb': {
        'label': 'UPCitemdb',
        'fields': frozenset({'title'}),
        'source_origin': 'https://www.upcitemdb.com',
        'search': upcitemdb.search,
    },
    'musicbrainz': {
        'label': 'MusicBrainz',
        'fields': frozenset({'title','artist','format','date','country','label','catalog_number'}),
        'source_origin': 'https://musicbrainz.org',
        'search': musicbrainz.search,
        'cover': musicbrainz.cover,
        'canonical_id': lambda ident: str(UUID(ident)),
        'source_url': lambda ident: 'https://musicbrainz.org/release/'+str(UUID(ident)),
    },
}
