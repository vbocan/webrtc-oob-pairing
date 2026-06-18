# C4 — run conditions

Companion to `evidence/throughput/conditions.md`, for the C4
(TLS-intercepting forward proxy) scenario.

## Date / artifact

- Run date: 2026-06-10.
- Artifact version: **0.4.0** (stamped in `session_start`).
- Logs: `qr-webrtc-laptop-2026-06-10T11-07-00.jsonl`,
  `qr-webrtc-phone-2026-06-10T11-06-43.jsonl`.
- Proxy capture: `flows` (~158 MB, gitignored); curated in
  `proxy-evidence.md`.

## Network

- Wi-Fi band **5 GHz**, AP **TP-Link Archer C2**.
- Workstation `192.168.0.101`; phone `192.168.0.102` (different DHCP
  lease than the T0 session, which was `.103`).

## Control under test (Docker, nothing installed on host)

- **mitmproxy** in Docker (`testbed/tls-proxy`), listening
  `127.0.0.1:8080`, mitmweb UI `:8081`.
- Static pairing-page server also in Docker
  (`autorunner/docker-compose.yml`), `:8000`.
- Workstation browser: **throwaway** Edge instance launched with
  `--proxy-server=127.0.0.1:8080 --ignore-certificate-errors
  --user-data-dir=$TEMP\c4-edge-profile --test-type`. No CA installed,
  no system proxy, ephemeral profile. Phone (BYOD) **not** proxied.
- Proxy verified live: `example.com` decrypted in mitmweb before the run
  (see `proxy-evidence.md`).

## Devices

| Role | Device / OS | Browser |
|---|---|---|
| Workstation (sender) | Windows 11 x64 | Edge 149, throwaway profile |
| Phone (receiver) | Motorola Edge 60 Pro, Android 16 | Edge for Android |

## ICE path

- Selected pair **host↔host on the LAN** on all 10 iterations
  (`192.168.0.101` ↔ `192.168.0.102`), no relay.
- Iter 1 cold-start anomaly: a single mDNS `.local` candidate surfaced
  and the handshake took 35.8 s; from iter 2 the full 8-candidate set
  appeared and handshakes normalised to ~7.3 s.

## Result summary

- **10 / 10 paired, 10 / 10 transferred — through the active proxy.**
- Handshake median 7.3 s (mean inflated by the iter-1 cold start).
- Throughput (1 MB) median ~1.0 MB/s — **lower than T0's 7.2 MB/s**, but
  the path is identical (host↔host LAN), so the proxy is not in the data
  path. The likely cause is contention: the throwaway profile generated
  1104 background HTTP requests (~158 MB of Edge first-run telemetry)
  over the same Wi-Fi during the run. **Throughput is T0's measurement,
  not C4's** — C4 measures establishment + proxy-blindness, both
  confirmed. For later C/M scenarios, suppress the profile's telemetry
  (or warm the profile) so it doesn't contend.
- Proxy-side evidence (1104 flows incl. example.com; 0 flows to the
  peer): `proxy-evidence.md`.
