"""Project a chrome://webrtc-internals "Create Dump" onto the webrtc_api schema.

Primary, production-equivalent telemetry source for §8.3
(telemetry-pipeline.md §3.1). The dump is a JSON object with:

  - "getUserMedia": a list of calls; the *call* entries carry the requested
    constraints (an "audio" key when audio was requested) and "origin"/"url"
    -> F1 (media_kind=audio) and F4 (tab_origin).
  - "PeerConnections": a dict keyed by connection id; each has "updates"
    whose entries describe createDataChannel / datachannel state changes
    -> F2 (rtcpeerconnection) and F3 (datachannel_open). The connection's
    "url" gives the origin for F3.

Note: webrtc-internals drops a PeerConnection from the dump once it closes,
so a dump taken after an auto-closing pairing may contain getUserMedia
(F1/F4) but an empty PeerConnections (no F3). That is a capture-timing
artefact, not a logic gap; F2/F3 for the rate are taken from the artifact
JSONL via jsonl_to_webrtc_api.py. This parser still emits whatever the dump
contains so the origin clause (F4) is anchored to a production-equivalent
source.

Usage:
    python parse_webrtc_internals.py dump.json [--host ws01] [--process msedge.exe] \
        > events.ndjson

Stdlib only.
"""

import argparse
import json
import sys
from pathlib import Path

DC_HINTS = ("createdatachannel", "datachannel")


def parse(dump, host, process):
    out = []
    # F1 / F4 — getUserMedia call entries (those with an "audio" constraint).
    for gum in dump.get("getUserMedia", []):
        if "audio" in gum and gum.get("audio") not in (None, "", "false"):
            out.append({
                "timestamp": gum.get("timestamp"),
                "host": host,
                "process": process,
                "tab_origin": gum.get("origin") or gum.get("url", ""),
                "api": "getusermedia",
                "media_kind": "audio",
                "channel_label": "",
                "pairing": f"webrtc-internals#{gum.get('pid', 0)}",
                "source": "webrtc-internals",
            })
    # F2 / F3 — per PeerConnection updates.
    for pc_id, pc in (dump.get("PeerConnections") or {}).items():
        origin = pc.get("url", "")
        pairing = f"webrtc-internals#{pc_id}"
        out.append({
            "timestamp": None, "host": host, "process": process,
            "tab_origin": origin, "api": "rtcpeerconnection",
            "media_kind": "", "channel_label": "",
            "pairing": pairing, "source": "webrtc-internals",
        })
        for upd in pc.get("updates", []):
            utype = str(upd.get("type", "")).lower()
            if any(h in utype for h in DC_HINTS):
                out.append({
                    "timestamp": upd.get("time"),
                    "host": host, "process": process,
                    "tab_origin": origin, "api": "datachannel_open",
                    "media_kind": "", "channel_label": str(upd.get("value", "")),
                    "pairing": pairing, "source": "webrtc-internals",
                })
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("dump", type=Path)
    p.add_argument("--host", default="ws01")
    p.add_argument("--process", default="msedge.exe")
    args = p.parse_args()

    dump = json.loads(args.dump.read_text(encoding="utf-8"))
    for rec in parse(dump, args.host, args.process):
        sys.stdout.write(json.dumps(rec) + "\n")


if __name__ == "__main__":
    main()
