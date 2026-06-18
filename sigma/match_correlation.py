"""Reference matcher for rule.yml's temporal correlation (§8.3 detection rate).

Implements exactly the published rule logic so the detection-rate result is
reproducible without a full Sigma backend:

  fires  <=>  getusermedia(media_kind=audio)        [F1]
              AND datachannel_open on a non-allowlisted tab_origin   [F3 ∧ F4]
              within `timespan` (default 2 min), grouped by host+process.

Input is the browser/webrtc_api NDJSON produced by jsonl_to_webrtc_api.py or
parse_webrtc_internals.py. Each record's `pairing` field defines one pairing;
the matcher evaluates the correlation per pairing and reports the firing rate.

The VoIP origin allowlist mirrors rule.yml / allowlist.yml — keep in sync.

Usage:
    python jsonl_to_webrtc_api.py evidence/.../laptop.jsonl | python match_correlation.py
    python match_correlation.py events.ndjson [--timespan-ms 120000]

Stdlib only.
"""

import argparse
import fnmatch
import json
import sys
from pathlib import Path

# Mirror of rule.yml `voip_origin_allowlist` / allowlist.yml. Keep in sync.
VOIP_ALLOWLIST = [
    "https://teams.microsoft.com",
    "https://*.teams.microsoft.com",
    "https://meet.google.com",
    "https://*.zoom.us",
    "https://app.zoom.us",
    "https://whereby.com",
    "https://*.whereby.com",
]


def is_allowlisted(origin):
    return any(fnmatch.fnmatch(origin, pat) for pat in VOIP_ALLOWLIST)


def read_events(paths):
    if paths:
        lines = []
        for p in paths:
            lines += Path(p).read_text(encoding="utf-8").splitlines()
    else:
        lines = sys.stdin.read().splitlines()
    return [json.loads(ln) for ln in lines if ln.strip()]


def evaluate(events, timespan_ms):
    by_pairing = {}
    for ev in events:
        by_pairing.setdefault(ev.get("pairing", "?"), []).append(ev)

    results = []
    for pairing, evs in by_pairing.items():
        f1 = [e for e in evs if e["api"] == "getusermedia" and e.get("media_kind") == "audio"]
        f3 = [e for e in evs if e["api"] == "datachannel_open" and not is_allowlisted(e.get("tab_origin", ""))]

        fired = False
        # Same host+process and within the temporal window.
        for a in f1:
            for d in f3:
                if a["host"] != d["host"] or a["process"] != d["process"]:
                    continue
                ta, td = a.get("timestamp"), d.get("timestamp")
                if ta is None or td is None:
                    fired = True  # no timestamps -> treat as same pairing window
                elif abs(td - ta) <= timespan_ms:
                    fired = True
        results.append({
            "pairing": pairing,
            "f1_getusermedia_audio": bool(f1),
            "f3_datachannel_nonvoip": bool(f3),
            "origins": sorted({e.get("tab_origin", "") for e in f3}) or
                       sorted({e.get("tab_origin", "") for e in f1}),
            "fired": fired,
        })
    return results


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("events", nargs="*", help="NDJSON files (default: stdin)")
    p.add_argument("--timespan-ms", type=int, default=120000)
    args = p.parse_args()

    results = evaluate(read_events(args.events), args.timespan_ms)
    results.sort(key=lambda r: r["pairing"])

    fired = sum(1 for r in results if r["fired"])
    total = len(results)
    print(f"{'pairing':<42}{'F1':>4}{'F3':>4}{'fired':>7}  origin")
    print("-" * 88)
    for r in results:
        print(f"{r['pairing']:<42}"
              f"{'Y' if r['f1_getusermedia_audio'] else 'N':>4}"
              f"{'Y' if r['f3_datachannel_nonvoip'] else 'N':>4}"
              f"{'YES' if r['fired'] else 'no':>7}  {','.join(r['origins'])}")
    print("-" * 88)
    rate = (100 * fired / total) if total else 0
    print(f"Detection rate: {fired}/{total} pairings fired ({rate:.0f}%)")


if __name__ == "__main__":
    main()
