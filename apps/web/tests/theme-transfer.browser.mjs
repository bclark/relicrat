import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {chromium, devices} from 'playwright';

assert.equal(process.env.RELICRAT_TEST_LINUX_INSTALL, '1');
const [phase, transferFile] = process.argv.slice(2);
assert.ok(['export', 'import'].includes(phase) && transferFile);
const origin = 'http://127.0.0.1:3000';
const source = phase === 'export';
const example = await readFile(new URL('../../../packages/themes/examples/blueprint.json', import.meta.url), 'utf8');
const factory = await readFile(new URL('../../../packages/themes/relicrat-default.json', import.meta.url), 'utf8');
const browser = await chromium.launch();

try {
  const context = await browser.newContext({
    ...(source ? {viewport: {width: 1440, height: 1000}} : devices['Pixel 7']),
    serviceWorkers: 'block',
  });
  await context.route('**/*', route =>
    new URL(route.request().url()).origin === origin ? route.continue() : route.abort('internetdisconnected'));
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  const button = name => page.getByRole('button', {name, exact: true});
  const saved = async () => {
    const response = await context.request.get(origin + '/api/v1/appearance');
    assert.equal(response.status(), 200);
    return response.json();
  };
  const waitForColor = hex => page.waitForFunction(color =>
    document.querySelector('.themed-app')?.style.getPropertyValue('--page') === color, hex);
  const openAppearance = async () => {
    if (await button('Menu').isVisible()) await button('Menu').click();
    await button('Appearance').press('Enter');
    await page.getByLabel('Theme name', {exact: true}).waitFor();
  };
  const apply = async () => {
    await button('Apply theme').click();
    await page.getByRole('status').filter({hasText: 'Appearance saved'}).waitFor();
  };

  await page.goto(origin);
  await page.getByLabel('Owner password').fill('synthetic-only-linux-install-password');
  await button('Sign in').click();
  await page.waitForURL(origin + '/');
  assert.equal((await saved()).revision, 0);
  assert.deepEqual((await saved()).theme, JSON.parse(factory));
  await openAppearance();
  await page.getByText('Import or export a theme', {exact: true}).click();
  const input = source ? example : await readFile(transferFile, 'utf8');
  assert.deepEqual(JSON.parse(input), JSON.parse(example));
  await page.getByLabel('Theme JSON (up to 8 KiB)', {exact: true}).fill(input);
  await button('Import and preview').click();
  await page.getByRole('status').filter({hasText: 'Preview ready'}).waitFor();
  assert.equal((await saved()).revision, 0);
  await waitForColor(JSON.parse(factory).colors.page);
  await apply();
  await page.reload();
  await waitForColor(JSON.parse(example).colors.page);
  assert.deepEqual((await saved()).theme, JSON.parse(example));
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
  await openAppearance();
  if (process.env.RELICRAT_THEME_SCREENSHOTS) {
    await page.screenshot({path: `${process.env.RELICRAT_THEME_SCREENSHOTS}/blueprint-${source ? 'desktop' : 'phone'}.png`, fullPage: true});
  }
  if (source) {
    await page.getByText('Import or export a theme', {exact: true}).click();
    const downloaded = page.waitForEvent('download');
    await button('Export current draft').click();
    await (await downloaded).saveAs(transferFile);
    assert.deepEqual(JSON.parse(await readFile(transferFile, 'utf8')), JSON.parse(example));
  } else {
    await button('Restore default draft').click();
    await button('Preview theme').click();
    await page.getByRole('status').filter({hasText: 'Preview ready'}).waitFor();
    await apply();
    await page.reload();
    await waitForColor(JSON.parse(factory).colors.page);
    assert.deepEqual((await saved()).theme, JSON.parse(factory));
  }
  console.log(`Blueprint ${phase} verified on a clean install`);
} finally {
  await browser.close();
}
