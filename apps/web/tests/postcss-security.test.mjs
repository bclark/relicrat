import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';

// Resolve through Next itself so a separately patched package cannot hide its copy.
const require = createRequire(import.meta.url);
const nextRequire = createRequire(require.resolve('next/package.json'));
const postcss = nextRequire('postcss');

test('Next PostCSS refuses external source maps while retaining local build maps', () => {
  const root = mkdtempSync(join(tmpdir(), 'relicrat-css-security-'));
  try {
    const styles = join(root, 'styles'); mkdirSync(styles);
    const map = JSON.stringify({ version: 3, sources: ['synthetic.css'], sourcesContent: ['synthetic-private-map'], names: [], mappings: 'AAAA' });
    writeFileSync(join(root, 'outside.map'), map);
    writeFileSync(join(styles, 'local.map'), map);
    symlinkSync(join(root, 'outside.map'), join(styles, 'escape.map'));
    const from = join(styles, 'main.css');
    const parse = (reference, options = {}) => postcss.parse(`a { color: red }\n/*# sourceMappingURL=${reference} */`, options).source.input.map;
    assert.equal(parse(join(root, 'outside.map'))?.text, undefined, 'Missing from must not permit absolute file reads');
    assert.equal(parse('../outside.map', { from })?.text, undefined, 'Traversal outside the CSS directory must not load');
    assert.equal(parse('escape.map', { from })?.text, undefined, 'Symlinks must not escape the CSS directory');
    assert.equal(parse('local.map', { from }).text, map, 'Ordinary local build source maps still work');
  } finally { rmSync(root, { recursive: true, force: true }); }
});
