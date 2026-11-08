"""Real PostgreSQL sessions, logout/rotation/expiry and serialized failed logins."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, select, text
from sqlalchemy.orm import Session

from relicrat.auth import now
from relicrat.credentials import hash_password
from relicrat.main import app
from relicrat.models import OwnerSession

URL = os.getenv('TEST_DATABASE_URL')
pytestmark = pytest.mark.skipif(not URL, reason='TEST_DATABASE_URL not configured')
PASSWORD = 'synthetic-only-owner-password'


@pytest.fixture
def setup():
    assert os.getenv('DATABASE_URL') == URL, 'Auth tests require the isolated test database'
    engine = create_engine(URL)
    with engine.begin() as connection:
        connection.execute(text('UPDATE owner_login_guard SET failures=0, window_started_at=now(), blocked_until=NULL'))
        connection.execute(delete(OwnerSession))
    with TestClient(app, raise_server_exceptions=False) as api:
        yield api, engine
    engine.dispose()


def login(api, password=PASSWORD):
    return api.post('/api/v1/auth/login', json={'password': password})


def test_guest_data_and_uploads_are_rejected_before_parsing_and_docs_are_not_public(setup):
    api, _ = setup
    for path in ['/api/v1/inventory', '/api/v1/storage-locations', '/api/v1/catalog/items', '/api/v1/auth/session', '/docs', '/openapi.json']:
        response = api.get(path)
        assert response.status_code == 401, response.text
        assert response.headers['cache-control'] == 'no-store'
    response = api.post('/api/v1/inventory', content=b'not-json', headers={'Content-Type': 'application/json'})
    assert response.status_code == 401
    assert api.post('/api/v1/inventory/not-a-copy/photos', content=b'not-multipart', headers={'Content-Type': 'multipart/form-data'}).status_code == 401
    assert api.get('/health').json() == {'status': 'ok'}
    assert api.get('/api/v1/inventory', headers={'Cookie': 'relicrat_loopback_session=' + 'a'*43}).status_code == 401
    assert api.get('/api/v1/inventory?token=' + 'a'*43).status_code == 401


def test_login_stores_only_hashes_and_logout_replay_is_rejected(setup):
    api, engine = setup
    result = login(api)
    assert result.status_code == 200, result.text
    token = result.json()['token']
    assert len(token) == 43
    headers = {'Authorization': 'Bearer ' + token}
    assert api.get('/api/v1/auth/session', headers=headers).json()['authenticated'] is True
    with Session(engine) as db:
        session = db.scalar(select(OwnerSession))
        assert session.token_hash != token and token not in repr(session.__dict__)
        assert session.expires_at > now() and session.expires_at <= now() + timedelta(hours=12)
    assert api.get('/api/v1/inventory', headers=headers).status_code == 200
    assert api.post('/api/v1/auth/logout', headers=headers).status_code == 200
    assert api.get('/api/v1/inventory', headers=headers).status_code == 401
    with Session(engine) as db:
        assert db.scalar(select(OwnerSession)).revoked_at is not None


def test_expired_sessions_password_rotation_and_secret_rotation_end_access(setup, monkeypatch):
    api, engine = setup
    token = login(api).json()['token']
    headers = {'Authorization': 'Bearer ' + token}
    monkeypatch.setenv('RELICRAT_SESSION_SECRET', '29' * 32)
    assert api.get('/api/v1/inventory', headers=headers).status_code == 401
    token = login(api).json()['token']; headers['Authorization'] = 'Bearer ' + token
    monkeypatch.setenv('RELICRAT_OWNER_PASSWORD_HASH', hash_password('a-different-synthetic-password'))
    assert api.get('/api/v1/inventory', headers=headers).status_code == 401
    token = login(api, 'a-different-synthetic-password').json()['token']; headers['Authorization'] = 'Bearer ' + token
    with engine.begin() as connection:
        connection.execute(text("UPDATE owner_sessions SET expires_at=now()-interval '1 second'"))
    assert api.get('/api/v1/inventory', headers=headers).status_code == 401


def test_bounded_login_and_validation_never_echo_passwords(setup):
    api, _ = setup
    password = 'private-' * 40
    response = login(api, password)
    assert response.status_code == 413 or response.status_code == 422
    assert password not in response.text
    for payload in ({'password': '', 'extra': True}, {'password': 'x', 'extra': True}, {'other': 'secret'}):
        response = api.post('/api/v1/auth/login', json=payload)
        assert response.status_code == 422
        assert 'input' not in response.text
    assert api.post('/api/v1/auth/login', content=b'x'*2049, headers={'Content-Type': 'application/json'}).status_code == 413
    assert login(api, 'incorrect-password').status_code == 401


def test_failed_login_limit_is_serialized_and_expires(setup):
    api, engine = setup
    with ThreadPoolExecutor(max_workers=6) as pool:
        statuses = list(pool.map(lambda _: login(api, 'incorrect-password').status_code, range(6)))
    assert sorted(statuses) == [401]*5 + [429]
    blocked = login(api)
    assert blocked.status_code == 429 and int(blocked.headers['Retry-After']) > 0
    with engine.begin() as connection:
        connection.execute(text("UPDATE owner_login_guard SET window_started_at=now()-interval '16 minutes', blocked_until=now()-interval '1 second'"))
    assert login(api).status_code == 200


def test_missing_owner_configuration_fails_closed(setup, monkeypatch):
    api, _ = setup
    monkeypatch.delenv('RELICRAT_OWNER_PASSWORD_HASH')
    assert login(api).status_code == 503
    assert api.get('/api/v1/inventory').status_code == 503


def test_revocable_agent_credential_reads_only_collection_projections(setup, monkeypatch):
    from uuid import uuid4

    from relicrat.models import AgentCredential, LocationAudit

    api, engine = setup
    owner = {'Authorization': 'Bearer ' + login(api).json()['token']}
    base = '/api/v1'
    management = base + '/auth/agent-credential'
    reads = base + '/agent'
    audit_id = uuid4()

    def create(path, payload, status=201):
        response = api.post(base + path, headers=owner, json=payload)
        assert response.status_code == status, response.text
        return response.json()

    box = create('/storage-locations', {'name': 'Synthetic agent audit box'})
    destination = create('/storage-locations', {'name': 'Synthetic agent destination'})
    copy = create('/inventory', {'title': 'Synthetic agent search copy', 'description': 'Private test note'})
    location = f"/inventory/{copy['id']}/location"
    move = {'storage_location_id': box['id'], 'expected_storage_revision': 0}
    create(location, move, status=200)
    audits = f"/storage-locations/{box['id']}/audits"
    preview = api.get(base + audits, headers=owner).json()

    try:
        create(audits, {'request_id': str(audit_id), 'snapshot': preview['snapshot'],
                        'found_ids': [], 'extras': ['Synthetic extra']}, status=200)
        assert api.post(management).status_code == 401
        issued = api.post(management, headers=owner)
        assert issued.status_code == 201
        assert issued.headers['cache-control'] == 'no-store'
        token = issued.json()['token']
        agent = {'Authorization': 'Bearer ' + token}
        with Session(engine) as db:
            stored = db.get(AgentCredential, 1)
            assert stored.token_hash != token and token not in repr(stored.__dict__)

        expected = {'id': copy['id'], 'title': copy['title'], 'edition': None,
                    'location': {'id': box['id'], 'name': box['name']}}
        search = api.get(reads + '/copies', headers=agent, params={'q': copy['title'], 'limit': 1})
        assert search.status_code == 200 and search.json() == [expected]
        assert api.get(reads + '/copies', headers=agent, params={'limit': 101}).status_code == 422
        assert api.get(f"{reads}/copies/{copy['id']}", headers=agent).json() == expected
        findings = api.get(reads + '/unresolved-locations', headers=agent)
        assert findings.status_code == 200
        assert {'id': box['id'], 'name': box['name'], 'unresolved': 2} in findings.json()

        denied = api.post(base + location, headers=agent,
                          json={'storage_location_id': destination['id'], 'expected_storage_revision': 1})
        assert denied.status_code == 403
        assert api.get(f"{reads}/copies/{copy['id']}", headers=agent).json() == expected
        assert api.get(base + '/inventory', headers=agent).status_code == 403
        assert api.post(reads + '/copies', headers=agent).status_code == 403
        assert api.post(management, headers=agent).status_code == 403
        assert api.delete(management, headers=agent).status_code == 403

        replacement = api.post(management, headers=owner).json()['token']
        assert api.get(reads + '/copies', headers=agent).status_code == 401
        agent = {'Authorization': 'Bearer ' + replacement}
        assert api.get(reads + '/copies', headers=agent).status_code == 200
        with monkeypatch.context() as settings:
            settings.setenv('RELICRAT_SESSION_SECRET', '29' * 32)
            assert api.get(reads + '/copies', headers=agent).status_code == 401
        assert api.delete(management, headers=owner).json() == {'active': False}
        assert api.get(reads + '/copies', headers=agent).status_code == 401
    finally:
        with engine.begin() as connection:
            connection.execute(delete(LocationAudit).where(LocationAudit.id == audit_id))
            connection.execute(delete(AgentCredential).where(AgentCredential.id == 1))
