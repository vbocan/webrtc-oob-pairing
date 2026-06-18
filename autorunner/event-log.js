// Structured event log for measurement runs.
//
// Each call to record(event, payload) appends one JSON line of the form
//   { t, iteration, event, ...payload }
// where t is milliseconds since the log was started (or last cleared).
// download(filename) emits the lines as JSONL — one event per line —
// ready for analysis in pandas, jq, or a notebook.
//
// Designed to be cheap (no batching, no formatting until download) so
// it's safe to leave on even during normal pairings.

export class EventLog extends EventTarget {
  constructor(role, meta = {}) {
    super();
    this.role = role;
    this.lines = [];
    this.t0 = performance.now();
    this.iteration = 0;
    // Caller-supplied meta (e.g. {version}) is folded into session_start
    // so the data file itself proves which build produced it.
    this.record('session_start', { role, ua: navigator.userAgent, ...meta });
  }

  nextIteration(extra = {}) {
    this.iteration += 1;
    this.record('iteration_start', { iteration: this.iteration, ...extra });
  }

  record(event, payload = {}) {
    const entry = {
      t: Math.round(performance.now() - this.t0),
      iteration: this.iteration,
      event,
      ...payload,
    };
    this.lines.push(entry);
    // Mirror to console so an open devtools shows the stream live.
    console.log('[evt]', event, payload);
    // Dispatch so awaiters (like the auto-runner) can react to a
    // specific event without polling the lines array.
    this.dispatchEvent(new CustomEvent(event, { detail: entry }));
  }

  // Resolve when `event` is recorded, or reject after `timeoutMs`.
  waitFor(event, timeoutMs = 60_000) {
    return new Promise((resolve, reject) => {
      const onEvent = (ev) => {
        clearTimeout(timer);
        resolve(ev.detail);
      };
      const timer = setTimeout(() => {
        this.removeEventListener(event, onEvent);
        reject(new Error(`timeout waiting for "${event}" after ${timeoutMs}ms`));
      }, timeoutMs);
      this.addEventListener(event, onEvent, { once: true });
    });
  }

  count() {
    return this.lines.length;
  }

  download(filename) {
    const text = this.lines.map(l => JSON.stringify(l)).join('\n') + '\n';
    const blob = new Blob([text], { type: 'application/x-ndjson' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename || defaultFilename(this.role);
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  clear() {
    this.lines = [];
    this.t0 = performance.now();
    this.iteration = 0;
    this.record('session_start', { role: this.role });
  }
}

function defaultFilename(role) {
  const stamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  return `qr-webrtc-${role}-${stamp}.jsonl`;
}
