import assert from 'node:assert/strict';
import {after, before, test} from 'node:test';
import {chromium, devices} from 'playwright';
import {chooseCollection, openDisclosure, showIntake, showTools} from './journey-test-helpers.mjs';

assert.equal(process.env.RELICRAT_TEST_LINUX_INSTALL, '1', 'Use only the disposable install runner');
const origin = process.env.RELICRAT_TEST_WEB_URL ?? 'http://127.0.0.1:3000';
assert.match(origin, /^http:\/\/127\.0\.0\.1:\d+$/);
const password = 'synthetic-only-linux-install-password';
const photo = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGPgl1QGAACGAEwFRbXWAAAAAElFTkSuQmCC', 'base64');
let browser;
before(async () => { browser = await chromium.launch({executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE}); });
after(async () => { await browser?.close(); });

for (const [layout, profile] of [
  ['desktop', {viewport: {width: 1440, height: 1000}}],
  ['phone', devices['Pixel 7']],
]) {
  test(`private Linux install on ${layout}`, async t => {
    const context = await browser.newContext({...profile, serviceWorkers: 'block'});
    t.after(() => context.close());
    await context.route('**/*', route =>
      new URL(route.request().url()).origin === origin ? route.continue() : route.abort('internetdisconnected'));
    const page = await context.newPage();
    await page.goto(origin, {waitUntil: 'networkidle'});
    await page.waitForURL('**/login');
    await page.getByLabel('Owner password').fill(password);
    await page.getByRole('button', {name: 'Sign in', exact: true}).click();
    await page.waitForURL(origin + '/');

    const title = `Synthetic Linux copy for ${layout}`;
    const box = `Synthetic Linux box for ${layout}`;
    let boxId;
    await chooseCollection(page, 'other');
    if (process.env.RELICRAT_TEST_AFTER_RESTART !== '1') {
      await showIntake(page);
      await page.getByRole('form', {name: 'Add an item', exact: true}).getByLabel('Title', {exact: true}).fill(title);
      await page.getByRole('button', {name: 'Save item', exact: true}).click();
      await page.getByRole('button', {name: 'View item', exact: true}).click();
      await page.getByLabel('Photo file', {exact: true}).setInputFiles({
        name: 'synthetic.png', mimeType: 'image/png', buffer: photo,
      });
      await page.getByRole('button', {name: 'Upload photo', exact: true}).click();
      await page.getByText('Photo saved. The copy and its existing history are unchanged.', {exact: true}).waitFor();
      await openDisclosure(page, 'Create a storage location');
      await page.getByLabel('Location name', {exact: true}).fill(box);
      const created = page.waitForResponse(response =>
        response.url() === origin + '/api/v1/storage-locations' && response.request().method() === 'POST');
      await page.getByRole('button', {name: 'Create location', exact: true}).click();
      const location = await created;
      assert.equal(location.status(), 201);
      ({id: boxId} = await location.json());
      await page.getByRole('status').filter({hasText: `${box} created.`}).waitFor();
      await page.getByLabel('Location', {exact: true}).selectOption(boxId);
      await page.getByRole('status').filter({hasText: `Added to ${box}.`}).waitFor();
      await page.getByRole('button', {name: 'Back to collection', exact: true}).click();
    }
    await page.getByLabel('Find a copy', {exact: true}).fill(title);
    await page.getByRole('button', {name: 'Search', exact: true}).click();
    await page.getByRole('button', {name: `Open ${title}`, exact: true}).click();
    await page.getByText(`Current location: ${box}`, {exact: true}).waitFor();
    const image = page.getByAltText(`Photo 1 of ${title}`, {exact: true});
    await image.waitFor();
    const source = await image.getAttribute('src');
    assert.ok(source.startsWith('/api/v1/inventory/'));
    const saved = await context.request.get(new URL(source, origin).href);
    assert.equal(saved.status(), 200);
    assert.deepEqual(await saved.body(), photo);

    const importedTitle = `Synthetic CSV game for ${layout}`;
    await page.getByRole('button', {name: 'Back to collection', exact: true}).click();
    if (process.env.RELICRAT_TEST_AFTER_RESTART !== '1') {
      if (layout === 'phone') {
        await page.getByRole('button', {name: 'Back to collections', exact: true}).click();
        const shortcut = page.getByRole('button', {name: 'Start a CSV import', exact: true});
        await shortcut.click();
        await page.locator('h2:focus').filter({hasText: 'Import a collection'}).waitFor();
        await page.locator('.collection-tools > summary').click();
        await shortcut.click();
      } else {
        await showTools(page);
        await page.getByRole('button', {name: 'Import CSV', exact: true}).click();
      }
      await page.locator('h2:focus').filter({hasText: 'Import a collection'}).waitFor();
      await page.getByLabel('Export format', {exact: true}).selectOption('game_recipe');
      await page.getByLabel('CSV file', {exact: true}).setInputFiles({
        name: 'synthetic-games.csv', mimeType: 'text/csv',
        buffer: Buffer.from(`Platform,Title\nSynthetic Console,${importedTitle}\n`),
      });
      await page.getByRole('button', {name: 'Preview import', exact: true}).click();
      await page.getByText('1 valid row → 1 physical copy in Video games.', {exact: true}).waitFor();
      await page.getByRole('checkbox', {name: /I reviewed the preview/}).check();
      await page.getByRole('button', {name: 'Import 1 copy', exact: true}).click();
      await page.getByRole('status').filter({hasText: 'Imported 1 physical copy into Video games.'}).waitFor();
      await page.getByRole('button', {name: 'View imported copies', exact: true}).click();
      await page.getByRole('button', {name: `Open ${importedTitle}`, exact: true}).click();
      await page.getByLabel('Location', {exact: true}).selectOption(boxId);
      await page.getByRole('status').filter({hasText: `Added to ${box}.`}).waitFor();
      await page.getByRole('button', {name: 'Back to collection', exact: true}).click();
    }
    await chooseCollection(page, 'game');
    await page.getByLabel('Find a copy', {exact: true}).fill(importedTitle);
    await page.getByRole('button', {name: 'Search', exact: true}).click();
    await page.getByRole('button', {name: `Open ${importedTitle}`, exact: true}).click();
    await page.getByText(`Current location: ${box}`, {exact: true}).waitFor();
  });
}

test('video game release and physical contents survive reload', async t => {
  const context = await browser.newContext({...devices['Pixel 7'], serviceWorkers: 'block'});
  t.after(() => context.close());
  await context.route('**/*', route =>
    new URL(route.request().url()).origin === origin ? route.continue() : route.abort('internetdisconnected'));
  const page = await context.newPage();
  await page.route('**/api/v1/collection-settings/types', async route => {
    const response = await route.fetch();
    const types = await response.json();
    types.game.title_lookup = {provider: 'igdb', max_results: 5};
    await route.fulfill({response, json: types});
  });
  await page.goto(origin);
  await page.waitForURL('**/login');
  await page.getByLabel('Owner password').fill(password);
  await page.getByRole('button', {name: 'Sign in', exact: true}).click();
  await page.waitForURL(origin + '/');
  const title = 'Synthetic Orbital Racer';
  const release = 'Example 64 · Japan · Launch';
  await chooseCollection(page, 'game');
  if (process.env.RELICRAT_TEST_AFTER_RESTART !== '1') {
    await showIntake(page);
    await page.getByRole('form', {name: 'Add an item', exact: true}).getByLabel('Game title', {exact: true}).fill(title);
    await page.getByRole('button', {name: 'Save item', exact: true}).click();
    await page.getByRole('button', {name: 'View item', exact: true}).click();
    await openDisclosure(page, 'Game release and catalog match');
    await openDisclosure(page, 'Can’t find it? Add a collectible');
    await page.getByLabel('Catalog game title').fill(title);
    await page.getByRole('button', {name: 'Add game title', exact: true}).click();
    await openDisclosure(page, 'Add a game release');
    const form = page.getByRole('form', {name: 'Add game release'});
    await form.getByLabel('Platform', {exact: true}).fill('Example 64');
    await form.getByLabel('Region', {exact: true}).fill('Japan');
    await form.getByLabel('Edition', {exact: true}).fill('Launch');
    await form.getByRole('button', {name: 'Add game release', exact: true}).click();
    await page.getByRole('button', {name: 'Save catalog match', exact: true}).click();
    await page.getByText('Release: ' + release, {exact: true}).waitFor();
    await page.getByRole('button', {name: 'Edit details', exact: true}).click();
    await page.getByRole('form', {name: 'Edit copy details'}).getByLabel('Manual', {exact: true}).selectOption('missing');
    await page.getByRole('button', {name: 'Save changes', exact: true}).click();
    await page.getByText('Changes saved.', {exact: true}).waitFor();
    await page.getByRole('button', {name: 'Back to collection', exact: true}).click();
  }
  await showIntake(page);
  const titleInput = page.getByRole('form', {name: 'Add an item', exact: true}).getByLabel('Game title', {exact: true});
  await titleInput.fill('Synthetic Orbi');
  await page.waitForFunction(value =>
    Array.from(document.querySelectorAll('#find-title-suggestions option')).some(option => option.value === value), title);
  await titleInput.clear();
  const barcode = '012345678905';
  const suggestion = 'Synthetic Barcode Game';
  let barcodeMiss = false;
  await page.route('**/api/v1/barcode-lookups/game', route => {
    assert.equal(route.request().method(), 'POST');
    assert.equal(route.request().postDataJSON().value, barcode);
    return route.fulfill({json: {provider_label: 'UPCitemdb', candidates: barcodeMiss ? [] : [{
      id: barcode, title: suggestion, description: 'Retail product match',
      fields: {title: suggestion}, cover_url: null,
    }]}});
  });
  await page.getByRole('button', {name: 'Type a barcode instead', exact: true}).click();
  await page.getByLabel('Barcode', {exact: true}).fill(barcode);
  await page.getByRole('button', {name: 'Use barcode', exact: true}).click();
  const match = page.getByRole('button', {name: new RegExp(suggestion)});
  await match.waitFor();
  assert.equal(await titleInput.inputValue(), '');
  await match.click();
  assert.equal(await titleInput.inputValue(), suggestion);
  await titleInput.clear();
  barcodeMiss = true;
  await page.getByRole('button', {name: 'Find game details', exact: true}).click();
  await page.getByRole('status').filter({hasText: 'No match for this barcode'}).waitFor();
  await page.getByRole('button', {name: 'Continue with title search', exact: true}).click();
  assert.equal(await titleInput.evaluate(input => input === document.activeElement), true);
  const query = 'Synthetic Adventure';
  const canonical = 'Synthetic Adventure II';
  await page.route('**/api/v1/title-lookups/game', route => {
    assert.equal(route.request().method(), 'POST');
    assert.deepEqual(route.request().postDataJSON(), {title: query});
    return route.fulfill({json: {provider_label: 'IGDB', candidates: [{
      id: '42', title: canonical, description: 'Catalog title',
      fields: {title: canonical}, cover_url: null,
    }]}});
  });
  await titleInput.fill(query);
  await page.getByRole('button', {name: 'Search online by title', exact: true}).click();
  const titleMatch = page.getByRole('button', {name: new RegExp(canonical)});
  await titleMatch.waitFor();
  assert.equal(await titleInput.inputValue(), query);
  await titleMatch.click();
  assert.equal(await titleInput.inputValue(), canonical);
  await page.getByText('Barcode '+barcode+' · UPC-A', {exact: true}).waitFor();
  await page.getByRole('button', {name: 'Remove barcode from draft', exact: true}).click();
  await titleInput.clear();
  await page.getByRole('button', {name: 'Back to Video games', exact: true}).click();
  await page.getByRole('button', {name: 'Open ' + title, exact: true}).click();
  await page.getByText('Release: ' + release, {exact: true}).waitFor();
  await page.getByRole('definition').filter({hasText: 'Missing'}).waitFor();
});

test('game barcode offers existing copy or a separate copy on phone', {
  skip: process.env.RELICRAT_TEST_AFTER_RESTART === '1',
}, async t => {
  const context = await browser.newContext({...devices['Pixel 7'], serviceWorkers: 'block'});
  t.after(() => context.close());
  const page = await context.newPage();
  await page.goto(origin);
  await page.waitForURL('**/login');
  await page.getByLabel('Owner password').fill(password);
  await page.getByRole('button', {name: 'Sign in', exact: true}).click();
  await page.waitForURL(origin + '/');

  const barcode = '012345678912';
  const title = 'Synthetic Stored Game';
  const box = 'Synthetic Game Box';
  async function post(path, data, status) {
    const response = await context.request.post(origin + '/api/v1/' + path, {
      data, headers: {origin},
    });
    assert.equal(response.status(), status);
    return response.json();
  }
  const stored = await post('inventory', {title, collection_type: 'game',
    barcode: {value: barcode, format: 'UPC_A'}}, 201);
  const location = await post('storage-locations', {name: box, kind: 'box'}, 201);
  await post('inventory/'+stored.id+'/location', {
    storage_location_id: location.id, expected_storage_revision: stored.storage_revision,
  }, 200);
  let onlineLookups = 0;
  await page.route('**/api/v1/barcode-lookups/game', route => {
    onlineLookups++;
    return route.fulfill({json: {provider_label: 'UPCitemdb', candidates: []}});
  });

  await chooseCollection(page, 'game');
  await showIntake(page);
  await page.getByRole('button', {name: 'Type a barcode instead', exact: true}).click();
  await page.getByLabel('Barcode', {exact: true}).fill(barcode);
  await page.getByRole('button', {name: 'Use barcode', exact: true}).click();
  const matches = page.getByRole('region', {name: 'Already in your collection'});
  await matches.getByText(title, {exact: true}).waitFor();
  await matches.getByText(box, {exact: true}).waitFor();
  await matches.getByRole('button', {name: 'View copy', exact: true}).click();
  await page.getByRole('heading', {name: title, exact: true}).waitFor();
  await page.getByText('Current location: '+box, {exact: true}).waitFor();
  assert.equal(onlineLookups, 0);

  await showIntake(page);
  await matches.getByRole('button', {name: 'Add another copy', exact: true}).click();
  await page.getByText('Barcode '+barcode+' · UPC-A', {exact: true}).waitFor();
  const titleInput = page.getByRole('form', {name: 'Add an item', exact: true}).getByLabel('Game title', {exact: true});
  await titleInput.fill(title);
  const saved = page.waitForResponse(response =>
    response.url() === origin+'/api/v1/inventory' && response.request().method() === 'POST');
  await page.getByRole('button', {name: 'Save item', exact: true}).click();
  const response = await saved;
  assert.equal(response.status(), 201);
  const additional = await response.json();
  assert.notEqual(additional.id, stored.id);
  assert.equal(additional.barcode.value, barcode);
  assert.equal(additional.storage_location_id, null);
  const original = await context.request.get(origin+'/api/v1/inventory/'+stored.id);
  assert.equal(original.status(), 200);
  assert.equal((await original.json()).storage_location_id, location.id);
});
