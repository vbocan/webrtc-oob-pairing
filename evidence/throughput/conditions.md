# T0 throughput sweep — run conditions

Recorded alongside the data per the run protocol in the top-level
`README.md`. These are the "representative co-present conditions" the paper
cites when
framing the throughput figure as an order-of-magnitude number.

## Date / artifact

- Run date: 2026-06-10.
- Artifact version (stamped in every `session_start` event): **0.4.0**.
- Logs: `qr-webrtc-laptop-2026-06-10T10-32-06.jsonl`,
  `qr-webrtc-phone-2026-06-10T10-32-08.jsonl`.

## Network

- Wi-Fi band: **5 GHz**.
- Access point: **TP-Link Archer C2**.
- Both peers associated to the same LAN subnet (`192.168.0.0/24`):
  workstation `192.168.0.101`, phone `192.168.0.103`.

## Devices

| Role | Device / OS | Browser | Chromium |
|---|---|---|---|
| Workstation (sender) | Windows 11 x64 | Edge **149** | 149 |
| Phone (receiver) | Motorola Edge 60 Pro, **Android 16** | Edge for Android **148** | 148 |

> UA caveat: the phone's reported user-agent string is
> `Android 10; K … EdgA/148.0.0.0` — Android's UA reduction freezes the
> OS token at "10 (K)" regardless of the real OS version. The actual
> device OS is Android 16; the actual browser is Edge for Android 148.
> The workstation reports `Chrome/149 … Edg/149`.

## ICE path (attack-tree leaf A8f)

- Selected candidate pair on **all 29 successful pairings**:
  **host ↔ host on the LAN** (`192.168.0.101` ↔ `192.168.0.103`),
  direct peer UDP.
- Zero relay / srflx / prflx pairs selected — confirmed by the
  `selected_pair` events in the laptop log. No TURN relay involved.

## Transfer settings

- Defaults only (not tuned for a headline number): 16 KB chunks,
  1 MB / 256 KB `bufferedAmount` window.

## Result summary

- 29 / 30 paired (one pairing failure, iter 10, in the 100 KB bucket).
- Steady-state goodput **~6–7 MB/s**: 1 MB median 7.2 MB/s,
  10 MB median 6.3 MB/s. 100 KB is ramp-dominated at ~2.1 MB/s.
- Full per-iteration metrics in `per-iter.csv`.
