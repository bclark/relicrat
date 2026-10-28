# PostCSS dependency regression

Next 15.5.28 requests PostCSS 8.4.31 exactly. The scoped npm override selects
8.5.32 for Next's dependency, retaining Next 15 while removing the currently
reported PostCSS advisories. Keep package.json and the lockfile together and use
`npm ci`. Remove the override only when the supported framework resolves a fixed
PostCSS itself, with these checks still passing.

`postcss-security.test.mjs` resolves PostCSS through Next rather than importing
an unrelated patched copy. Its disposable source-map fixture checks absolute
file access without `from`, parent traversal, and symlink escape; a local source
map remains supported. The test demonstrably fails on the previous image's
8.4.31 dependency and passes on 8.5.32. It never reads real private files.

See upstream advisories:
- https://github.com/postcss/postcss/security/advisories/GHSA-6g55-p6wh-862q
- https://github.com/postcss/postcss/security/advisories/GHSA-fxqj-rqcc-2cmp

Run `npm test`, `npm audit`, `npm run lint`, production build and the disposable
web/browser integration before changing this override. A clean audit is a dated
check against current advisories, not a guarantee against undiscovered issues.
