"""Aggregate a pair of JSONL event logs into per-iteration metrics.

Usage:
    python analyze.py laptop.jsonl phone.jsonl
    python analyze.py --scenario B1 laptop.jsonl phone.jsonl

Reads the structured events emitted by the instrumented pairing pages,
groups by `iteration`, and prints a table + summary statistics suitable
for pasting into the paper's evaluation section.

No external deps — pure stdlib (json, statistics, argparse).
"""

import argparse
import json
import statistics
import sys
from pathlib import Path


def read_jsonl(path):
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def group_by_iteration(events):
    by_iter = {}
    for ev in events:
        i = ev.get("iteration", 0)
        by_iter.setdefault(i, []).append(ev)
    return by_iter


def per_iteration_metrics(laptop_iter_events, phone_iter_events):
    """Return a dict of metrics for one iteration. Missing data → None."""
    L = {ev["event"]: ev for ev in laptop_iter_events}
    P = {ev["event"]: ev for ev in phone_iter_events}

    # Was this iteration even started on each side?
    if "pairing_start" not in L:
        return None

    paired_laptop = "ice_connected" in L
    paired_phone = "ice_connected" in P
    paired = paired_laptop and paired_phone

    # Total handshake time from laptop perspective (pairing_start to
    # ice_connected). The lifecycle handler stamps totalMs into the
    # ice_connected payload.
    handshake_ms = L.get("ice_connected", {}).get("totalMs")

    # ICE gathering durations.
    ice_gather_laptop = L.get("ice_gathering_complete", {}).get("durationMs")
    ice_gather_phone = P.get("ice_gathering_complete", {}).get("durationMs")

    # Packet sizes — written when QR is rendered (laptop) and when the
    # answer is encoded (phone). These let us report the actual byte
    # counts per run, not just one anecdote.
    offer_bytes = L.get("qr_rendered", {}).get("packetSize")
    qr_chars = L.get("qr_rendered", {}).get("qrChars")
    answer_bytes = P.get("answer_encoded", {}).get("packetSize")
    answer_b64_chars = P.get("answer_encoded", {}).get("b64Chars")

    # How many audio chirps the phone sent before ICE connected.
    # answer_transmit fires once per chirp with an incrementing `attempt`.
    transmits = [
        ev for ev in phone_iter_events if ev["event"] == "answer_transmit"
    ]
    audio_attempts = max((ev.get("attempt", 0) for ev in transmits), default=0)

    # Transfer outcome (laptop sender perspective).
    transfer_ev = L.get("transfer_complete")
    transfer_ok = transfer_ev is not None
    transfer_kbps = transfer_ev.get("kbps") if transfer_ev else None
    transfer_size = transfer_ev.get("size") if transfer_ev else None
    transfer_ms = transfer_ev.get("durationMs") if transfer_ev else None

    # Failure mode (if any).
    failure = None
    if "iteration_failed" in L:
        failure = L["iteration_failed"].get("phase", "unknown")
    elif "ice_timeout" in L:
        failure = "ice_timeout"
    elif not paired:
        failure = "no_connect"
    elif not transfer_ok and paired:
        failure = "transfer_dropped"

    return {
        "paired": paired,
        "handshake_ms": handshake_ms,
        "ice_gather_laptop_ms": ice_gather_laptop,
        "ice_gather_phone_ms": ice_gather_phone,
        "offer_bytes": offer_bytes,
        "qr_chars": qr_chars,
        "answer_bytes": answer_bytes,
        "answer_b64_chars": answer_b64_chars,
        "audio_attempts": audio_attempts if paired else None,
        "transfer_ok": transfer_ok,
        "transfer_kbps": transfer_kbps,
        "transfer_size": transfer_size,
        "transfer_ms": transfer_ms,
        "failure": failure,
    }


def stats(values):
    """Return median, mean, P95, std for a list of numbers (None-safe)."""
    xs = [v for v in values if v is not None]
    if not xs:
        return None
    p95 = sorted(xs)[int(0.95 * (len(xs) - 1))]
    return {
        "n": len(xs),
        "median": statistics.median(xs),
        "mean": statistics.mean(xs),
        "p95": p95,
        "min": min(xs),
        "max": max(xs),
        "stdev": statistics.stdev(xs) if len(xs) > 1 else 0,
    }


def fmt(x, suffix=""):
    if x is None:
        return "—"
    if isinstance(x, float):
        return f"{x:.1f}{suffix}"
    return f"{x}{suffix}"


def print_per_iteration(rows):
    cols = [
        ("iter", lambda r: r["iter"]),
        ("paired", lambda r: "Y" if r["paired"] else "N"),
        ("hs_ms", lambda r: fmt(r["handshake_ms"])),
        ("offer_B", lambda r: fmt(r["offer_bytes"])),
        ("ans_B", lambda r: fmt(r["answer_bytes"])),
        ("audio_n", lambda r: fmt(r["audio_attempts"])),
        ("xfer_KBps", lambda r: fmt(r["transfer_kbps"])),
        ("xfer_ms", lambda r: fmt(r["transfer_ms"])),
        ("failure", lambda r: r["failure"] or ""),
    ]
    widths = [max(len(c[0]), 6) for c in cols]
    header = "  ".join(name.ljust(w) for (name, _), w in zip(cols, widths))
    print(header)
    print("-" * len(header))
    for r in rows:
        print("  ".join(getter(r).ljust(w) for (_, getter), w in zip(cols, widths)))


def print_summary(rows):
    print()
    print("=== Summary ===")
    n_total = len(rows)
    n_paired = sum(1 for r in rows if r["paired"])
    n_xfer = sum(1 for r in rows if r["transfer_ok"])
    print(f"Iterations:           {n_total}")
    print(f"Pairing success:      {n_paired}/{n_total} "
          f"({100*n_paired/n_total:.0f}%)" if n_total else "—")
    print(f"Transfer success:     {n_xfer}/{n_total} "
          f"({100*n_xfer/n_total:.0f}%)" if n_total else "—")
    print()

    metric_names = [
        ("handshake_ms", "Handshake (ms)"),
        ("ice_gather_laptop_ms", "ICE gather laptop (ms)"),
        ("ice_gather_phone_ms", "ICE gather phone (ms)"),
        ("offer_bytes", "Offer packet (B)"),
        ("answer_bytes", "Answer packet (B)"),
        ("audio_attempts", "Audio chirps until connect"),
        ("transfer_kbps", "Throughput (KB/s)"),
        ("transfer_ms", "Transfer wall time (ms)"),
    ]
    print(f"{'metric':<32}{'n':>4}{'median':>10}{'mean':>10}{'p95':>10}"
          f"{'min':>10}{'max':>10}{'stdev':>10}")
    print("-" * 96)
    for key, label in metric_names:
        s = stats([r[key] for r in rows])
        if s is None:
            print(f"{label:<32}  (no data)")
            continue
        print(f"{label:<32}{s['n']:>4}"
              f"{s['median']:>10.1f}{s['mean']:>10.1f}{s['p95']:>10.1f}"
              f"{s['min']:>10.1f}{s['max']:>10.1f}{s['stdev']:>10.1f}")

    # Failure breakdown
    failures = [r["failure"] for r in rows if r["failure"]]
    if failures:
        print()
        print("Failure modes:")
        from collections import Counter
        for mode, count in Counter(failures).most_common():
            print(f"  {mode}: {count}")


def fmt_size(nbytes):
    if nbytes is None:
        return "—"
    if nbytes < 1024 * 1024:
        return f"{nbytes // 1024} KB"
    return f"{nbytes / (1024 * 1024):g} MB"


def print_by_size(rows):
    """Throughput broken out per payload size — the sweep table.

    Each transfer_complete event carries its own `size`, so a single
    sweep log (multiple sizes back to back) buckets cleanly here without
    needing separate runs per size.
    """
    by_size = {}
    for r in rows:
        if r["transfer_size"] is None or r["transfer_kbps"] is None:
            continue
        by_size.setdefault(r["transfer_size"], []).append(r)

    if not by_size:
        return

    print()
    print("=== Throughput by payload size (steady-state sweep) ===")
    print(f"{'size':>8}{'n':>5}{'med KB/s':>11}{'mean KB/s':>11}"
          f"{'p95 KB/s':>11}{'stdev':>9}{'med ms':>9}")
    print("-" * 64)
    for size in sorted(by_size):
        bucket = by_size[size]
        kbps = stats([r["transfer_kbps"] for r in bucket])
        ms = stats([r["transfer_ms"] for r in bucket])
        print(f"{fmt_size(size):>8}{kbps['n']:>5}"
              f"{kbps['median']:>11.1f}{kbps['mean']:>11.1f}"
              f"{kbps['p95']:>11.1f}{kbps['stdev']:>9.1f}"
              f"{(ms['median'] if ms else 0):>9.1f}")
    print()
    print("Note: small payloads are dominated by DTLS/SCTP ramp-up; the "
          "largest size is the steady-state goodput figure for the paper.")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("laptop", type=Path, help="Laptop JSONL log")
    p.add_argument("phone", type=Path, help="Phone JSONL log")
    p.add_argument("--scenario", default=None, help="Scenario label for the header")
    p.add_argument("--csv", type=Path, default=None, help="Optional CSV output path")
    args = p.parse_args()

    laptop_events = read_jsonl(args.laptop)
    phone_events = read_jsonl(args.phone)

    laptop_by_iter = group_by_iteration(laptop_events)
    phone_by_iter = group_by_iteration(phone_events)

    iterations = sorted(set(laptop_by_iter) | set(phone_by_iter))
    # Skip iteration 0 — it's the "session_start" bucket before any
    # iteration_start has fired (manual runs land here).
    iterations = [i for i in iterations if i > 0]

    if not iterations:
        print("No iterations found. (Did you click 'Run' on the laptop's "
              "measurement panel? Manual single runs land in iteration 0 "
              "and are skipped by this script.)", file=sys.stderr)
        sys.exit(1)

    rows = []
    for i in iterations:
        L = laptop_by_iter.get(i, [])
        P = phone_by_iter.get(i, [])
        m = per_iteration_metrics(L, P)
        if m is None:
            continue
        m["iter"] = str(i)
        rows.append(m)

    if args.scenario:
        print(f"=== Scenario: {args.scenario} ===")
    print(f"Source: {args.laptop.name}, {args.phone.name}")
    print()
    print_per_iteration(rows)
    print_summary(rows)
    print_by_size(rows)

    if args.csv:
        import csv
        keys = list(rows[0].keys()) if rows else []
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            w.writerows(rows)
        print(f"\nPer-iteration CSV written to {args.csv}")


if __name__ == "__main__":
    main()
