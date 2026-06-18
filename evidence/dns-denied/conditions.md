# C5 — run conditions

Companion to `evidence/throughput/conditions.md`, for the C5 (external DNS
denied) control scenario. **Channel established with all external DNS
denied: 5/5.**

## Date / artifact

- Run date: 2026-06-17 (~22:47 local).
- Artifact version (stamped in `session_start`): **0.4.1** — the vendored,
  self-contained build (libraries served from `autorunner/vendor/`, no
  external load-time DNS). The 0.4.1 stamp in both logs confirms the
  vendored build actually loaded.
- Logs: `laptop.jsonl`, `phone.jsonl`.

## Control under test (how DNS was denied)

- Realised via **browser-level DNS denial**, no host changes. The
  workstation ran a throwaway Edge launched with
  `--host-resolver-rules="MAP * ~NOTFOUND, EXCLUDE localhost"`, so the
  pairing browser could resolve **no external name** while `localhost`
  (the local page + vendored libs) still loaded.
- Page + libraries served locally from Docker (`autorunner` compose,
  `https://localhost:8000`); nothing installed on the host.
- **DNS-denial evidence:** `dns-denied.png` (present) — `https://example.com`
  failing with `DNS_PROBE_FINISHED_NXDOMAIN` ("can't reach this page") in
  the same browser during the run window. This is the C5 evidence: the
  workstation browser could resolve no external name, yet pairing still
  ran 5/5.

## ICE path

- Selected pair on all 5 iterations: **host↔host on the LAN**
  (`192.168.1.100 ↔ 192.168.1.179`), direct peer UDP, no relay. The
  workstation advertised `192.168.1.100` / `192.168.100.5` (+ `172.x`
  Hyper-V/WSL virtuals); the phone advertised `192.168.1.179` (+ `10.x`
  Nebula interfaces). No STUN/TURN, so no name was resolved during pairing.

## Devices

| Role | Device / OS | Browser |
|---|---|---|
| Workstation (sender) | Windows 11 x64 | Edge 149, throwaway profile, DNS-denied via flag |
| Phone (receiver) | Android (Edge for Android 148) | Edge for Android, normal networking |

## Result summary

- **5/5 paired, 5/5 transferred** (1 MB each) with external DNS denied. ✓
- Handshake median **6.45 s** (mean 8.48 s, inflated by the iter-1
  cold start at 16.7 s; iters 2–5 cluster at ~6.4 s).
- One audio chirp sufficed each time. Throughput median ~2.0 MB/s at 1 MB
  (this run is establishment + DNS-independence, not a throughput study;
  see T0/T0b for goodput).
- Full per-iteration metrics in `per-iter.csv`.

## Significance

Empirical confirmation for §6.3: once the page is loaded, the surface
needs no name resolution — the pairing page is a `localhost`/IP-literal
origin and the WebRTC handshake uses ICE host candidates with no STUN or
TURN. Denying the workstation browser all external DNS does not impede
establishment.
