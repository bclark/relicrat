import assert from 'node:assert/strict';
import { before, after, test } from 'node:test';
import { mkdir } from 'node:fs/promises';
import { resolve } from 'node:path';
import { chromium } from 'playwright';

const base = process.env.RELICRAT_TEST_WEB_URL || 'http://127.0.0.1:63112';
assert.ok(['127.0.0.1', 'localhost'].includes(new URL(base).hostname) && new URL(base).protocol === 'http:', 'Use an isolated loopback test server');
const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGPgl1QGAACGAEwFRbXWAAAAAElFTkSuQmCC', 'base64');
const id = number => `00000000-0000-0000-0000-${String(number).padStart(12, '0')}`;
const copy = (number, title, extra = {}) => ({ id: id(number), title, description: 'Synthetic test notes', catalog_item_id: null, release_id: null, identification_status: 'unidentified', identification_revision: 0, storage_location_id: null, storage_revision: 0, ownership_status: 'owned', created_at: '2026-10-28T12:00:00Z', updated_at: '2026-10-28T12:00:00Z', ...extra });
const ownerPassword = 'synthetic-only-owner-password';
let browser;
async function signIn(context) {
  const response = await context.request.post(base + '/api/v1/auth/login', { data: { password: ownerPassword }, headers: { Origin: new URL(base).origin } });
  assert.equal(response.status(), 200, await response.text());
}
before(async () => { browser = await chromium.launch({ headless: true, executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || undefined }); });
after(async () => { await browser?.close(); });
async function fixture(t, initial = {}) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1050 } });
  t.after(() => context.close());
  await signIn(context);
  const page = await context.newPage();
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  t.after(() => assert.deepEqual(errors, [], 'Unexpected browser errors'));
  const state = { categories: [], items: [], releases: [], identifications: {}, identificationConflict: false, uncertainIdentification: false, copies: [], locations: [], photos: {}, moves: {}, writes: [], failCreate: '', failPhoto: false, conflict: false, failList: false, ...initial };
  await page.route('**/api/v1/**', async route => {
    const request = route.request(); const url = new URL(request.url());
    const path = url.pathname.replace('/api/v1/', ''); const parts = path.split('/');
    const method = request.method(); let result; let status = 200;
    if (method === 'GET' && path === 'inventory' && state.failList === 'invalid') { await route.fulfill({ status: 200, contentType: 'text/plain', body: 'invalid JSON' }); return; }
    if (method === 'GET' && path === 'inventory' && state.failList === 'network') { await route.abort('failed'); return; }
    if (method === 'POST') state.writes.push({ path, body: path.endsWith('/photos') ? null : request.postDataJSON() });
    if (method === 'GET' && path === 'inventory') {
      if (state.failList) { status = 502; result = { detail: 'Synthetic API unavailable' }; }
      else {
        const q = url.searchParams.get('q') || '';
        if (q === 'Old') await new Promise(resolve => setTimeout(resolve, 400));
        result = state.copies.filter(item => `${item.title || ''} ${item.description || ''}`.toLowerCase().includes(q.toLowerCase()));
        const offset = Number(url.searchParams.get('offset') || 0), limit = Number(url.searchParams.get('limit') || 50);
        result = result.slice(offset, offset + limit);
      }
    } else if (method === 'POST' && path === 'inventory') {
      const payload = request.postDataJSON();
      if (state.failCreate === 'validation') { status = 422; result = { detail: 'Synthetic validation error' }; }
      else {
        const item = copy(state.copies.length + 1, payload.title, { description: payload.description });
        state.copies.unshift(item);
        status = state.failCreate === 'uncertain' ? 502 : 201;
        result = status === 201 ? item : { detail: 'Save could not be confirmed. Reload inventory before retrying.' };
      }
    } else if (parts[0] === 'catalog') {
      const offset = Number(url.searchParams.get('offset') || 0), limit = Number(url.searchParams.get('limit') || 50);
      if (parts[1] === 'categories') {
        if (method === 'GET') result = state.categories.slice(offset, offset + limit);
        else { result = { id: id(3000 + state.categories.length), ...request.postDataJSON() }; state.categories.push(result); status = 201; }
      } else if (parts[1] === 'items' && parts.length === 2) {
        if (method === 'GET') {
          const q = url.searchParams.get('q') || '';
          if (q === 'Old catalog') await new Promise(resolve => setTimeout(resolve, 400));
          result = state.items.filter(item => item.canonical_name.toLowerCase().includes(q.toLowerCase())).slice(offset, offset + limit);
        } else { result = { id: id(4000 + state.items.length), ...request.postDataJSON() }; state.items.push(result); status = 201; }
      } else if (parts.length === 3) result = state.items.find(item => item.id === parts[2]);
      else if (parts[3] === 'releases') {
        if (method === 'GET') result = parts.length === 5 ? state.releases.find(item => item.id === parts[4] && item.catalog_item_id === parts[2]) : state.releases.filter(item => item.catalog_item_id === parts[2]).slice(offset, offset + limit);
        else { result = { id: id(5000 + state.releases.length), catalog_item_id: parts[2], ...request.postDataJSON() }; state.releases.push(result); status = 201; }
      }
    } else if (path === 'storage-locations' && method === 'GET') {
      const offset = Number(url.searchParams.get('offset') || 0), limit = Number(url.searchParams.get('limit') || 50);
      result = state.locations.slice(offset, offset + limit);
    } else if (parts[0] === 'storage-locations' && parts.length === 2) {
      result = state.locations.find(location => location.id === parts[1]);
    } else if (path === 'storage-locations' && method === 'POST') {
      const payload = request.postDataJSON(); result = { id: id(1000 + state.locations.length), ...payload }; state.locations.push(result); status = 201;
    } else if (parts[0] === 'inventory') {
      const cid = parts[1], item = state.copies.find(item => item.id === cid);
      if (parts.length === 2) {
        if (item?.title === 'Old record') await new Promise(resolve => setTimeout(resolve, 400));
        result = item;
      } else if (parts[2] === 'photos' && method === 'GET') {
        if (parts.length === 4) { await route.fulfill({ status: 200, contentType: 'image/png', body: png }); return; }
        result = state.photos[cid] || [];
      } else if (parts[2] === 'photos' && method === 'POST') {
        if (state.failPhoto) { status = 422; result = { detail: 'Invalid image' }; }
        else { result = { id: id(500 + state.writes.length), owned_copy_id: cid, content_type: 'image/png', byte_size: png.length }; state.photos[cid] = [result, ...(state.photos[cid] || [])]; status = 201; }
      } else if (parts[2] === 'reconciliations') {
        const offset = Number(url.searchParams.get('offset') || 0), limit = Number(url.searchParams.get('limit') || 50);
        result = (state.identifications[cid] || []).slice(offset, offset + limit);
      } else if (parts[2] === 'reconcile' && method === 'POST') {
        await new Promise(resolve => setTimeout(resolve, 150));
        const payload = request.postDataJSON();
        if (state.identificationConflict) { item.identification_revision += 1; state.identificationConflict = false; }
        if (payload.expected_revision !== item.identification_revision) { status = 409; result = { detail: 'Stale identification revision' }; }
        else {
          state.identifications[cid] = [...(state.identifications[cid] || []), { id: id(6000 + state.writes.length), before_catalog_item_id: item.catalog_item_id, after_catalog_item_id: payload.catalog_item_id, before_release_id: item.release_id, after_release_id: payload.release_id, after_revision: item.identification_revision + 1, created_at: item.created_at }];
          item.catalog_item_id = payload.catalog_item_id; item.release_id = payload.release_id; item.identification_status = 'identified'; item.identification_revision += 1;
          status = state.uncertainIdentification ? 502 : 200;
          result = status === 200 ? item : { detail: 'Save could not be confirmed. Reload and inspect.' };
        }
      } else if (parts[2] === 'locations') {
        const offset = Number(url.searchParams.get('offset') || 0), limit = Number(url.searchParams.get('limit') || 50);
        result = (state.moves[cid] || []).slice(offset, offset + limit);
      } else if (parts[2] === 'location' && method === 'POST') {
        const payload = request.postDataJSON();
        if (state.conflict) { item.storage_revision += 1; state.conflict = false; }
        if (payload.expected_storage_revision !== item.storage_revision) { status = 409; result = { detail: 'Stale storage revision' }; }
        else {
          const before = item.storage_location_id; item.storage_location_id = payload.storage_location_id; item.storage_revision += 1;
          state.moves[cid] = [...(state.moves[cid] || []), { id: id(700 + state.writes.length), before_location_id: before, after_location_id: item.storage_location_id, after_revision: item.storage_revision, created_at: item.created_at }]; result = item;
        }
      }
    }
    if (result === undefined) { status = 404; result = { detail: 'Synthetic record not found' }; }
    try { await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(result) }); } catch { /* An intentionally aborted stale read may have closed. */ }
  });
  await page.goto(base); await page.getByRole('status').filter({ hasText: /copies on this page|copy on this page|Inventory unavailable/ }).waitFor();
  return { page, state };
}
async function open(page, title) {
  await page.getByRole('button', { name: `Open ${title}`, exact: true }).click();
  await page.getByRole('heading', { name: title, exact: true }).waitFor();
  await page.getByLabel('Photo file', { exact: true }).waitFor();
}

test('add-first workflow keeps one copy across photo, explicit nested storage, and search', async t => {
  const { page, state } = await fixture(t);
  assert.ok(await page.getByRole('heading', { name: 'Your first find starts here' }).isVisible());
  await page.getByRole('button', { name: 'Save copy', exact: true }).click();
  assert.match(await page.getByRole('alert').filter({ hasText: 'Add a title or notes' }).innerText(), /title or notes/);
  await page.getByLabel('Title', { exact: true }).fill('Synthetic blue-cover comic');
  await page.getByLabel('Notes', { exact: true }).fill('A provisional copy for the first trial.');
  await page.getByRole('button', { name: 'Save copy', exact: true }).dblclick();
  await page.getByLabel('Photo file', { exact: true }).waitFor();
  assert.equal(state.copies.length, 1); assert.equal(state.writes.filter(write => write.path === 'inventory').length, 1);
  const cid = state.copies[0].id;
  await page.getByLabel('Photo file', { exact: true }).setInputFiles({ name: 'synthetic.png', mimeType: 'image/png', buffer: png });
  await page.getByRole('button', { name: 'Upload photo', exact: true }).click();
  await page.getByAltText('Photo 1 of Synthetic blue-cover comic').waitFor();
  await page.getByText('Create a storage location', { exact: true }).click();
  await page.getByLabel('Location name', { exact: true }).fill('Study');
  await page.getByRole('button', { name: 'Create location', exact: true }).click();
  await page.getByRole('status').filter({ hasText: 'Location created.' }).waitFor();
  assert.equal(state.copies[0].storage_location_id, null, 'Creating a location must not move a copy');
  await page.getByLabel('Location name', { exact: true }).fill('Comic box A');
  await page.getByLabel('Inside another location', { exact: true }).selectOption(state.locations[0].id);
  await page.getByRole('button', { name: 'Create location', exact: true }).click();
  await page.waitForFunction(() => document.querySelector('#location-name').value === '');
  await page.getByRole('button', { name: 'Save location', exact: true }).click();
  await page.getByRole('status').filter({ hasText: 'Location saved.' }).waitFor();
  assert.equal(state.copies[0].id, cid); assert.equal(state.copies[0].storage_location_id, state.locations[1].id);
  await page.getByLabel('Find a copy', { exact: true }).fill('does not match');
  await page.getByRole('button', { name: 'Search', exact: true }).click();
  await page.getByRole('heading', { name: 'No matching copies' }).waitFor();
  await page.getByRole('button', { name: 'Clear search', exact: true }).click();
  await page.getByRole('button', { name: 'Open Synthetic blue-cover comic', exact: true }).waitFor();
  await page.getByLabel('Location', { exact: true }).selectOption('');
  await page.getByRole('button', { name: 'Save location', exact: true }).click();
  await page.getByRole('status').filter({ hasText: 'Copy is now unassigned.' }).waitFor();
  assert.equal(state.copies[0].storage_revision, 2); assert.equal(state.moves[cid].length, 2);
});

test('notes-only intake works, and uncertain creation requires inspection without automatic retry', async t => {
  const { page, state } = await fixture(t, { failCreate: 'uncertain' });
  await page.getByLabel('Notes', { exact: true }).fill('Unknown record in a plain sleeve');
  await page.getByRole('button', { name: 'Save copy', exact: true }).click();
  await page.getByRole('alert').filter({ hasText: 'Save could not be confirmed' }).waitFor();
  assert.equal(await page.getByLabel('Notes', { exact: true }).inputValue(), 'Unknown record in a plain sleeve');
  assert.ok(await page.getByRole('button', { name: 'Save copy', exact: true }).isDisabled());
  assert.equal(state.writes.length, 1);
  await page.getByRole('button', { name: 'Reload inventory', exact: true }).last().click();
  await page.getByRole('button', { name: 'Open Unknown record in a plain sleeve', exact: true }).waitFor();
  assert.equal(state.copies[0].title, null); assert.equal(state.writes.length, 1);
  assert.ok(await page.getByRole('button', { name: 'Save copy', exact: true }).isEnabled());
});

test('API outages and failed photos stay distinct from empty inventory and failed copy creation', async t => {
  const { page, state } = await fixture(t, { failList: true });
  assert.ok(await page.getByRole('alert').filter({ hasText: 'Synthetic API unavailable' }).isVisible());
  assert.equal(await page.getByRole('heading', { name: 'Your first find starts here' }).count(), 0);
  state.failList = false; state.failCreate = 'validation';
  await page.getByLabel('Title', { exact: true }).fill('Retained title');
  await page.getByRole('button', { name: 'Save copy', exact: true }).click();
  await page.getByRole('alert').filter({ hasText: 'Synthetic validation error' }).waitFor();
  assert.equal(await page.getByLabel('Title', { exact: true }).inputValue(), 'Retained title');
  state.failCreate = ''; state.failPhoto = true;
  await page.getByRole('button', { name: 'Save copy', exact: true }).click();
  await page.getByLabel('Photo file', { exact: true }).waitFor();
  const count = state.writes.length;
  await page.getByLabel('Photo file', { exact: true }).setInputFiles({ name: 'empty.png', mimeType: 'image/png', buffer: Buffer.alloc(0) });
  await page.getByRole('button', { name: 'Upload photo', exact: true }).click();
  await page.getByRole('alert').filter({ hasText: 'between 1 byte and 15 MiB' }).waitFor();
  assert.equal(state.writes.length, count);
  await page.getByLabel('Photo file', { exact: true }).setInputFiles({ name: 'bad.png', mimeType: 'image/png', buffer: png });
  await page.getByRole('button', { name: 'Upload photo', exact: true }).click();
  await page.getByRole('alert').filter({ hasText: 'Invalid image' }).waitFor();
  assert.equal(state.copies.length, 1); assert.equal(await page.getByLabel('Photo file', { exact: true }).evaluate(input => input.files[0].name), 'bad.png');
});

test('aborted detail/search reads cannot overwrite a newer selection, and inventory paginates', async t => {
  const copies = [copy(1, 'Old record'), copy(2, 'New record'), ...Array.from({ length: 20 }, (_, index) => copy(index + 3, `Other copy ${index}`))];
  const { page } = await fixture(t, { copies });
  await page.getByRole('button', { name: 'Open Old record', exact: true }).click();
  await open(page, 'New record');
  await page.waitForTimeout(500);
  assert.equal(await page.locator('#record-title').innerText(), 'New record');
  await page.getByLabel('Find a copy', { exact: true }).fill('Old'); await page.getByRole('button', { name: 'Search', exact: true }).click();
  await page.getByLabel('Find a copy', { exact: true }).fill('New'); await page.getByRole('button', { name: 'Search', exact: true }).click();
  await page.getByRole('button', { name: 'Open New record', exact: true }).waitFor();
  await page.waitForTimeout(500); assert.equal(await page.getByRole('button', { name: 'Open Old record', exact: true }).count(), 0);
  await page.getByRole('button', { name: 'Clear search', exact: true }).click();
  await page.getByRole('navigation', { name: 'Inventory pages', exact: true }).getByRole('button', { name: 'Next', exact: true }).click();
  await page.getByRole('navigation', { name: 'Inventory pages', exact: true }).getByText('Page 2', { exact: true }).waitFor();
  await page.getByRole('button', { name: 'Open Other copy 19', exact: true }).waitFor();
  assert.ok(await page.getByRole('navigation', { name: 'Inventory pages', exact: true }).getByRole('button', { name: 'Next', exact: true }).isDisabled());
});

test('storage conflicts require reload; location and history pages are not silently truncated', async t => {
  const places = Array.from({ length: 102 }, (_, index) => ({ id: id(index + 1000), name: `Place ${index}`, parent_id: null }));
  const item = copy(1, 'Stored find', { storage_location_id: places[101].id });
  const movements = Array.from({ length: 12 }, (_, index) => ({ id: id(index + 700), before_location_id: null, after_location_id: places[0].id, after_revision: index + 1, created_at: item.created_at }));
  const { page, state } = await fixture(t, { copies: [item], locations: places, moves: { [item.id]: movements }, conflict: true });
  await open(page, 'Stored find');
  assert.equal(await page.getByLabel('Location', { exact: true }).inputValue(), places[101].id);
  await page.getByRole('button', { name: 'Load more locations', exact: true }).click();
  await page.getByText('102 locations loaded.', { exact: true }).waitFor();
  await page.getByText('Movement history · 10+ recorded', { exact: true }).click();
  await page.getByRole('button', { name: 'Load more movements', exact: true }).click();
  await page.getByText('Movement history · 12 recorded', { exact: true }).waitFor();
  await page.getByLabel('Location', { exact: true }).selectOption(places[0].id);
  await page.getByRole('button', { name: 'Save location', exact: true }).click();
  await page.getByRole('alert').filter({ hasText: 'changed elsewhere' }).waitFor();
  assert.ok(await page.getByRole('button', { name: 'Save location', exact: true }).isDisabled()); assert.equal(state.writes.length, 1);
  await page.getByRole('button', { name: 'Reload copy', exact: true }).click();
  await page.getByLabel('Location', { exact: true }).waitFor();
  await page.getByLabel('Location', { exact: true }).selectOption(places[0].id);
  await page.getByRole('button', { name: 'Save location', exact: true }).click();
  await page.getByRole('status').filter({ hasText: 'Location saved.' }).waitFor();
  assert.equal(state.writes[1].body.expected_storage_revision, 1);
});


test('unreadable/network errors and long untrusted text stay safe and keyboard accessible', async t => {
  const { page, state } = await fixture(t, { failList: 'invalid' });
  await page.getByRole('alert').filter({ hasText: 'unreadable response' }).waitFor();
  state.failList = 'network';
  await page.getByRole('button', { name: 'Reload inventory', exact: true }).click();
  await page.getByRole('alert').filter({ hasText: 'Cannot reach the inventory' }).waitFor();
  state.failList = false;
  const title = '<img src=x onerror="alert(1)"> ' + 'Long'.repeat(110);
  state.copies = [copy(1, title)];
  await page.getByRole('button', { name: 'Reload inventory', exact: true }).click();
  await open(page, title);
  assert.equal(await page.locator('.inventory-list img').count(), 0);
  await page.setViewportSize({ width: 390, height: 844 });
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  await page.getByLabel('Title', { exact: true }).focus(); await page.keyboard.press('Tab');
  assert.ok(await page.getByLabel('Notes', { exact: true }).evaluate(input => input === document.activeElement));
  assert.notEqual(await page.getByLabel('Notes', { exact: true }).evaluate(input => getComputedStyle(input).outlineStyle), 'none');
});

test('real browser creates one synthetic copy, photo and nested location through the production stack', { skip: process.env.RELICRAT_REAL_UI_TEST !== '1' }, async t => {
  const context = await browser.newContext(); t.after(() => context.close());
  await signIn(context);
  const page = await context.newPage(); await page.goto(base);
  const initial = await page.evaluate(() => fetch('/api/v1/inventory').then(response => response.json()));
  assert.deepEqual(initial, [], 'Refusing to write to a nonempty live inventory');
  const title = 'Synthetic browser trial comic';
  await page.getByLabel('Title', { exact: true }).fill(title);
  await page.getByRole('button', { name: 'Save copy', exact: true }).click();
  await page.getByLabel('Photo file', { exact: true }).waitFor();
  await page.getByLabel('Photo file', { exact: true }).setInputFiles({ name: 'synthetic.png', mimeType: 'image/png', buffer: png });
  await page.getByRole('button', { name: 'Upload photo', exact: true }).click();
  await page.getByAltText(`Photo 1 of ${title}`).waitFor();
  await page.getByText('Create a storage location', { exact: true }).click();
  await page.getByLabel('Location name', { exact: true }).fill('Synthetic study');
  await page.getByRole('button', { name: 'Create location', exact: true }).click();
  await page.getByRole('status').filter({ hasText: 'Location created.' }).waitFor();
  const room = await page.getByLabel('Location', { exact: true }).inputValue();
  await page.getByLabel('Location name', { exact: true }).fill('Synthetic box');
  await page.getByLabel('Inside another location', { exact: true }).selectOption(room);
  await page.getByRole('button', { name: 'Create location', exact: true }).click();
  await page.waitForFunction(() => document.querySelector('#location-name').value === '');
  await page.getByRole('button', { name: 'Save location', exact: true }).click();
  await page.getByRole('status').filter({ hasText: 'Location saved.' }).waitFor();
  const saved = await page.evaluate(() => fetch('/api/v1/inventory').then(response => response.json())); assert.equal(saved.length, 1);
  const cid = saved[0].id;
  await page.locator('summary').filter({ hasText: /^Create a catalog entry$/ }).click();
  await page.getByLabel('New category name', { exact: true }).fill('Synthetic comics');
  await page.getByRole('button', { name: 'Create category', exact: true }).click();
  await page.getByRole('status').filter({ hasText: 'Category created.' }).waitFor();
  await page.getByLabel('Catalog name', { exact: true }).fill('Synthetic Canonical Hero #1');
  await page.getByRole('button', { name: 'Create catalog entry', exact: true }).click();
  await page.getByRole('status').filter({ hasText: 'Catalog entry created.' }).waitFor();
  await page.locator('summary').filter({ hasText: /^Create a release for/ }).click();
  await page.getByLabel('Release name', { exact: true }).fill('Synthetic first printing');
  await page.getByRole('button', { name: 'Create release', exact: true }).click();
  await page.getByRole('status').filter({ hasText: 'Release created.' }).waitFor();
  const unlinked = await page.evaluate(cid => fetch(`/api/v1/inventory/${cid}`).then(r => r.json()), cid);
  assert.equal(unlinked.catalog_item_id, null);
  await page.getByRole('button', { name: 'Save identification', exact: true }).click();
  await page.getByRole('status').filter({ hasText: 'Identification saved.' }).waitFor();
  await page.getByLabel('Edition or variant', { exact: true }).selectOption('');
  await page.getByRole('button', { name: 'Save identification', exact: true }).click();
  await page.waitForFunction(() => document.querySelector('.current-identification')?.textContent.includes('No release specified'));
  const reconciled = await page.evaluate(cid => fetch(`/api/v1/inventory/${cid}`).then(r => r.json()), cid);
  assert.equal(reconciled.id, cid); assert.equal(reconciled.identification_revision, 2); assert.equal(reconciled.release_id, null);
  assert.equal(reconciled.storage_location_id, saved[0].storage_location_id);
  const identifications = await page.evaluate(cid => fetch(`/api/v1/inventory/${cid}/reconciliations`).then(r => r.json()), cid);
  assert.equal(identifications.length, 2); assert.ok(identifications[1].before_release_id);
  await page.getByLabel('Find a copy', { exact: true }).fill('Canonical Hero'); await page.getByRole('button', { name: 'Search', exact: true }).click();
  await page.getByRole('button', { name: `Open ${title}`, exact: true }).waitFor();
  await page.reload(); await open(page, title);
  const photos = await page.evaluate(cid => fetch(`/api/v1/inventory/${cid}/photos`).then(response => response.json()), cid);
  const bytes = await page.evaluate(async ({ cid, photo }) => [...new Uint8Array(await (await fetch(`/api/v1/inventory/${cid}/photos/${photo}`)).arrayBuffer())], { cid, photo: photos[0].id });
  assert.deepEqual(Buffer.from(bytes), png);
  const moves = await page.evaluate(cid => fetch(`/api/v1/inventory/${cid}/locations`).then(response => response.json()), cid);
  assert.equal(moves.length, 1); assert.equal(moves[0].after_revision, 1);
});

test('catalog creation stays separate from ownership; identification and release removal retain the copy', async t => {
  const original = copy(1, 'Synthetic mystery', { storage_location_id: id(1000), storage_revision: 2 });
  const { page, state } = await fixture(t, { copies: [original], locations: [{ id: id(1000), name: 'Shelf', parent_id: null }] });
  await open(page, 'Synthetic mystery');
  await page.locator('summary').filter({ hasText: /^Create a catalog entry$/ }).click();
  await page.getByLabel('New category name', { exact: true }).fill('Synthetic comics');
  await page.getByRole('button', { name: 'Create category', exact: true }).click();
  await page.getByRole('status').filter({ hasText: 'Category created.' }).waitFor();
  await page.getByLabel('Catalog name', { exact: true }).fill('Synthetic Hero #1');
  await page.getByRole('button', { name: 'Create catalog entry', exact: true }).click();
  await page.getByRole('status').filter({ hasText: 'Catalog entry created.' }).waitFor();
  await page.locator('summary').filter({ hasText: /^Create a release for/ }).click();
  await page.getByLabel('Release name', { exact: true }).fill('First printing');
  await page.getByRole('button', { name: 'Create release', exact: true }).click();
  await page.getByRole('status').filter({ hasText: 'Release created.' }).waitFor();
  assert.equal(state.copies.length, 1); assert.equal(state.copies[0].catalog_item_id, null);
  await page.getByRole('button', { name: 'Save identification', exact: true }).click();
  assert.ok(await page.getByRole('button', { name: 'Save identification', exact: true }).isDisabled());
  await page.getByRole('status').filter({ hasText: 'Identification saved.' }).waitFor();
  assert.equal(state.writes.filter(write => write.path.endsWith('/reconcile')).length, 1);
  await page.getByLabel('Edition or variant', { exact: true }).selectOption('');
  await page.getByRole('button', { name: 'Save identification', exact: true }).click();
  await page.waitForFunction(() => document.querySelector('.current-identification')?.textContent.includes('No release specified'));
  assert.equal(state.copies[0].id, original.id); assert.equal(state.copies[0].storage_revision, 2);
  assert.equal(state.copies[0].identification_revision, 2); assert.equal(state.copies[0].release_id, null);
  assert.equal(state.identifications[original.id].length, 2);
  if (process.env.RELICRAT_SCREENSHOTS) {
    await page.locator('.identification details').evaluateAll(nodes => nodes.forEach(node => { node.open = false; }));
    await page.getByLabel('Find a catalog entry', { exact: true }).fill('Hero');
    await page.getByRole('button', { name: 'Search catalog', exact: true }).click();
    await page.getByRole('radio', { name: /Synthetic Hero/ }).waitFor();
    await page.getByText('Identification history', { exact: true }).click();
    const output = resolve(process.env.RELICRAT_SCREENSHOTS); await mkdir(output, { recursive: true });
    await page.evaluate(async () => { document.activeElement?.blur(); window.scrollTo(0, 0); await new Promise(requestAnimationFrame); await new Promise(requestAnimationFrame); });
    await page.screenshot({ path: `${output}/desktop.png`, fullPage: true, animations: 'disabled' });
    await page.setViewportSize({ width: 390, height: 844 });
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.evaluate(async () => { document.activeElement?.blur(); window.scrollTo(0, 0); await new Promise(requestAnimationFrame); await new Promise(requestAnimationFrame); });
    await page.screenshot({ path: `${output}/mobile.png`, fullPage: true, animations: 'disabled' });
  }
});

test('catalog paging, selected release beyond page one, stale revisions and uncertain writes require review', async t => {
  const items = Array.from({ length: 22 }, (_, index) => ({ id: id(4000 + index), category_id: id(3000), canonical_name: `Catalog ${index}` }));
  const releases = Array.from({ length: 22 }, (_, index) => ({ id: id(5000 + index), catalog_item_id: items[21].id, name: `Edition ${index}` }));
  const original = copy(1, 'Identified trial', { catalog_item_id: items[21].id, release_id: releases[21].id, identification_status: 'identified' });
  const { page, state } = await fixture(t, { copies: [original], items, releases, identificationConflict: true });
  await open(page, 'Identified trial');
  await page.getByLabel('Edition or variant', { exact: true }).waitFor();
  assert.equal(await page.getByLabel('Edition or variant', { exact: true }).inputValue(), releases[21].id);
  await page.getByRole('navigation', { name: 'Catalog pages', exact: true }).getByRole('button', { name: 'Next', exact: true }).click();
  await page.getByRole('radio', { name: /Catalog 21/ }).waitFor();
  assert.ok(await page.getByRole('radio', { name: /Catalog 21/ }).isChecked());
  await page.getByRole('navigation', { name: 'Release pages', exact: true }).getByRole('button', { name: 'Next', exact: true }).click();
  await page.getByLabel('Edition or variant', { exact: true }).selectOption('');
  await page.getByRole('button', { name: 'Save identification', exact: true }).click();
  await page.getByRole('alert').filter({ hasText: 'This copy changed elsewhere' }).waitFor();
  assert.ok(await page.getByRole('button', { name: 'Upload photo', exact: true }).isDisabled());
  await page.getByRole('button', { name: 'Reload copy', exact: true }).click();
  await page.getByLabel('Edition or variant', { exact: true }).waitFor();
  await page.getByLabel('Edition or variant', { exact: true }).selectOption('');
  state.uncertainIdentification = true;
  await page.getByRole('button', { name: 'Save identification', exact: true }).click();
  await page.getByRole('alert').filter({ hasText: 'Save could not be confirmed' }).first().waitFor();
  assert.ok(await page.getByRole('button', { name: 'Save identification', exact: true }).isDisabled());
  assert.equal(state.writes.filter(write => write.path.endsWith('/reconcile')).length, 2);
  await page.getByRole('button', { name: 'Reload copy', exact: true }).click();
  await page.getByText('No release specified', { exact: false }).first().waitFor();
  await page.getByLabel('Edition or variant', { exact: true }).waitFor();
  assert.ok(await page.getByRole('button', { name: 'Save identification', exact: true }).isDisabled());
});

test('obsolete catalog searches are cancelled and changing catalog clears the selected release', async t => {
  const items = [{ id: id(4000), category_id: id(3000), canonical_name: 'Old catalog' }, { id: id(4001), category_id: id(3000), canonical_name: 'New catalog <img src=x>' }];
  const releases = [{ id: id(5000), catalog_item_id: items[0].id, name: 'Old edition' }];
  const { page } = await fixture(t, { copies: [copy(1, 'Race trial', { catalog_item_id: items[0].id, release_id: releases[0].id })], items, releases });
  await open(page, 'Race trial');
  await page.getByLabel('Find a catalog entry', { exact: true }).fill('Old catalog');
  await page.getByRole('button', { name: 'Search catalog', exact: true }).click();
  await page.getByLabel('Find a catalog entry', { exact: true }).fill('New catalog');
  await page.getByRole('button', { name: 'Search catalog', exact: true }).click();
  await page.getByRole('radio', { name: /New catalog/ }).check();
  await page.waitForTimeout(500);
  assert.equal(await page.getByRole('radio', { name: /Old catalog/ }).count(), 0);
  assert.equal(await page.getByLabel('Edition or variant', { exact: true }).inputValue(), '');
  assert.equal(await page.locator('.catalog-results img').count(), 0);
});

test('private owner login blocks guests, protects photos, and logout invalidates captured cookies', async t => {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1050 } });
  t.after(() => context.close());
  const page = await context.newPage(); await page.goto(base);
  await page.waitForURL('**/login');
  assert.equal(await page.getByRole('heading', { name: 'Add a find', exact: true }).count(), 0);
  for (const path of ['inventory', 'catalog/items', 'storage-locations']) assert.equal((await context.request.get(`${base}/api/v1/${path}`)).status(), 401);
  await page.getByLabel('Owner password', { exact: true }).fill('incorrect-synthetic-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.getByRole('alert').filter({ hasText: 'Password not recognized' }).waitFor();
  if (process.env.RELICRAT_SCREENSHOTS) {
    const output = resolve(process.env.RELICRAT_SCREENSHOTS); await mkdir(output, { recursive: true });
    await page.screenshot({ path: `${output}/login-desktop.png`, fullPage: true, animations: 'disabled' });
    await page.setViewportSize({ width: 390, height: 844 });
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({ path: `${output}/login-mobile.png`, fullPage: true, animations: 'disabled' });
  }
  await page.getByLabel('Owner password', { exact: true }).fill(ownerPassword);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.getByRole('heading', { name: 'Add a find', exact: true }).waitFor();
  assert.equal(new URL(page.url()).pathname, '/');
  const cookies = await context.cookies();
  const session = cookies.find(cookie => cookie.name === 'relicrat_loopback_session');
  assert.ok(session?.httpOnly); assert.equal(session.sameSite, 'Strict');
  assert.ok(!(await page.evaluate(() => document.cookie)).includes(session.value));
  const signed = await context.request.get(base);
  assert.match(signed.headers()['cache-control'], /no-store/);
  const blocked = await context.request.post(`${base}/api/v1/inventory`, { data: { title: 'Must not exist' }, headers: { Origin: 'https://evil.test' } });
  assert.equal(blocked.status(), 403);
  const copies = await (await context.request.get(`${base}/api/v1/inventory`)).json();
  if (copies.length) {
    const cid = copies[0].id;
    const photos = await (await context.request.get(`${base}/api/v1/inventory/${cid}/photos`)).json();
    if (photos.length) {
      const guest = await browser.newContext(); t.after(() => guest.close());
      const path = `${base}/api/v1/inventory/${cid}/photos/${photos[0].id}`;
      assert.equal((await guest.request.get(path)).status(), 401);
      assert.equal((await context.request.get(path)).status(), 200);
    }
  }
  await page.reload(); await page.getByRole('button', { name: 'Sign out', exact: true }).waitFor();
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await page.waitForURL('**/login');
  const replay = await browser.newContext(); t.after(() => replay.close()); await replay.addCookies(cookies);
  assert.equal((await replay.request.get(`${base}/api/v1/inventory`)).status(), 401);
  await page.goto(base); await page.waitForURL('**/login');
  assert.equal(await page.getByRole('heading', { name: 'Add a find', exact: true }).count(), 0);
});
