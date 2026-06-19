// Tiny file transfer protocol on top of an RTCDataChannel.
//
// Wire format (one transfer = one manifest + N chunks + one done + one ack):
//
//   text  : {"type":"manifest","name":...,"size":...,"mime":...,"chunks":N}
//   binary: ArrayBuffer chunk #1
//   binary: ArrayBuffer chunk #2
//   ...
//   text  : {"type":"done"}
//   text  : {"type":"ack"}                   <-- from receiver to sender
//
// sendFile() doesn't resolve until the ack arrives. That makes "the file
// is on the other side" a real signal, not a hope based on
// bufferedAmount + a sleep. The caller can safely close the peer
// connection as soon as sendFile() resolves.
//
// Multiple transfers can run sequentially over the same channel —
// receiveFile() resets its accumulator on each new manifest.
//
// Chunks are 16 KB, which fits the practical cross-browser DataChannel
// message limit. bufferedAmount is monitored so we don't outrun the
// channel's send queue on large files.

const CHUNK_SIZE = 16 * 1024;
const BUFFER_HIGH = 1 * 1024 * 1024;   // pause sending above this
const BUFFER_LOW = 256 * 1024;         // resume when drained below this

// ---- sender ------------------------------------------------------------

export async function sendFile(channel, file, { onProgress, ackTimeoutMs = 15_000 } = {}) {
  channel.binaryType = 'arraybuffer';
  channel.bufferedAmountLowThreshold = BUFFER_LOW;

  // Install the ack listener BEFORE sending anything so we never miss
  // the ack message between send-done and start-listening.
  const ackPromise = new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      channel.removeEventListener('message', listener);
      reject(new Error(`ack timeout after ${ackTimeoutMs}ms`));
    }, ackTimeoutMs);
    const listener = (ev) => {
      if (typeof ev.data !== 'string') return;
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === 'ack') {
          clearTimeout(timer);
          channel.removeEventListener('message', listener);
          resolve();
        }
      } catch { /* not JSON, ignore */ }
    };
    channel.addEventListener('message', listener);
  });

  const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
  channel.send(JSON.stringify({
    type: 'manifest',
    name: file.name,
    size: file.size,
    mime: file.type || 'application/octet-stream',
    chunks: totalChunks,
  }));

  let sent = 0;
  for (let offset = 0; offset < file.size; offset += CHUNK_SIZE) {
    if (channel.readyState !== 'open') {
      throw new Error(`channel closed mid-transfer (state=${channel.readyState})`);
    }
    if (channel.bufferedAmount > BUFFER_HIGH) {
      await new Promise(resolve => {
        channel.addEventListener('bufferedamountlow', resolve, { once: true });
      });
    }
    const chunk = await file.slice(offset, offset + CHUNK_SIZE).arrayBuffer();
    channel.send(chunk);
    sent += chunk.byteLength;
    onProgress?.(sent, file.size);
  }

  channel.send(JSON.stringify({ type: 'done' }));

  // Wait for receiver to ack — proves the file is intact on the other
  // side before the caller closes the peer connection.
  await ackPromise;
}

// ---- receiver ----------------------------------------------------------

// Attaches a message handler to the channel. Returns a detach function
// in case the caller wants to swap protocols later.
export function receiveFile(channel, { onManifest, onProgress, onComplete, onError } = {}) {
  channel.binaryType = 'arraybuffer';

  let manifest = null;
  let chunks = [];
  let received = 0;

  const handler = (ev) => {
    try {
      if (typeof ev.data === 'string') {
        const msg = JSON.parse(ev.data);
        if (msg.type === 'manifest') {
          manifest = msg;
          chunks = [];
          received = 0;
          onManifest?.(manifest);
        } else if (msg.type === 'done') {
          if (!manifest) throw new Error('done without manifest');
          if (received !== manifest.size) {
            throw new Error(`size mismatch: expected ${manifest.size}, got ${received}`);
          }
          const blob = new Blob(chunks, { type: manifest.mime });
          const completed = manifest;
          manifest = null;
          chunks = [];
          received = 0;
          // Send the ack BEFORE invoking onComplete so the sender can
          // close the channel even if onComplete does heavy work
          // (image render, blob URL allocation, etc.).
          try { channel.send(JSON.stringify({ type: 'ack' })); }
          catch (e) { onError?.(new Error(`ack failed: ${e.message}`)); }
          onComplete?.(blob, completed);
        }
      } else {
        if (!manifest) throw new Error('binary chunk before manifest');
        chunks.push(ev.data);
        received += ev.data.byteLength;
        onProgress?.(received, manifest.size);
      }
    } catch (err) {
      onError?.(err);
    }
  };

  channel.addEventListener('message', handler);
  return () => channel.removeEventListener('message', handler);
}

// ---- formatting helpers (shared UI) -----------------------------------

export function formatBytes(n) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(2)} MB`;
}
