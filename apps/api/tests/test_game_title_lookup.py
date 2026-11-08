import json

import httpx
from fastapi.testclient import TestClient

from auth_helpers import sign_in
from relicrat import igdb
from relicrat.barcode_providers import TITLE_PROVIDERS
from relicrat.main import app


def test_opt_in_title_lookup_is_owner_only(monkeypatch):
    provider = TITLE_PROVIDERS['igdb']
    monkeypatch.setitem(provider, 'enabled', lambda: False)
    path = '/api/v1/title-lookups/game'
    query = {'title': 'Synthetic Quest'}
    with TestClient(app) as client:
        assert client.post(path, json=query).status_code == 401
        sign_in(client)
        assert client.post(path, json=query).status_code == 404
        types = '/api/v1/collection-settings/types'
        assert client.get(types).json()['game']['title_lookup'] is None
        monkeypatch.setitem(provider, 'enabled', lambda: True)
        assert client.get(types).json()['game']['title_lookup']['provider'] == 'igdb'
        monkeypatch.setitem(provider, 'search', lambda title, limit: [{'title': title, 'limit': limit}])
        assert client.post(path, json=query).json()['candidates'] == [{'title': 'Synthetic Quest', 'limit': 5}]
        assert client.post(path, json={**query, 'url': 'https://untrusted.invalid'}).status_code == 422


def test_title_adapter_pins_transport_and_keeps_results_title_only(monkeypatch):
    monkeypatch.setenv('RELICRAT_IGDB_CLIENT_ID', 'syntheticid')
    monkeypatch.setenv('RELICRAT_IGDB_CLIENT_SECRET', 'syntheticsecret')
    monkeypatch.setattr(igdb, '_token', None)
    monkeypatch.setattr(igdb, '_last_search', float('-inf'))
    requests = []

    def handle(request):
        requests.append(request)
        if str(request.url) == igdb.TOKEN_URL:
            result = {'access_token': 'synthetictoken', 'expires_in': 3600}
        else:
            result = [
                {'id': 7, 'name': 'Synthetic Quest', 'slug': 'synthetic-quest', 'platforms': ['Example 64']},
                {'id': 8, 'name': 'Invalid source', 'slug': '../bad'},
            ]
        return httpx.Response(200, stream=httpx.ByteStream(json.dumps(result).encode()))

    real_client = httpx.Client
    monkeypatch.setattr(igdb.httpx, 'Client', lambda **kwargs: real_client(
        transport=httpx.MockTransport(handle), **kwargs,
    ))
    matches = igdb.search('Synthetic "Quest', 5)
    assert [str(request.url) for request in requests] == [igdb.TOKEN_URL, igdb.GAMES_URL]
    assert b'syntheticsecret' in requests[0].content
    assert b'syntheticsecret' not in requests[1].content
    assert requests[1].headers['authorization'] == 'Bearer synthetictoken'
    assert requests[1].content == b'search "Synthetic Quest"; fields name,slug; limit 5;'
    assert [match['fields'] for match in matches] == [{'title': 'Synthetic Quest'}]
