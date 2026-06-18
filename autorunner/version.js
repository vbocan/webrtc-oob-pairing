// Single source of truth for the page version.
//
// Bump on any change you want to confirm is actually loaded in the
// browser. Both pair pages display this in their header and stamp it
// into the JSONL log's session_start event, so a mismatched
// laptop/phone pair is visible in the data too.
//
// Convention:
//   patch  — bug fix only (0.2.0 → 0.2.1)
//   minor  — new feature, schema change to JSONL (0.2.1 → 0.3.0)
//   major  — incompatible protocol change (0.3.0 → 1.0.0)

// 0.4.1 — libraries vendored under ./vendor/ (ggwave@0.4.0, qrcode@1.5.4,
// qwbp@0.1.0, jsqr@1.4.0; identical versions, served locally) so the pages
// load with zero external DNS. No functional or schema change from 0.4.0;
// results remain comparable. Resolves the A8a load-time-DNS caveat.
export const VERSION = '0.4.1';
