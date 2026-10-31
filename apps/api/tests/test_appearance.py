"""Appearance previews never write; applying is private, atomic and conflict checked."""
import json
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from relicrat.appearance import SaveAppearance, save_appearance
from relicrat.theme_values import DEFAULT_THEME, PRESETS
from test_copy_details import context

URL = os.getenv('TEST_DATABASE_URL')
pytestmark = pytest.mark.skipif(not URL, reason='TEST_DATABASE_URL not configured')
BASE = '/api/v1/appearance'


@pytest.fixture(autouse=True)
def appearance_reset():
    if not URL: yield; return
    engine = create_engine(URL)
    def reset():
        with engine.begin() as db:
            db.execute(text('UPDATE appearance_settings SET theme=CAST(:theme AS jsonb),revision=0 WHERE id=1'), {'theme':json.dumps(DEFAULT_THEME)})
    reset()
    yield
    reset(); engine.dispose()


def test_preview_apply_noop_conflict_and_owner_boundary(context):
    api, engine, create = context
    copy = create(title='Synthetic unchanged collectible')
    before = api.get(BASE).json()
    assert before['revision'] == 0 and before['theme'] == DEFAULT_THEME
    preview = api.post(BASE+'/preview', json={'theme':PRESETS[2]})
    assert preview.status_code == 200 and preview.json()['styles']['colorScheme'] == 'dark'
    assert api.get(BASE).json() == before
    save = api.post(BASE, json={'theme':PRESETS[2], 'expected_revision':0})
    assert save.status_code == 200 and save.json()['revision'] == 1
    assert api.post(BASE, json={'theme':PRESETS[2], 'expected_revision':1}).json() == save.json()
    assert api.post(BASE, json={'theme':DEFAULT_THEME, 'expected_revision':0}).status_code == 409
    assert api.get(BASE).json()['theme'] == PRESETS[2]
    assert api.get('/api/v1/inventory/'+copy['id']).json() == copy
    with engine.connect() as db:
        assert db.scalar(text('SELECT revision FROM appearance_settings WHERE id=1')) == 1
    api.headers.pop('Authorization')
    for path in (BASE, BASE+'/preview'):
        assert api.get(path).status_code == 401
        assert api.post(path, json={'theme':DEFAULT_THEME,'expected_revision':1}).status_code == 401


def test_invalid_theme_never_writes_and_error_explains_contrast(context):
    api, _, _ = context
    before = api.get(BASE).json()
    bad = {**DEFAULT_THEME, 'colors':{**DEFAULT_THEME['colors'], 'ink':'#ffffff'}}
    for path in (BASE, BASE+'/preview'):
        payload = {'theme':bad, **({'expected_revision':0} if path == BASE else {})}
        response = api.post(path,json=payload)
        assert response.status_code == 422 and 'contrast' in response.json()['detail']
    for payload in ({'theme':DEFAULT_THEME,'expected_revision':True}, {'theme':{**DEFAULT_THEME,'css':'bad'},'expected_revision':0}):
        assert api.post(BASE,json=payload).status_code == 422
    assert api.get(BASE).json() == before


def test_direct_sql_bounds(context):
    _, engine, _ = context
    bad_themes = [None, {}, [], {**DEFAULT_THEME,'font':'https://example.test/font'},
                  {**DEFAULT_THEME,'colors':{}}, {**DEFAULT_THEME,'colors':{**DEFAULT_THEME['colors'],'page':None}},
                  {**DEFAULT_THEME,'colors':{**DEFAULT_THEME['colors'],'page':'url(secret)'}},
                  {**DEFAULT_THEME,'colors':{**DEFAULT_THEME['colors'],'extra':'#ffffff'}},
                  {**DEFAULT_THEME,'css':'display:none'}, {**DEFAULT_THEME,'schema_version':True}]
    for theme in bad_themes:
        with pytest.raises(DBAPIError), engine.begin() as db:
            db.execute(text('UPDATE appearance_settings SET theme=CAST(:theme AS jsonb) WHERE id=1'),{'theme':json.dumps(theme)})
    with pytest.raises(DBAPIError), engine.begin() as db:
        db.execute(text('UPDATE appearance_settings SET revision=-1 WHERE id=1'))


def test_failed_commit_rolls_back(context):
    api, engine, _ = context
    before = api.get(BASE).json()
    def fail(connection): raise RuntimeError('Synthetic commit failure')
    with Session(engine) as db:
        event.listen(engine,'commit',fail)
        try:
            with pytest.raises(RuntimeError, match='Synthetic commit failure'):
                save_appearance(SaveAppearance(theme=PRESETS[1],expected_revision=0),db)
        finally: event.remove(engine,'commit',fail)
    assert api.get(BASE).json() == before


def test_concurrent_theme_apply_only_one_wins(context):
    _, engine, _ = context
    barrier = Barrier(2)
    def apply(theme):
        with Session(engine) as db:
            barrier.wait(timeout=10)
            try: return save_appearance(SaveAppearance(theme=theme, expected_revision=0), db)['revision']
            except HTTPException as error: return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(apply, PRESETS[1:]))
    assert sorted(results) == [1,409]
