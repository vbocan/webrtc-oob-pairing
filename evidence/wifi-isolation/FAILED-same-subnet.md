# M1 — ineffective-config run: naïve "guest network" isolation does NOT close the surface

**This is not a successful M1 mitigation run.** It is a documented
*negative* result: an attempted Wi-Fi isolation that failed to block the
channel because the guest network shared the workstation's subnet. The
finding is useful for §7 and is preserved here deliberately.

## What was attempted

- Run date: 2026-06-17 (~21:17 local).
- Artifact version: **0.4.0**.
- Logs: `laptop-FAILED-same-subnet.jsonl`, `phone-FAILED-same-subnet.jsonl`.
- Router setting: TP-Link **guest network** with **"Allow Local Access" =
  OFF**. Phone associated to the **guest** SSID; workstation on the
  corporate LAN.
- Intent: deny the peer UDP path (attack-tree leaf A8f). Expected 0/5.

## What actually happened

- **5 of the attempted iterations paired and transferred 1 MB**
  (iters 1, 3, 4, 5, 6). Iters 2 and 7 failed only on the *acoustic* leg
  (no `audio_frame_decoded`; `auto_rescan reason: tx-grace`) — **not** on
  the network. The channel was not blocked.
- ICE `selected_pair` on every successful iteration:
  **`192.168.1.100 ↔ 192.168.1.189`** (host↔host, direct UDP).

## Root cause

The phone and the workstation were on the **same `192.168.1.0/24`
subnet**:

| Device | Host candidate(s) seen | Subnet |
|---|---|---|
| Workstation | `192.168.1.100` (selected), also `192.168.100.5`, `172.26.96.1`, `172.30.48.1` | `192.168.1.0/24` (+ virtual adapters) |
| Phone (guest SSID) | `192.168.1.189` (selected), also `10.66.30.66`, `10.106.193.83` | **same** `192.168.1.0/24` |

The guest SSID was **bridged to the main subnet**. The "Allow Local
Access = OFF" toggle on this router restricts guest reachability to
router/LAN *services*, but does **not** enforce layer-2 station-to-station
isolation against a same-subnet wired host. The phone therefore reached
`192.168.1.100` directly via the host candidate, and ICE selected it.

The 10-second pre-check (load `https://192.168.1.100:8000/...` from the
phone) would have caught this: that page would have loaded, proving the
LAN path was open.

## Implication for the paper (§7 mitigation taxonomy)

This *strengthens* the M1 row rather than weakening it. The mitigation
that closes the surface is **true client/station isolation or VLAN/subnet
separation** — not a consumer "guest network + block-local-access" toggle
that leaves both peers in one broadcast domain. The §7 prose should state:

> Naïve guest-network isolation that bridges the guest SSID to the
> corporate subnet does **not** close the surface; the channel selects a
> host↔host candidate pair on the shared subnet and establishes normally.
> Effective mitigation requires AP/station isolation (blocking
> station-to-station traffic) or placing BYOD devices on a separate,
> firewalled subnet with no route to workstation IPs.

## Next attempt

Re-run with the phone on a path that has **no route to any workstation
candidate IP** (cellular-only, true station isolation, or a separate
firewalled subnet). Gate the run on the reachability pre-check in the M1
row of the top-level `README.md` (confirm the workstation page is
unreachable from the phone first). A clean M1 result lands in
`laptop.jsonl` / `phone.jsonl` (no `-FAILED-` suffix) with 0/5 established.
