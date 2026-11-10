import hashlib
import io
import json
import os
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

from PIL import Image
from sqlalchemy import delete
from sqlalchemy.orm import Session

from relicrat.models import OwnedCopy
from test_reconciliation import request as reconcile
from test_storage import BASE, assign, reconciliation_setup, setup  # noqa: F401


def test_owner_export_can_be_read_with_standard_tools(setup):
    api, engine, copy_id, items, release_id, locations = setup
    assert reconcile(api, copy_id, items[0], 0, release_id).status_code == 200
    for revision, location in enumerate(locations[1:]):
        assert assign(api, copy_id, location['id'], revision).status_code == 200
    image = io.BytesIO()
    Image.new('RGB', (2, 3)).save(image, 'PNG')
    data = image.getvalue()
    response = api.post(f'{BASE}/{copy_id}/photos', files={'file': ('photo.png', data, 'image/png')})
    assert response.status_code == 201
    photo_id = response.json()['id']

    with Session(engine) as db:
        second = OwnedCopy(provisional_title='Second copy', catalog_item_id=items[0], release_id=release_id)
        provisional = OwnedCopy(provisional_title='Unknown copy')
        db.add_all([second, provisional])
        db.commit()
        second_id, provisional_id = second.id, provisional.id

    def export():
        return subprocess.run(
            [sys.executable, '-m', 'relicrat.owner_export'],
            env={**os.environ, 'DATABASE_URL': engine.url.render_as_string(hide_password=False)},
            capture_output=True, timeout=30,
        )

    try:
        result = export()
        assert result.returncode == 0, result.stderr
        with ZipFile(io.BytesIO(result.stdout)) as archive:
            assert archive.testzip() is None

            def records(name):
                return json.loads(archive.read(f'{name}.json'))

            manifest = records('manifest')
            assert (manifest['format'], manifest['version']) == ('relicrat-owner-export', 1)
            copies = {row['id']: row for row in records('copies')}
            original = copies[str(copy_id)]
            assert original['release_id'] == copies[str(second_id)]['release_id'] == str(release_id)
            assert copies[str(provisional_id)]['release_id'] is None
            releases = {row['id']: row for row in records('releases')}
            assert releases[str(release_id)]['catalog_item_id'] == str(items[0])
            assert original['catalog_item_id'] == str(items[0])
            boxes = {row['id']: row for row in records('storage_locations')}
            assert original['storage_location_id'] == locations[2]['id']
            assert boxes[locations[2]['id']]['parent_id'] == locations[1]['id']
            assert boxes[locations[1]['id']]['parent_id'] == locations[0]['id']
            moves = [row for row in records('movement_history') if row['owned_copy_id'] == str(copy_id)]
            assert [row['after_location_id'] for row in moves] == [loc['id'] for loc in locations[1:]]
            assert moves[1]['before_location_id'] == moves[0]['after_location_id']
            photo = next(row for row in records('photos') if row['id'] == photo_id)
            assert photo['owned_copy_id'] == str(copy_id)
            assert archive.read(photo['path']) == data
            assert photo['sha256'] == hashlib.sha256(data).hexdigest()
            assert 'storage_key' not in photo

        root = Path(os.environ['MEDIA_ROOT'])
        stored = root / photo_id[:2] / f"{photo_id.replace('-', '')}.png"
        stored.write_bytes(bytes(len(data)))
        failure = export()
        assert failure.returncode == 1
        assert b'Size or checksum mismatch' in failure.stderr
    finally:
        with engine.begin() as conn:
            conn.execute(delete(OwnedCopy).where(OwnedCopy.id.in_([second_id, provisional_id])))
