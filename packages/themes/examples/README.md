# Blueprint

Blueprint pairs navy surfaces and pale blue actions with monospaced headings
inspired by technical drawing labels.

1. Open [blueprint.json](blueprint.json) and copy the JSON.
2. In RelicRat, open **Appearance → Import or export a theme**. Paste the JSON
   and choose **Import and preview**.
3. Choose **Apply theme** to save the preview. To switch back, use
   **Restore default draft → Preview theme → Apply theme**.
4. To share your version, use **Export current draft**. Share the downloaded
   JSON with its name, a screenshot, and the RelicRat version you tested.

Blueprint uses theme schema version 1. System fonts may look different across
devices. The [authoring guide](../AUTHORING-PROMPT.md) describes the supported
fields and contrast requirements.

See Blueprint applied on a synthetic install in the [desktop screenshot](blueprint-desktop.png)
and [phone screenshot](blueprint-phone.png).

To repeat the transfer check, start two disposable Linux Compose installs with
separate databases and the synthetic password used by the Linux install test.
Point the loopback relay on port 3000 to the source, then to the recipient:

```sh
RELICRAT_TEST_LINUX_INSTALL=1 node apps/web/tests/theme-transfer.browser.mjs export /tmp/blueprint-export.json
RELICRAT_TEST_LINUX_INSTALL=1 node apps/web/tests/theme-transfer.browser.mjs import /tmp/blueprint-export.json
```
