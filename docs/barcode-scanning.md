# Barcode intake

Scan a barcode, explicitly choose **Use barcode**, then save the find. Albums
also offer **Find album details**: review a configured provider’s suggestions,
choose fields, then **Use these details** to fill the draft before saving. See
[lookup configuration and adapter contract](barcode-lookup.md). Scanning
alone never creates inventory, fills a title, matches a catalog entry or calls a
provider. Camera frames stay on-device; only an explicitly saved barcode
observation goes to your private inventory API.

## Try it

After sign-in, choose **Scan barcode** beside Add a find. Allow camera access,
hold the code steady, and review its digits, format and optional supplement.
The camera stops after a reading. Choose **Use barcode** to attach it to the
current draft, enter a meaningful title, and choose **Save copy**. You can scan
again or close the scanner to discard an unused reading. Replacing an attached
barcode has a separate **Replace draft barcode** action. Failed saves retain
the draft; uncertain saves require reload/review before another save.

Saved copies expose **Barcode (optional)** under Edit this copy. You can scan a
replacement or remove the observation, then explicitly **Save details**.
Corrections and removals remain in Copy edit history. Closing that disclosure
stops an active camera. Search can find copies by the main barcode digits; shared
codes can return several physical copies and never merge them.

Camera access requires a secure browser context. For a phone, use the private
HTTPS address configured by your operator with Tailscale connected. See the
[private phone access guide](private-phone-access.md). Your existing owner password
protects access. Private HTTPS was verified separately; autofocus, lighting and
physical-device permission behavior still need a hands-on phone trial.

## What is read

Supported decoder formats are UPC-A, UPC-E, EAN-8 and EAN-13. Digits are kept as
strings, including leading zeroes. UPC-A may be reported as UPC-A rather than the
equivalent EAN-13 with an extra initial zero. This is a decoder interpretation,
not an authoritative catalog identifier. No ISBN or edition conversion is made.
A detected two- or five-digit supplement is displayed separately. Missing
supplements mean **Not detected**, not a default issue/variant/printing. Comics
require review and a separately selected catalog source before identification.

The camera requests video only, preferring the rear camera. It stops on a read,
explicit stop/close, page exit, backgrounding, disconnect, startup/decoder error,
or a one-minute limit. Cancelled runs stop a late camera stream as soon as its
permission request resolves. Separate video elements prevent an old run from
clearing a subsequent run's preview. Resuming requires another explicit action.
The same button remains focused during start/stop; a successful result focuses
its heading. Barcode text is rendered as text, never as a URL or markup.

## Dependencies and access boundary

Native `BarcodeDetector` has limited browser availability, so the scanner
lazily loads locally bundled
`@zxing/browser` 0.1.5 and its `@zxing/library` 0.21.3 peer. These are compatible
with the existing Node 22 deployment; newer pairs currently require Node 24.
They replace writing/maintaining a barcode decoder and camera sampling loop.
There are no CDN scripts, provider credentials or scanner-side network requests.
Explicit copy saves use the existing authenticated inventory API.
See the [ZXing browser project](https://github.com/zxing-js/browser) and
[browser camera requirements](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia).

Private phone access must retain owner authentication, exact-origin/Host checks,
CSRF protection and Secure, HttpOnly cookies. The existing preview bridge is
specifically a loopback adapter and forwards only its loopback session cookie;
putting an HTTPS proxy in front of it unchanged does not establish the required
phone security boundary. Choose and verify the phone access path separately.
Network access, origins and credentials remain part of the separate phone-access
deployment; this intake increment does not change them.

Each bundled type config declares `barcode_formats` and optional `lookup`.
Album selects the first installed MusicBrainz adapter. Comics/Other have no lookup
configured. Suggestions remain unconfirmed personal-copy details, with no automatic
catalog identity or ownership. Provider availability and physical-phone validation
remain separate checks.
