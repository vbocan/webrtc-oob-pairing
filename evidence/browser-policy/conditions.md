# M2 — run conditions

Companion to `evidence/throughput/conditions.md`, for the M2 (WebRTC
disabled by browser policy) mitigation scenario. **Successful mitigation
run: 0/5 established.**

## Date / artifact

- Run date: 2026-06-17 (~22:05 local).
- Artifact version (stamped in `session_start`): **0.4.0**.
- Logs: `laptop.jsonl` (sender), `phone.jsonl` (empty — no phone needed;
  see below).

## Control under test (how the policy was realised)

- Realised via **Option C — throwaway Dockerized Firefox** with an
  enterprise policy, fully reversible, no host browser/registry touched.
  Setup in `testbed/m2-browser-policy/` (`policies.json` +
  `docker-compose.yml`); see the M2 row in the top-level `README.md`.
- Browser: **Firefox 151.0** (Linux, in container; UA
  `X11; Linux x86_64; rv:151.0`).
- Policy: `media.peerconnection.enabled = false` (**locked**) — the
  canonical "disable WebRTC by browser policy" lever.
- Policy confirmed live at `about:policies` → Active (screenshot
  `policy-active.png`): the locked `Preferences` entry is shown.

## Why no phone / mic / camera was involved

With WebRTC disabled, `new RTCPeerConnection()` is undefined, so the
sender throws at **offer creation** — before the page requests the
microphone, renders the QR, or needs the phone. The run is therefore a
workstation-only demonstration; `phone.jsonl` is intentionally empty.

## Result summary

- Pairing established: **0/5** (expected 0/5). ✓
- Every iteration: `iteration_start` → `pairing_start` →
  **`iteration_pairing_threw` reason `"RTCPeerConnection is not defined"`**
  → `iteration_failed` (phase `pairing`). No `offer_created`, no ICE
  candidates, no QR rendered.
- Failure mode from analyzer: `pairing` ×5. Metrics in `per-iter.csv`.

## Fidelity note for the paper

The other runs (B1/B2/E1/M1) used Edge/Chrome on Windows; M2 here is
realised with **Firefox** enterprise policy because it provides the
cleanest, documented WebRTC kill-switch
(`media.peerconnection.enabled=false`). The §7 M2 row / §6 prose should
state the actual lever used. The Chrome/Edge registry equivalent
(`WebRtcLocalIpsAllowedUrls` / `URLBlocklist`) is the alternative
realisation, not used here.
