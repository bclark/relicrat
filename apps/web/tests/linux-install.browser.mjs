import assert from 'node:assert/strict';
import {after, before, test} from 'node:test';
import {chromium, devices} from 'playwright';
import {chooseCollection, openDisclosure, showIntake} from './journey-test-helpers.mjs';

assert.equal(process.env.RELICRAT_TEST_LINUX_INSTALL, '1', 'Use only the disposable install runner');
const origin = 'http://127.0.0.1:3000';
const password = 'synthetic-only-linux-install-password';
const photo = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGPgl1QGAACGAEwFRbXWAAAAAElFTkSuQmCC', 'base64');
let browser;
before(async () => { browser = await chromium.launch(); });
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
    await page.goto(origin);
    await page.waitForURL('**/login');
    await page.getByLabel('Owner password').fill(password);
    await page.getByRole('button', {name: 'Sign in', exact: true}).click();
    await page.waitForURL(origin + '/');

    const title = `Synthetic Linux copy for ${layout}`;
    const box = `Synthetic Linux box for ${layout}`;
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
      await page.getByRole('button', {name: 'Create location', exact: true}).click();
      await page.getByRole('status').filter({hasText: `${box} created.`}).waitFor();
      await page.getByLabel('Location', {exact: true}).selectOption({label: box});
      await page.getByRole('status').filter({hasText: `Added to ${box}.`}).waitFor();
      await page.getByRole('button', {name: 'Back to collection', exact: true}).click();
    }
    await page.getByLabel('Find a copy', {exact: true}).fill(title);
    await page.getByRole('button', {name: 'Search', exact: true}).click();
    await page.getByRole('button', {name: `Open ${title}`, exact: true}).click();
    assert.equal(await page.getByLabel('Location', {exact: true}).locator('option:checked').textContent(), box);
    const image = page.getByAltText(`Photo 1 of ${title}`, {exact: true});
    await image.waitFor();
    const source = await image.getAttribute('src');
    assert.ok(source.startsWith('/api/v1/inventory/'));
    const saved = await context.request.get(new URL(source, origin).href);
    assert.equal(saved.status(), 200);
    assert.deepEqual(await saved.body(), photo);
  });
}
