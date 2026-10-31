/** A camera-only trial. Frames and readings stay in this tab; no fetch or storage. */
const lengths = { UPC_A: 12, UPC_E: 8, EAN_8: 8, EAN_13: 13 };
/** @returns {{value:string,format:string,supplement:string|null}|null} */
export function readBarcode(value, format, supplement) {
  if (typeof format !== 'string' || !Object.hasOwn(lengths, format) || typeof value !== 'string' ||
      !/^\d+$/.test(value) || value.length !== lengths[format]) return null;
  return { value, format, supplement: typeof supplement === 'string' && /^(\d{2}|\d{5})$/.test(supplement) ? supplement : null };
}

export function cameraError(error) {
  if (error?.name === 'NotAllowedError' || error?.name === 'SecurityError') return 'Camera access was not allowed. Enable it for this site in your browser settings, then try again.';
  if (error?.name === 'NotFoundError') return 'No camera was found. Try a device with a camera.';
  if (error?.name === 'NotReadableError') return 'The camera is unavailable. Close other apps using it, then try again.';
  return 'The camera could not scan. Stop, check camera access, and try again.';
}

/**
 * Each run owns a separate video element. A late permission/decoder response from
 * a cancelled run can never detach a later run's video or leave its camera on.
 * @param {HTMLElement} container
 * @param {{onReady:()=>void,onResult:(reading:NonNullable<ReturnType<typeof readBarcode>>)=>void,onError:(message:string)=>void}} handlers
 */
export function startBarcodeCamera(container, handlers) {
  const video = document.createElement('video');
  video.muted = true; video.autoplay = true; video.playsInline = true;
  video.setAttribute('aria-label', 'Live barcode camera preview');
  container.replaceChildren(video);
  let stopped = false, stream = null, controls = null;
  const stopTracks = value => value?.getTracks().forEach(track => track.stop());
  const timer = setTimeout(() => fail('Camera stopped after one minute. Start it again when you are ready.'), 60_000);
  function stop() {
    if (stopped) return;
    stopped = true; clearTimeout(timer);
    try { controls?.stop(); } catch { /* Explicit track cleanup below still runs. */ }
    stopTracks(stream);
    video.pause(); video.srcObject = null; video.remove();
  }
  function fail(message) { stop(); handlers.onError(message); }
  async function run() {
    try {
      if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
        fail('Camera scanning needs a supported browser at the private HTTPS address.'); return;
      }
      const [{ BrowserMultiFormatReader }, library] = await Promise.all([import('@zxing/browser'), import('@zxing/library')]);
      if (stopped) return;
      const { BarcodeFormat, DecodeHintType, ResultMetadataType, NotFoundException, ChecksumException, FormatException } = library;
      const hints = new Map([
        [DecodeHintType.POSSIBLE_FORMATS, [BarcodeFormat.UPC_A, BarcodeFormat.UPC_E, BarcodeFormat.EAN_8, BarcodeFormat.EAN_13]],
        [DecodeHintType.TRY_HARDER, true],
      ]);
      const reader = new BrowserMultiFormatReader(hints, { delayBetweenScanAttempts: 300 });
      stream = await navigator.mediaDevices.getUserMedia({ audio: false, video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 }, height: { ideal: 720 } } });
      if (stopped) { stopTracks(stream); return; }
      for (const track of stream.getVideoTracks()) track.addEventListener('ended', () => { if (!stopped) fail('Camera disconnected. Start scanning again when it is available.'); });
      const started = await reader.decodeFromStream(stream, video, (result, error, ownControls) => {
        if (stopped) { ownControls.stop(); return; }
        if (result) {
          const reading = readBarcode(result.getText(), BarcodeFormat[result.getBarcodeFormat()], result.getResultMetadata()?.get(ResultMetadataType.UPC_EAN_EXTENSION));
          if (reading) { controls = ownControls; stop(); handlers.onResult(reading); }
        } else if (error && ![NotFoundException, ChecksumException, FormatException].some(type => error instanceof type)) {
          controls = ownControls; fail(cameraError(error));
        }
      });
      if (stopped) { started.stop(); return; }
      controls = started; handlers.onReady();
    } catch (error) { if (!stopped) fail(cameraError(error)); }
  }
  // Defer unsupported-browser errors until the caller owns the stop handle.
  void Promise.resolve().then(run);
  return { stop };
}
