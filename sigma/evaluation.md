# Detection-rule evaluation

Evaluation of [`rule.yml`](rule.yml) under the Option-B scope
(the accompanying paper): a **measured detection rate** against our own
pairing telemetry, and a **structural false-positive argument** in place
of the deferred multi-platform benchmark.

## 1. Detection rate (measured)

### Method

For each successful pairing captured in `evidence/`, project the
workstation-side telemetry onto the `browser/webrtc_api` schema
(`telemetry-pipeline.md` §2) from either source:

- **Primary:** a `chrome://webrtc-internals` "Create Dump" taken during
  the run (the reproducible production-equivalent source).
- **Corroborating:** the artifact's JSONL already in `evidence/`
  (`mic_listening` → F1, `datachannel_open` → F3, `session_start.url` →
  F4), which exists for every captured pairing.

Then evaluate the temporal correlation (`getUserMedia(audio)` near a
non-VoIP-origin `datachannel_open`, within 2 min, per host+process).

### Inputs

| Scenario | Pairings | Telemetry present | Source |
|---|---|---|---|
| B1 baseline | 10/10 | JSONL ✓ (`evidence/baseline`) | corroborating |
| E1 TLS proxy | 10/10 | JSONL ✓ (`evidence/tls-proxy`) | corroborating |
| E2 DNS denied | 5/5 | JSONL ✓ (`evidence/dns-denied`) + webrtc-internals dump | both |

### Result

**The rule fired on 25 / 25 successful pairings (100 %): B1 10/10, E1
10/10, E2 5/5.** Every pairing's telemetry carried F1 (`getUserMedia`
audio) and F3 (`datachannel_open`) on the artifact's non-allowlisted
origin (`https://localhost:8000`), correlatable within the two-minute
window, so the temporal correlation matched in each case. The origin
clause (F4) is anchored to a production-equivalent source by the
`chrome://webrtc-internals` dump in `evidence/sigma-telemetry/`, whose
`getUserMedia` record carries `origin: https://localhost:8000` — the same
non-allowlisted origin. (The dump's `PeerConnections` block is empty
because webrtc-internals drops a connection once it closes and the
auto-runner closes each pairing immediately after transfer; F2/F3 for the
rate are therefore taken from the artifact JSONL, which records
`offer_created` and `datachannel_open` for every pairing. This is a
capture-timing artefact, not a logic gap.)

Reproduce with:

```sh
cd sigma
python jsonl_to_webrtc_api.py \
  ../evidence/baseline/qr-webrtc-laptop-*.jsonl \
  ../evidence/tls-proxy/qr-webrtc-laptop-*.jsonl \
  ../evidence/dns-denied/laptop.jsonl | python match_correlation.py
python parse_webrtc_internals.py ../evidence/sigma-telemetry/webrtc_internals_dump.txt
```

The detection rate is bounded only by telemetry completeness, which is
exactly what this measurement establishes — that the four facts are
jointly observable in captured telemetry. A miss would indicate a
telemetry gap, not a logic gap; none occurred across the 25 pairings.

The honest claim is therefore: *given telemetry that carries the four
facts (which both sources do), the rule detects the surface on 100 % of
successful pairings.* The §8 prose states this precisely and does not
generalise to "any EDR will catch it" — that depends on the deployment's
instrumentation (`telemetry-pipeline.md` §4).

## 2. False-positive resistance (structural argument)

The empirical multi-platform benchmark (80 Teams/Meet/Zoom/Whereby
sessions) is **future work** (scope decision). The rule's FP resistance
is instead argued from its selection logic. A legitimate session must
satisfy *all* of the rule's clauses to produce a false alarm:

| Rule clause | Legitimate Teams/Meet/Zoom/Whereby session | Match? |
|---|---|---|
| F1 `getUserMedia(audio)` | Yes — a call captures the mic | ✓ |
| F3 `RTCDataChannel` open | Calls negotiate **media tracks** (`m=audio`/`m=video`); DataChannels, when used, are auxiliary | usually ✗ |
| F4 non-VoIP origin | Runs on an allowlisted origin (`allowlist.yml`) | ✗ |
| Temporal: F1 ∧ F3 within 2 min, same process | Requires F3 to also hold | usually ✗ |

A benign session fails at **F4** (wrong origin) and typically also at
**F3** (media track, not DataChannel). Both independently prevent a
match. The conjunction is what makes the rule specific: "microphone +
peer connection" alone is every video call and would be useless; the
rule does not alert on that.

### Residual risk (stated honestly)

The rule *would* match a browser-based WebRTC application that (a) opens
a DataChannel, (b) from an origin not in the allowlist, (c) while
capturing the microphone, within the window. Such applications exist
(some collaboration and file-sharing web apps use DataChannels). The
operator resolves these by adding the origin to `allowlist.yml` — the
same tuning loop every Sigma rule has. The paper states this residual
risk plainly and notes that quantifying its real-world rate is the
purpose of the deferred benchmark; the structural argument establishes
that the rate is bounded by "non-allowlisted DataChannel-using web apps
that also use the mic," a narrow population, not "all WebRTC traffic."

## 3. Reproducing the evaluation

```sh
# 1. Project a capture onto the webrtc_api schema:
python parse_webrtc_internals.py dump.json > events.ndjson       # webrtc-internals source
# or, from the artifact JSONL already in evidence/:
python jsonl_to_webrtc_api.py evidence/baseline/qr-webrtc-laptop-*.jsonl > events.ndjson

# 2. Evaluate rule.yml's temporal correlation and count firings per pairing
#    (reference matcher; or `sigma convert -t <backend> rule.yml` for a SIEM):
python match_correlation.py events.ndjson
```

The three parsers/matcher ship alongside this file:
`jsonl_to_webrtc_api.py` and `parse_webrtc_internals.py` project a capture
onto the §2 schema; `match_correlation.py` is a stdlib reference
implementation of `rule.yml`'s temporal correlation (F1 ∧ F3-on-non-VoIP
within 2 min, grouped by host+process), so the 25/25 result above
reproduces without a Sigma backend. Its origin allowlist mirrors
`rule.yml` / `allowlist.yml`.
