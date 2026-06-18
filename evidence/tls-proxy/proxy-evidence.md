# E1 — proxy-side evidence

The headline of E1 is a *negative* result at the proxy: with a
TLS-intercepting forward proxy verifiably live in front of the
workstation, the pairing and file transfer are invisible to it. This
file records that evidence. It is derived from the raw mitmproxy capture
(`flows`, ~158 MB, **not committed** — gitignored as binary telemetry
noise; regenerate by re-running E1, or read a local copy with the
command below).

## The proxy was live and decrypting (positive control)

mitmproxy intercepted **1104 HTTP(S) request flows** during the session,
all TLS-decrypted. Top hosts:

| Flows | Host | What it is |
|---|---|---|
| 707 | edge.microsoft.com | Edge first-run telemetry / config / component updates |
| 239 | assets.msn.com | new-tab page content |
| 23 | browser.events.data.msn.com | telemetry |
| 22 | www.bing.com | SmartScreen / bloom filters |
| 16 | www.gstatic.com | component updater |
| 6 | esm.sh | **the pairing page's libs** (`qrcode@1.5.4`, `qwbp@0.1.0`) |
| 4 | **example.com** | **the manual sanity check — confirms decryption is live** |
| … | (unpkg.com) | `ggwave@0.4.0/ggwave.js` (59.1 kB, decrypted) |

The `example.com` sanity check (4 flows) and the decrypted page
dependencies (`ggwave`, `qrcode`, `qwbp`) prove the proxy was fully
intercepting and decrypting TLS throughout the run.

## The channel was invisible to the proxy (the result)

- **Flows involving the peer `192.168.0.102` (the phone): 0**
- **Flows involving the workstation LAN address `192.168.0.101`: 0**
- None of the 10 × 1 MB transfers appear anywhere in the capture.

This is structural, not incidental: the WebRTC DataChannel is
SCTP-over-DTLS-over-**UDP**, established peer-to-peer on the LAN
(host↔host ICE pair on all 10 iterations — see `per-iter.csv` and the
`selected_pair` events). An HTTP/HTTPS forward proxy never sees it.

## Reproduce the check

With the raw `flows` file present and the testbed image pulled:

```powershell
$d = "<repo>\runs\tls-proxy"
docker run --rm -v "${d}:/data" mitmproxy/mitmproxy:latest `
  mitmdump -nr /data/flows --set flow_detail=1 2>&1 |
  Select-String '192\.168\.0\.10'      # expect: no matches
```

## Fidelity note (attack-tree leaf A8a)

In this run the pairing page pulled `ggwave`, `qrcode`, and `qwbp` from
public CDNs (`esm.sh`, `unpkg.com`), which transited the proxy. Leaf A8a
("load static HTML page — self-hosted or pre-cached") assumes these are
vendored locally. In a locked-down deployment the adversary would bundle
them; doing so would remove even these incidental flows. This does not
affect the result — the *channel* is invisible regardless — but the
paper should note that a fully self-contained page leaves the proxy with
nothing but the operator's own background traffic.
