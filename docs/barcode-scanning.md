# Camera barcode trial

The first increment reads a barcode and displays its digits, detected format and
optional supplement. It does **not** identify an edition, fill the add form,
create ownership, search a provider, upload a frame or save a reading. Existing
intake drafts remain independent.

## Try it

After owner sign-in, choose **Scan barcode** beside Add a find. Allow camera
access when prompted, hold the barcode steady, then inspect the reading. The
camera stops after the first valid UPC/EAN result. Choose **Scan another barcode**
to repeat or **Close scanner** to discard the reading. Nothing is saved.

Camera access requires a secure browser context. A Mac's localhost preview can
use that Mac's camera. A phone needs a private HTTPS address reachable from the
phone; the current Mac-loopback SSH preview is not that address. This increment
does not provision phone access or change the live app's network or sign-in
configuration. Physical-phone testing remains a separate rollout step.

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

The existing application has no barcode decoder. Native `BarcodeDetector` has
limited browser availability, so the trial lazily loads locally bundled
`@zxing/browser` 0.1.5 and its `@zxing/library` 0.21.3 peer. These are compatible
with the existing Node 22 deployment; newer pairs currently require Node 24.
They replace writing/maintaining a barcode decoder and camera sampling loop.
There are no CDN scripts, provider credentials or scanner-side network requests.
See the [ZXing browser project](https://github.com/zxing-js/browser) and
[browser camera requirements](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia).

Private phone access must retain owner authentication, exact-origin/Host checks,
CSRF protection and Secure, HttpOnly cookies. The existing preview bridge is
specifically a loopback adapter and forwards only its loopback session cookie;
putting an HTTPS proxy in front of it unchanged does not establish the required
phone security boundary. Choose and verify the phone access path separately.
No public tunnel, published container ports, origin relaxation, credential
rotation or VPN configuration is part of this scanner-only increment.

Next work: private phone access and hands-on camera validation, then reviewed
catalog suggestions (Albums first). Supported identifiers and lookup behavior
should be declared in each collection type's configuration when lookup exists;
this prototype adds no unused pack/provider framework or identifier schema.
