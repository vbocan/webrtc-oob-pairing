// Shared helpers for ggwave.js.
//
// ggwave's JS bindings shuttle audio buffers around as Int8Array even when
// the bytes are really Float32 samples. This shim hides the type punning
// and exposes a small, typed API for the two pages.

export function convertTypedArray(src, type) {
  const buffer = new ArrayBuffer(src.byteLength);
  new src.constructor(buffer).set(src);
  return new type(buffer);
}

// Wait until the global `ggwave_factory` script tag has finished loading
// and return an initialized module instance bound to the given context's
// sample rate.
export async function initGgwave(audioContext) {
  if (typeof ggwave_factory !== 'function') {
    throw new Error('ggwave_factory missing — did the <script> tag load?');
  }
  const ggwave = await ggwave_factory();
  const params = ggwave.getDefaultParameters();
  params.sampleRateInp = audioContext.sampleRate;
  params.sampleRateOut = audioContext.sampleRate;
  const instance = ggwave.init(params);
  return { ggwave, instance };
}

// Protocol shortcuts, named for clarity.
export function protocols(ggwave) {
  return {
    AUDIBLE_NORMAL:  ggwave.ProtocolId.GGWAVE_PROTOCOL_AUDIBLE_NORMAL,
    AUDIBLE_FAST:    ggwave.ProtocolId.GGWAVE_PROTOCOL_AUDIBLE_FAST,
    AUDIBLE_FASTEST: ggwave.ProtocolId.GGWAVE_PROTOCOL_AUDIBLE_FASTEST,
  };
}
