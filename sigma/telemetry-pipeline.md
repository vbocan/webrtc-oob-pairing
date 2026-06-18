# Telemetry pipeline for the detection rule

This document answers the question a SOC engineer asks before deploying
the rule in [`rule.yml`](rule.yml): *what has to be logged for this rule
to fire, and can I actually get that telemetry today?* It is written to
the Option-B scope decision in the accompanying paper — we validate the
rule's **detection rate** against reproducible browser-API telemetry and
argue its false-positive resistance structurally, rather than running a
live multi-platform benchmark.

The honest headline, stated up front so the paper does not overclaim:

> **No stock endpoint telemetry source logs `getUserMedia` and
> `RTCPeerConnection` API calls today.** Sysmon does not. The rule
> therefore targets an *abstract browser-API event schema* (defined
> below). We demonstrate that schema is populatable from two sources any
> reader can reproduce, and we document which production EDR/browser
> telemetry supplies each field today and which fields still require
> vendor instrumentation. The latter is an explicit call to action in
> §8 and the mitigation taxonomy.

---

## 1. The four observable facts the rule keys on

The characterised surface is identifiable by the **co-occurrence**, in a
single browser tab, of four facts within a short window:

| # | Fact | Browser API | Artifact event (`event-log.js`) |
|---|---|---|---|
| F1 | Microphone capture starts | `navigator.mediaDevices.getUserMedia({audio})` | `mic_listening` |
| F2 | A peer connection is created | `new RTCPeerConnection()` / `createOffer` | `offer_created` |
| F3 | A **data** channel opens (not a media track) | `createDataChannel` → `datachannel.onopen` | `datachannel_open` |
| F4 | The page origin is not an approved VoIP origin | document origin | `session_start.url` / page origin |

A legitimate collaboration session populates F1 and F2 but, crucially,
negotiates **media tracks** (`m=audio`/`m=video`) rather than a
DataChannel, and runs on an **allowlisted origin** (F4 false). The
surface populates F1+F2+**F3** on a **non-allowlisted origin**. The rule
is the conjunction; see [`rule.yml`](rule.yml) for the exact logic and
[`allowlist.yml`](allowlist.yml) for F4.

> The discriminator that does the real work is **F3 vs media-track**:
> "microphone + peer connection" alone is every video call; "microphone
> + peer connection + DataChannel + unknown origin + no outbound media
> track" is the surface. This is why the FP argument in §8.3 is
> structural rather than threshold-tuned.

---

## 2. Abstract event schema (what the rule consumes)

The rule is written against a vendor-neutral logsource we name
`browser/webrtc_api`. Each event is one record with at least:

```
timestamp        ISO-8601, ms precision
host             workstation identifier
process          browser image (msedge.exe, chrome.exe, ...)
tab_origin       https origin of the initiating document
api              one of: getusermedia | rtcpeerconnection | datachannel_open | track_added
media_kind       for getusermedia/track_added: audio | video | (empty)
channel_label    for datachannel_open: the RTCDataChannel.label (may be empty)
```

This is the minimum schema that makes F1–F4 expressible. Mapping it onto
a concrete backend (the field renames, the table/index names) is a
deployment step, documented per-source in §4.

---

## 3. Sources that populate the schema **today** (reproducible)

These two are reproducible by any reader on a single laptop, with no
enterprise EDR licence. They are what we use for the detection-rate
measurement in §8.3.

### 3.1 `chrome://webrtc-internals` event dump (primary, reproducible)

Chromium-family browsers expose a live, per-tab log of every WebRTC API
call at `chrome://webrtc-internals` (Edge: `edge://webrtc-internals`).
The page's **"Create Dump"** button exports a JSON file containing, per
`RTCPeerConnection`:

- `getUserMedia` calls with the requested constraints (→ F1, `media_kind`).
- The `RTCPeerConnection` constructor and `createDataChannel` calls,
  each timestamped (→ F2, F3, `channel_label`).
- The SDP of every offer/answer, from which media-track-vs-DataChannel
  (`m=application` for SCTP, no `m=audio`/`m=video`) is read directly.
- The document origin is not in the dump; it is recovered from the
  concurrent browser history / the page URL (→ F4).

A small parser (`parse_webrtc_internals.py`, to accompany the rule)
projects a dump onto the §2 schema. This source is **ground truth** for
the API sequence and is fully reproducible — it is part of the shipping
browser, requires no policy, and works for both our artifact and any
third-party WebRTC site, which is what makes the structural FP argument
checkable by a reviewer.

### 3.2 The artifact's own instrumentation (`event-log.js`) (corroborating)

The reference artifact emits the JSONL already in `evidence/` with
`mic_listening`, `offer_created`, `datachannel_open`, `selected_pair`,
`transfer_start`. These map one-to-one onto F1–F3 (§1 table) and carry
the document URL in `session_start`. We use these logs as the
corroborating second source for the detection-rate measurement so the
result does not depend on a single instrumentation path. They are *not*
a production telemetry source — they exist because the page instruments
itself — but they prove the four facts are jointly emitted in every
successful pairing already captured (B1, E1, and E2 once run).

---

## 4. Production sources (what an enterprise would actually wire up)

These are the deployment targets named in §8.2 of the plan. Each row
states honestly what it supplies today.

| Source | Supplies F1 (`getUserMedia`)? | Supplies F2/F3 (PC/DataChannel)? | Supplies F4 (origin)? | Notes |
|---|---|---|---|---|
| **Sysmon (stock)** | No | No | No | Process/network/file only; no browser-API surface. Establishes the gap. |
| **Chrome/Edge Enterprise WebRTC event-log collection** (`WebRtcEventLogCollectionAllowed=1`) | Partial | Yes (PC events, SDP) | Indirect | Collected to the admin console; logs are connection/SDP-oriented. SDP exposes DataChannel vs media; origin via managed-browser reporting. Pipeline to SIEM is org-specific. |
| **Microsoft Defender for Endpoint** (`DeviceEvents`) | No (no documented browser-API event) | No | Partial (page URL via web-content events) | Browser-API-level instrumentation is **not** generally queryable today. This is the principal call-to-action for vendors. |
| **CrowdStrike Falcon** (browser/script visibility) | Partial | Partial | Partial | Coverage is product-tier dependent and does not expose the full F1–F3 sequence as discrete events today. |
| **Managed-browser extension / CDP collector** (org-deployed) | Yes | Yes | Yes | A WebExtension or a Chrome DevTools Protocol agent can observe all four facts and ship them in the §2 schema. Highest fidelity; requires the org to deploy and manage it. The deployable-today recommendation for orgs that want this rule live. |

**Reading of the table for the paper.** The rule is *operationally
meaningful today* in two deployment shapes: (a) an org that runs a
managed-browser extension / CDP collector (last row), which supplies the
full schema directly; or (b) an org that ships Chrome/Edge Enterprise
WebRTC event logs to its SIEM and accepts SDP-level discrimination of
DataChannel-vs-media. For the common Sysmon-only or stock-Defender SOC,
the rule is a **specification plus a vendor call-to-action**: the
selection logic is correct and deployable the moment the telemetry
exists, and §7/§8 name exactly which instrumentation closes the gap.

---

## 5. Field mapping (abstract → backends), for the appendix

| §2 field | webrtc-internals dump | Defender `DeviceEvents` (when available) | managed-extension collector |
|---|---|---|---|
| `timestamp` | event `time` | `Timestamp` | `ts` |
| `host` | (host of capture) | `DeviceName` | `host` |
| `process` | (browser) | `InitiatingProcessFileName` | `process` |
| `tab_origin` | recovered from URL | `RemoteUrl` / `AdditionalFields` | `origin` |
| `api` | event `type` | `ActionType` (proposed) | `api` |
| `media_kind` | `getUserMedia` constraints / SDP `m=` | `AdditionalFields` (proposed) | `mediaKind` |
| `channel_label` | `createDataChannel` args | `AdditionalFields` (proposed) | `label` |

"(proposed)" marks fields a vendor would need to add — the call to
action. The webrtc-internals and managed-extension columns are
populatable today; that is the reproducibility floor the paper stands on.

---

## 6. Detection-rate measurement procedure (§8.3)

1. For each captured pairing in `evidence/{baseline,tls-proxy,dns-denied}`,
   take the workstation-side source: either a `chrome://webrtc-internals`
   dump captured during the run (preferred) or the artifact JSONL
   already present (corroborating).
2. Project onto the §2 schema with the accompanying parser.
3. Run [`rule.yml`](rule.yml) (via `sigma convert` to a query, or the
   reference matcher) over the projected events.
4. Report the fraction of pairings on which the temporal correlation
   fires. Target ≥ 95 % (we expect 100 %, since every successful pairing
   emits F1→F2→F3 by construction; the only way to miss is a telemetry
   gap, which is what this measurement surfaces).

The measurement therefore validates *that the telemetry carries the
signature*, which is the honest claim — not that an arbitrary EDR will
catch it regardless of instrumentation.
