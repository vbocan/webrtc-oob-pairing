// Transport-agnostic pairing helpers shared by laptop.html and phone.html.
//
// Both pages do the same dance around the QWBP codec: extract the DTLS
// fingerprint, derive HKDF ICE credentials, patch the local SDP, gather
// ICE, encode the packet — and on the receive side, decode, reconstruct,
// addIceCandidate. Centralising the dance here keeps the page scripts
// focused on transport (QR vs ggwave).

import {
  encode, decode,
  extractCandidatesFromSDP, extractFingerprintFromSDP,
  reconstructSDP, buildCandidateString,
  deriveCredentials,
} from './vendor/qwbp.js';

export { encode, decode };

// QWBP's library doesn't export its SDP credential patcher, so we inline
// it. Both peers re-derive ICE ufrag/pwd from the fingerprint via HKDF,
// then string-replace the browser-generated creds before setLocalDescription.
export function patchSdpCredentials(sdp, ufrag, pwd) {
  return sdp
    .replace(/a=ice-ufrag:\S+/g, `a=ice-ufrag:${ufrag}`)
    .replace(/a=ice-pwd:\S+/g, `a=ice-pwd:${pwd}`);
}

export function awaitIceComplete(pc) {
  return new Promise(resolve => {
    if (pc.iceGatheringState === 'complete') return resolve();
    const check = () => {
      if (pc.iceGatheringState === 'complete') {
        pc.removeEventListener('icegatheringstatechange', check);
        resolve();
      }
    };
    pc.addEventListener('icegatheringstatechange', check);
  });
}

// Take a fresh offer/answer SDP, HKDF-derive matching ICE creds from its
// fingerprint, patch them in, set as local description, gather ICE, then
// return the encoded QWBP packet (Uint8Array).
export async function localToPacket(pc, type, sdp) {
  const fingerprint = extractFingerprintFromSDP(sdp);
  const creds = await deriveCredentials(fingerprint);
  const patched = patchSdpCredentials(sdp, creds.ufrag, creds.pwd);
  await pc.setLocalDescription({ type, sdp: patched });
  await awaitIceComplete(pc);
  const candidates = extractCandidatesFromSDP(pc.localDescription.sdp);
  return { packet: encode(fingerprint, candidates), candidates, fingerprint };
}

// Decode an incoming QWBP packet, reconstruct the remote SDP (creds
// derived via HKDF from the remote's fingerprint), apply it, and add
// each candidate via addIceCandidate.
export async function packetToRemote(pc, packet, isOffer) {
  const decoded = decode(packet);
  const sdp = await reconstructSDP(decoded.fingerprint, isOffer);
  await pc.setRemoteDescription({
    type: isOffer ? 'offer' : 'answer',
    sdp,
  });
  let ok = 0, bad = 0;
  for (const c of decoded.candidates) {
    const candStr = await buildCandidateString(c);
    try {
      await pc.addIceCandidate({ candidate: candStr, sdpMid: '0', sdpMLineIndex: 0 });
      ok++;
    } catch {
      bad++;
    }
  }
  return { decoded, addedOk: ok, addedBad: bad };
}

// QWBP packets are tiny and start with magic byte 0x51 ('Q'). Pre-screen
// before invoking the full codec so noise frames and accidental QR scans
// of unrelated codes are rejected cheaply. Returns the decoded packet on
// success, or throws with a short reason on failure.
const QWBP_MAGIC = 0x51;
const QWBP_MIN_SIZE = 34;   // 2 B header + 32 B fingerprint
export function tryDecodeQwbp(bytes) {
  if (bytes.length < QWBP_MIN_SIZE) {
    throw new Error(`packet too small (${bytes.length} B)`);
  }
  if (bytes[0] !== QWBP_MAGIC) {
    throw new Error(`bad magic 0x${bytes[0].toString(16)}`);
  }
  return decode(bytes);
}

// Wire the ICE state change handler + a one-shot pairing timeout onto a
// peer connection. The callbacks fire exactly once each. log/status are
// the page's UI sinks; the page itself opens its post-connect UI.
export function wireConnectionLifecycle(pc, { onConnected, onTimeout, timeoutMs, log, status }) {
  let resolved = false;
  const finish = (which) => {
    if (resolved) return;
    resolved = true;
    clearTimeout(timer);
    which();
  };
  pc.addEventListener('iceconnectionstatechange', () => {
    const s = pc.iceConnectionState;
    log(`ICE state → ${s}`);
    const cls = (s === 'connected' || s === 'completed') ? 'ok'
              : (s === 'failed') ? 'bad' : '';
    status(`ICE: ${s}`, cls);
    if (s === 'connected' || s === 'completed') finish(onConnected);
  });
  const timer = setTimeout(() => finish(onTimeout), timeoutMs);
  return () => finish(() => {});  // cancel hook
}

// --- ICE diagnostics --------------------------------------------------
// Multi-homed hosts (WSL/Hyper-V virtual adapters, several NICs) make ICE
// pick from many local candidates, only some reachable by the peer. These
// helpers make the actual path visible per pairing.

// Log every local host/srflx candidate gathered (all interfaces).
export function logLocalCandidates(pc, log, evt) {
  const lines = (pc.localDescription?.sdp || '')
    .split(/\r?\n/).filter(l => l.startsWith('a=candidate:'));
  const cands = lines.map(l => {
    const p = l.split(' ');
    return { ip: p[4], port: p[5], type: p[7] };   // ...4=ip 5=port 6='typ' 7=type
  });
  const summary = cands.map(c => `${c.type} ${c.ip}:${c.port}`).join(', ');
  log(`Local candidates (${cands.length}): ${summary || '(none)'}`);
  evt?.record('local_candidates', { count: cands.length, candidates: cands });
}

// Log the nominated/selected ICE candidate pair (which local↔remote IPs
// actually carried the connection).
export async function logSelectedPair(pc, log, evt) {
  try {
    const stats = await pc.getStats();
    const locals = {}, remotes = {};
    let pair = null;
    stats.forEach(r => {
      if (r.type === 'local-candidate') locals[r.id] = r;
      else if (r.type === 'remote-candidate') remotes[r.id] = r;
      else if (r.type === 'candidate-pair' &&
               (r.nominated || r.selected || r.state === 'succeeded')) {
        if (!pair || r.nominated) pair = r;
      }
    });
    if (!pair) { log('No nominated ICE pair in stats.', 'warn'); return; }
    const L = locals[pair.localCandidateId] || {};
    const R = remotes[pair.remoteCandidateId] || {};
    const li = `${L.address || L.ip}:${L.port} (${L.candidateType})`;
    const ri = `${R.address || R.ip}:${R.port} (${R.candidateType})`;
    log(`Selected ICE pair: local ${li} ↔ remote ${ri}`, 'ok');
    evt?.record('selected_pair', { local: li, remote: ri });
  } catch (e) {
    log(`getStats failed: ${e.message}`, 'warn');
  }
}

// Base64url codec — used to put binary QWBP packets through transports
// that prefer text (QR text mode, ggwave string payloads).
export function bytesToB64url(bytes) {
  let s = '';
  for (let i = 0; i < bytes.length; i++) s += String.fromCharCode(bytes[i]);
  return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

export function b64urlToBytes(str) {
  let s = str.replace(/-/g, '+').replace(/_/g, '/');
  while (s.length % 4) s += '=';
  const bin = atob(s);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}
