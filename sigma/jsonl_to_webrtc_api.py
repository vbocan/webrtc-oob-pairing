"""Project the artifact's JSONL event log onto the browser/webrtc_api schema.

Corroborating telemetry source for the §8.3 detection-rate measurement
(telemetry-pipeline.md §3.2). Reads one or more laptop-side JSONL logs and
emits one NDJSON record per relevant API event, mapping:

    mic_listening    -> api=getusermedia,     media_kind=audio   (F1)
    offer_created    -> api=rtcpeerconnection                    (F2)
    datachannel_open -> api=datachannel_open                     (F3)

Origin (F4) is not present in the artifact JSONL (session_start carries no
url), so it is supplied via --origin; it defaults to the artifact's serving
origin https://localhost:8000, which the concurrent webrtc-internals dump
confirms (its getUserMedia.origin field). Each record carries `pairing`
(the iteration index) so the matcher can report per-pairing firings.

Usage:
    python jsonl_to_webrtc_api.py LAPTOP.jsonl [LAPTOP2.jsonl ...] \
        [--origin https://localhost:8000] [--host ws01] [--process msedge.exe] \
        > events.ndjson

Stdlib only.
"""

import argparse
import json
import sys
from pathlib import Path

EVENT_MAP = {
    "mic_listening":    {"api": "getusermedia",     "media_kind": "audio"},
    "offer_created":    {"api": "rtcpeerconnection", "media_kind": ""},
    "datachannel_open": {"api": "datachannel_open",  "media_kind": ""},
}


def project(path, origin, host, process):
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            ev = json.loads(line)
            mapped = EVENT_MAP.get(ev.get("event"))
            if not mapped:
                continue
            out.append({
                "timestamp": ev.get("t"),          # ms from session start
                "host": host,
                "process": process,
                "tab_origin": origin,
                "api": mapped["api"],
                "media_kind": mapped["media_kind"],
                "channel_label": "",
                "pairing": f"{Path(path).stem}#{ev.get('iteration', 0)}",
                "source": "artifact-jsonl",
            })
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("logs", nargs="+", type=Path)
    p.add_argument("--origin", default="https://localhost:8000")
    p.add_argument("--host", default="ws01")
    p.add_argument("--process", default="msedge.exe")
    args = p.parse_args()

    for path in args.logs:
        for rec in project(path, args.origin, args.host, args.process):
            sys.stdout.write(json.dumps(rec) + "\n")


if __name__ == "__main__":
    main()
