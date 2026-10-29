"""Synthetic rehearsal driver; only invoked inside the fixed disposable stack."""
import difflib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tarfile

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import inspect, select, text

from relicrat.database import session_factory
from relicrat.main import app
from relicrat.models import Category, CatalogItem, Release, ReconciliationEvent, CopyDetailEvent, MediaAsset, OwnedCopy, StorageLocation, CopyLocationEvent, StorageHierarchyGuard

EVIDENCE = Path('/evidence')
MEDIA = Path('/media')
BASE = '/api/v1/inventory'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def canonical_check(expression):
    # PG17 dump/restore pushes the text[] cast into each varchar array element.
    # Recognize only these two exact equivalent spellings, not arbitrary SQL.
    for column, values in (
        ('identification_status', ('unidentified', 'partial', 'identified', 'verified')),
        ('ownership_status', ('owned', 'sold', 'traded', 'lost')),
        ('before_status', ('unidentified', 'partial', 'identified', 'verified')),
    ):
        elements = ', '.join(f"'{value}'::character varying" for value in values)
        original = f"{column}::text = ANY (ARRAY[{elements}]::text[])"
        restored_elements = ', '.join(f"'{value}'::character varying::text" for value in values)
        restored = f"{column}::text = ANY (ARRAY[{restored_elements}])"
        if column == 'before_status':
            original = f"({original}) AND after_status::text = 'identified'::text"
            restored = f"({restored}) AND after_status::text = 'identified'::text"
        if expression == restored:
            return original
    return expression


def check_canonicalization():
    # Positive cast equivalence and negative changed-value/operator controls.
    original = "ownership_status::text = ANY (ARRAY['owned'::character varying, 'sold'::character varying, 'traded'::character varying, 'lost'::character varying]::text[])"
    restored = "ownership_status::text = ANY (ARRAY['owned'::character varying::text, 'sold'::character varying::text, 'traded'::character varying::text, 'lost'::character varying::text])"
    require(canonical_check(restored) == original, 'Cast equivalence check failed')
    for changed in (restored.replace("'lost'", "'missing'"), restored.replace(' = ANY', ' <> ALL')):
        require(canonical_check(changed) != original, 'Changed predicate was hidden')
    original_status = "(before_status::text = ANY (ARRAY['unidentified'::character varying, 'partial'::character varying, 'identified'::character varying, 'verified'::character varying]::text[])) AND after_status::text = 'identified'::text"
    restored_status = "(before_status::text = ANY (ARRAY['unidentified'::character varying::text, 'partial'::character varying::text, 'identified'::character varying::text, 'verified'::character varying::text])) AND after_status::text = 'identified'::text"
    require(canonical_check(restored_status) == original_status, 'History cast equivalence failed')
    for changed in (restored_status.replace("'verified'", "'invalid'"), restored_status.replace("after_status::text =", "after_status::text <>")):
        require(canonical_check(changed) != original_status, 'Changed history predicate hidden')
    require(canonical_check('byte_size >= 0') == 'byte_size >= 0', 'Unrelated check changed')


def snapshot():
    """Capture all seeded row columns and schema, independently of API projection."""
    with session_factory()() as db:
        inspector = inspect(db.bind)
        schema = {}
        for table in sorted(inspector.get_table_names()):
            schema[table] = {
                'columns': inspector.get_columns(table),
                'pk': inspector.get_pk_constraint(table),
                'foreign_keys': inspector.get_foreign_keys(table),
                'checks': inspector.get_check_constraints(table),
                'unique': inspector.get_unique_constraints(table),
                'indexes': inspector.get_indexes(table),
            }
        for table in schema.values():
            for constraint in table['checks']:
                constraint['sqltext'] = canonical_check(constraint['sqltext'])
        revision = db.execute(text('SELECT version_num FROM alembic_version')).scalars().all()
        require(sorted(revision) == sorted(ScriptDirectory.from_config(Config('alembic.ini')).get_heads()),
                'Database is not at the source migration head')
        triggers = db.execute(text("""
            SELECT pg_get_triggerdef(t.oid) FROM pg_trigger t
            JOIN pg_class c ON c.oid = t.tgrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND NOT t.tgisinternal
            ORDER BY c.relname, t.tgname
        """)).scalars().all()
        functions = db.execute(text("""
            SELECT pg_get_functiondef(p.oid) FROM pg_proc p
            JOIN pg_namespace n ON n.oid = p.pronamespace
            WHERE n.nspname = 'public' ORDER BY p.proname, p.oid
        """)).scalars().all()
        rows = {}
        for model in (Category, CatalogItem, Release, OwnedCopy, MediaAsset, ReconciliationEvent, CopyDetailEvent, StorageLocation, CopyLocationEvent, StorageHierarchyGuard):
            rows[model.__tablename__] = [
                {column.name: getattr(row, column.name) for column in model.__table__.columns}
                for row in db.scalars(select(model).order_by(model.id))
            ]
        # Normalize UUIDs, dates and SQLAlchemy types for a portable manifest.
        return json.loads(json.dumps(dict(schema=schema, revision=revision,
                                          triggers=triggers, functions=functions, rows=rows), default=str))


def seed():
    output = io.BytesIO()
    Image.new('RGB', (4, 4), (45, 110, 201)).save(output, format='PNG')
    photo_bytes = output.getvalue()
    with TestClient(app) as api:
        access = api.post('/api/v1/auth/login', json={'password': os.environ['RELICRAT_TEST_OWNER_PASSWORD']})
        require(access.status_code == 200, 'Synthetic owner login failed')
        api.headers['Authorization'] = 'Bearer ' + access.json()['token']
        response = api.post(BASE, json={
            'title': 'Synthetic unidentified comic',
            'description': 'Recovery fixture only; blue cover, issue unknown.',
        })
        require(response.status_code == 201, response.text)
        copy = response.json()
        response = api.post(f"{BASE}/{copy['id']}/photos",
                            files={'file': ('synthetic.png', photo_bytes, 'image/png')})
        require(response.status_code == 201, response.text)
        photo = response.json()
        # Catalog CRUD is outside this rehearsal; seed only synthetic identities.
        with session_factory()() as db:
            category = Category(slug='synthetic-comics', name='Synthetic comics')
            db.add(category)
            db.flush()
            item = CatalogItem(category_id=category.id, canonical_name='Synthetic comic', identity_key='fixture')
            db.add(item)
            db.flush()
            release = Release(catalog_item_id=item.id, release_key='synthetic-edition')
            db.add(release)
            db.commit()
            item_id, release_id = str(item.id), str(release.id)
        for revision, release_value in ((0, release_id), (1, None)):
            response = api.post(f"{BASE}/{copy['id']}/reconcile", json={
                'catalog_item_id': item_id, 'release_id': release_value,
                'expected_revision': revision,
            })
            require(response.status_code == 200, response.text)
            copy = response.json()
        root = api.post('/api/v1/storage-locations', json={'name': 'Synthetic room'}).json()
        child = api.post('/api/v1/storage-locations', json={'name': 'Synthetic box', 'parent_id': root['id']}).json()
        for revision, location in enumerate((root, child)):
            response = api.post(f"{BASE}/{copy['id']}/location", json={
                'storage_location_id': location['id'], 'expected_storage_revision': revision})
            require(response.status_code == 200, response.text)
            copy = response.json()
        response = api.post(f"{BASE}/{copy['id']}/details", json={
            'title': 'Edited synthetic recovery copy', 'edition_label': 'Blue test edition',
            'expected_details_revision': copy['details_revision'],
            'expected_identification_revision': copy['identification_revision']})
        require(response.status_code == 200, response.text)
        copy = response.json()
        edits = api.get(f"{BASE}/{copy['id']}/detail-history").json()
        require(len(edits) == 1, 'Copy edit history missing')
        movements = api.get(f"{BASE}/{copy['id']}/locations").json()
        require(len(movements) == 2, 'Movement history missing')
        history = api.get(f"{BASE}/{copy['id']}/reconciliations").json()
        require(len(history) == 2, 'Reconciliation history missing')
    state = snapshot()
    key = state['rows']['media_assets'][0]['storage_key']
    require(photo['owned_copy_id'] == copy['id'], 'Photo ownership mismatch')
    require(photo['sha256'] == hashlib.sha256(photo_bytes).hexdigest(), 'Upload checksum mismatch')
    require((MEDIA / key).read_bytes() == photo_bytes, 'Upload bytes mismatch')
    EVIDENCE.joinpath('original.png').write_bytes(photo_bytes)
    manifest = dict(copy=copy, photo=photo, edits=edits, history=history, movements=movements, locations=[root, child], storage_key=key, database=state)
    EVIDENCE.joinpath('manifest.json').write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2), flush=True)


def manifest():
    return json.loads(EVIDENCE.joinpath('manifest.json').read_text())


def media_path():
    path = (MEDIA / manifest()['storage_key']).resolve()
    require(path.is_relative_to(MEDIA) and path != MEDIA, 'Invalid fixture storage key')
    return path


def verify():
    expected = manifest()
    actual = snapshot()
    if actual != expected['database']:
        print(''.join(difflib.unified_diff(
            json.dumps(expected['database'], indent=2, sort_keys=True).splitlines(True),
            json.dumps(actual, indent=2, sort_keys=True).splitlines(True),
            fromfile='source', tofile='restored')), flush=True)
        raise RuntimeError('Restored database rows/schema/revision differ')
    with TestClient(app) as api:
        access = api.post('/api/v1/auth/login', json={'password': os.environ['RELICRAT_TEST_OWNER_PASSWORD']})
        require(access.status_code == 200, 'Synthetic owner login failed')
        api.headers['Authorization'] = 'Bearer ' + access.json()['token']
        copy = expected['copy']
        photo = expected['photo']
        response = api.get(f"{BASE}/{copy['id']}")
        require(response.status_code == 200 and response.json() == copy, 'Inventory differs')
        require(api.get(BASE).json() == [copy], 'Inventory list differs')
        require(api.get(f"{BASE}/{copy['id']}/reconciliations").json() == expected['history'],
                'Reconciliation history differs')
        require(api.get(f"{BASE}/{copy['id']}/locations").json() == expected['movements'], 'Movement history differs')
        require(api.get(f"{BASE}/{copy['id']}/detail-history").json() == expected['edits'], 'Copy edit history differs')
        for location in expected['locations']:
            require(api.get(f"/api/v1/storage-locations/{location['id']}").json() == location, 'Location differs')
        response = api.get(f"{BASE}/{copy['id']}/photos")
        require(response.status_code == 200 and response.json() == [photo], 'Photo metadata differs')
        response = api.get(f"{BASE}/{copy['id']}/photos/{photo['id']}")
        require(response.status_code == 200, f'Photo download failed: HTTP {response.status_code}')
        require(response.headers['content-type'] == photo['content_type'], 'Download type differs')
        require(response.content == EVIDENCE.joinpath('original.png').read_bytes(), 'Downloaded photo bytes differ')
        require(hashlib.sha256(response.content).hexdigest() == photo['sha256'], 'Download checksum differs')
    print('Verified UUIDs, reconciliations and referenced identities, inventory, ownership, all row columns, schema, migration head and exact photo bytes.', flush=True)


def main():
    check_canonicalization()
    mode = sys.argv[1]
    if mode == 'seed':
        seed()
    elif mode == 'archive':
        with tarfile.open(EVIDENCE / 'media.tar', 'w') as archive:
            for child in sorted(MEDIA.iterdir()):
                archive.add(child, arcname=child.name)
        print('Archived quiesced media.', flush=True)
    elif mode == 'extract':
        require(not any(MEDIA.iterdir()), 'Restore media directory must be empty')
        # Only this run's generated archive is accepted; data filter also rejects
        # traversal, special files and links escaping the destination.
        with tarfile.open(EVIDENCE / 'media.tar') as archive:
            archive.extractall(MEDIA, filter='data')
        print('Extracted media into separate restore volume.', flush=True)
    elif mode == 'missing':
        media_path().unlink()
        print('Injected missing restored media.', flush=True)
    elif mode == 'corrupt':
        media_path().write_bytes(b'corrupted synthetic media')
        print('Injected corrupted restored media.', flush=True)
    elif mode == 'verify':
        verify()
    else:
        raise ValueError('Unknown rehearsal mode')


if __name__ == '__main__':
    main()
