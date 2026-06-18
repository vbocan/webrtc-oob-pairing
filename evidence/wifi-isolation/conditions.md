# M1 — run conditions

Companion to `evidence/throughput/conditions.md`, for the M1 (Wi-Fi client
isolation) mitigation scenario. **Successful mitigation run: 0/5
established.** (For the earlier ineffective-config attempt, see
`FAILED-same-subnet.md`.)

## Date / artifact

- Run date: 2026-06-17 (~21:30 local).
- Artifact version (stamped in `session_start`): **0.4.0**.
- Logs: `laptop.jsonl`, `phone.jsonl`.

## Control under test (how isolation was realised)

- The phone (Bob, BYOD) was placed on **cellular data only**, with Wi-Fi
  off — i.e. **no network path to any workstation candidate IP**. The
  workstation (Alice) stayed on the corporate LAN. This realises the §7
  claim that denying the BYOD↔workstation peer path closes the surface.
- The pairing page was loaded on the phone over Wi-Fi first, then Wi-Fi
  was disabled and the tab kept open (the client-side SPA needs no server
  after load).
- Pre-check (STOP gate): from the phone on cellular, the workstation's
  pairing URLs were unreachable.

## Candidate evidence (why ICE could not connect)

| Device | Host candidates advertised | Reachable common path? |
|---|---|---|
| Workstation | `192.168.100.5`, `192.168.1.100`, `172.26.96.1`, `172.30.48.1` | — |
| Phone (cellular) | `10.66.30.66`, `10.106.193.83` only — **no `192.168.x`** | **none** |

The app uses no STUN/TURN (host candidates only), so with the phone off
the LAN there was no candidate pair that could connect.

## Devices

| Role | Device / OS | Browser |
|---|---|---|
| Workstation (sender) | Windows 11 x64 | Edge 149 |
| Phone (receiver) | Android (Edge for Android 148), cellular data only | Edge for Android |

## Result summary

- Pairing established: **0/5** (expected 0/5). ✓
- **Bootstrap legs succeeded** on all five: QR scanned + `qr_rendered`,
  and the acoustic answer was decoded (`audio_frame_decoded`,
  `remote_applied addedOk:4`). Only the network leg (attack-tree A8f)
  failed.
- Network outcome each iteration: `connection_state: connecting` →
  `failed` → `ice_timeout` (45 s) → `iteration_failed` (phase `pairing`).
- ICE gathering still completed (laptop median 140 ms, phone 129 ms) —
  candidates were gathered, just unroutable to each other.
- Failure mode from analyzer: `pairing` ×5. Full per-iteration metrics in
  `per-iter.csv`.

## Significance

This is the empirical confirmation for the §7 M1 row: when the BYOD device
has no LAN path to the workstation, the QR + acoustic bootstrap still
works but the WebRTC DataChannel never establishes. Paired with
`FAILED-same-subnet.md`, the paper can make the sharper point that the
mitigation must be **true isolation / separate subnet**, not a
same-subnet "guest network" toggle.
