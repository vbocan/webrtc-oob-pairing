# T0b throughput sweep (rerun) — run conditions

A **second** steady-state throughput sweep, independent of the committed
`evidence/throughput/` session. Same artifact build (**0.4.0**), different
date and a different LAN subnet, so it serves as a corroborating sample
for the §9 throughput figure — not a re-baseline (the original T0 is
already 0.4.0; see `evidence/throughput/conditions.md`).

## Date / artifact

- Run date: 2026-06-17.
- Artifact version (stamped in every `session_start`): **0.4.0**.
- Logs: `laptop.jsonl` (orig. `qr-webrtc-laptop-2026-06-17T20-24-04.jsonl`),
  `phone.jsonl` (orig. `qr-webrtc-phone-2026-06-17T20-24-10.jsonl`).

## Network

- Subnet: `192.168.1.0/24` — workstation `192.168.1.100`, phone
  `192.168.1.179`. (Differs from the original T0 session, which was on
  `192.168.0.0/24`.)
- Wi-Fi band / AP / RSSI: **TODO — confirm (author)**; not derivable from
  the logs.
- ICE-candidate note: the phone advertised three **host** candidates —
  `192.168.1.179` (LAN) plus `10.66.30.66` and `10.106.193.83`. The two
  `10.x` addresses are additional local interfaces on the phone (VPN /
  private-DNS / tethering-style virtual adapters). They are harmless
  here: the `selected_pair` on **all 30** pairings was
  `192.168.1.179 ↔ 192.168.1.100` — host↔host on the LAN, direct peer UDP
  (attack-tree leaf A8f), no relay.

## Devices (from the user-agent strings)

| Role | Device / OS | Browser | Chromium |
|---|---|---|---|
| Workstation (sender) | Windows 11 x64 | Edge **149** | 149 |
| Phone (receiver) | Android (Edge for Android) | Edge for Android **148** | 148 |

> UA caveat (same as T0): Android UA reduction freezes the OS token at
> "10 (K)"; the real OS version is higher.

## Transfer settings

- Defaults only (not tuned): 16 KB chunks, 1 MB / 256 KB `bufferedAmount`
  window.

## Result summary

- **30 / 30 paired, 30 / 30 transferred.** No failures.
- Handshake median **6.76 s** (mean 6.97 s; min 6.20 s, max 9.94 s —
  iter 1 cold start).
- A single audio chirp sufficed on every iteration (`audio_attempts` = 1).
- Throughput by payload size (median):
  - 100 KB → **2.1 MB/s** (ramp-dominated)
  - 1 MB → **6.1 MB/s**
  - 10 MB → **4.9 MB/s** (steady-state goodput)
- Full per-iteration metrics in `per-iter.csv`.

## How this relates to the paper

Use as a **corroborating** sample for the §9 throughput cell, not a
replacement. The original `evidence/throughput/` (1 MB 7.2 MB/s, 10 MB
6.3 MB/s) remains the headline; this rerun (6.1 / 4.9 MB/s on a different
network with extra virtual interfaces present) confirms the same
order of magnitude under different co-present conditions.
