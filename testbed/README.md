# Testbed

Docker rigs that reproduce the adversarial scenarios in the evaluation.
Each rig is self-contained in its own folder; nothing is installed on the
host, and `docker compose down` removes every trace.

| Folder | Scenario | What it brings up |
|---|---|---|
| [`tls-proxy/`](tls-proxy/) | **C4** (TLS-intercepting proxy) | mitmproxy |
| [`m2-browser-policy/`](m2-browser-policy/) | **M2** (WebRTC disabled by managed-browser policy) | a throwaway Dockerized Firefox with `media.peerconnection.enabled=false` locked |

The two rigs are split by concern: `tls-proxy/` imposes a control at the
**network layer**, whereas `m2-browser-policy/` imposes one at the **browser
layer** and needs a different setup (noVNC GUI, policy mount). Keeping them
apart avoids conflating the two and lets each be torn down independently.

> **C5 (DNS restriction)** needs no rig — it is reproduced with the browser
> flag `--host-resolver-rules`, not Docker. See
> [`../evidence/dns-denied/conditions.md`](../evidence/dns-denied/conditions.md).

## 1. TLS-intercepting proxy (`tls-proxy/`)

```sh
cd tls-proxy
docker compose up -d                   # mitmproxy; proxy :8080, web UI :8081
docker compose down                    # tear down
```

First-run setup notes (CA-cert install on the phone) are in the header
comments of [`tls-proxy/docker-compose.yml`](tls-proxy/docker-compose.yml).

## 2. Browser policy (`m2-browser-policy/`)

```sh
cd m2-browser-policy
docker compose up -d                   # Firefox + noVNC at http://localhost:3010
docker compose down
```

The locked policy lives in
[`m2-browser-policy/policies.json`](m2-browser-policy/policies.json); verify
it took via `about:policies` after the container starts.
