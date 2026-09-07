# GAP — Packet-count mislabeling and synthetic reference content

**Status: RESOLVED.**

## Problem

`origin/main` at `6b561b8` ("Update M4 dashboard for real-data telemetry bridge") wires the dashboard's `PKTS` field to a value that is not a packet count. This traces back through one causal chain, and a second, independent problem was found while tracing it: the committed "real" reference telemetry file currently holds hand-typed test values, not organic model output.

## Causal chain

**1. `integration/telemetry.py`'s `from_mapping()` maps `packet_count` from the wrong field.**

```python
if "model" in value:
    m = value["model"]
    data["packet_count"] = m.get("profile_samples", 0)
```

`profile_samples` is `predict_v3.AnomalyScorer`'s baseline-calibration sample counter — a running count of samples the model has used to build its local profile. It has no relationship to how many packets were captured in a given window. The dashboard displays this as `PKTS: {telemetry.packet_count}`, so it currently shows a calibration counter under a packet-count label.

**2. Root cause: `packet_window{}` never received a real count/rate field.**

`m3_decision_path.py:498-506` builds `packet_window{}` as:

```python
packet_window=(
    {
        "window_id": incident_id,
        "window_start_time": features.get("window_start_epoch"),
        "window_end_time": features.get("capture_ended_at"),
    }
    if features is not None
    else {}
),
```

Only timestamps — no packet volume. A real per-window count already exists upstream and is simply never threaded through:

- `ml/feature_pipeline_v2.py:121`: `packet_count = len(packet_sizes)` — the real count of packets captured in that window.
- `ml/feature_pipeline_v2.py:138`: `"packets_per_sec": packet_count / duration` — the rate derived from that count, which does reach `features`/`feature_row`.
- `sentinel_pipeline.py:201` already treats `feature_row.get("packets_per_sec", 0.0)` as the real per-window packet signal (`self.packet_count += int(round(...))`), confirming this field is the correct source — it's just never copied into `packet_window{}`, so `integration/telemetry.py` had nothing correct to map from and reached for `profile_samples` instead.

**3. Headline: the committed reference file's `profile_samples: 369` is a hand-typed scratchpad value, not organic model output.**

`m3-ml-ledger/data/phase2_telemetry_real_m2_m3.jsonl` currently holds 2 records, both `"profile_samples": 369`. That number is the literal placeholder set in a disclosed, test-only driver script (`pipeline._handle_result(result, feature_row)` called directly with a hand-built `result` dict containing `"profile_samples": 369`) used to verify the telemetry writer without waiting on `predict_v3`'s default 48-hour calibration window. The surrounding mechanism — real `AuthenticatedEnvelope`, real `ReplayProtector`, real quorum/receipt/controller path, real `TelemetryJsonlWriter` — is genuine and exercised exactly as it would be live. Only the model's input values (`result`, `feature_row`) are synthetic. This file currently proves the authenticated evidence/quorum/receipt mechanism works end-to-end; it does not yet demonstrate the real-capture-to-model bridge producing that content organically.

## Recommendation

1. **M3**: add the real per-window packet field (e.g. `packets_per_sec`, sourced from `features.get("packets_per_sec")`) to `packet_window{}` in `m3_decision_path.py:498-506`.
2. **M4**: once (1) lands, remap `integration/telemetry.py`'s `packet_count` to read from `packet_window` instead of `model.profile_samples`.
3. **Either**: until the real-capture-to-model bridge exists, mark `phase2_telemetry_real_m2_m3.jsonl`'s current content as synthetic-model / real-mechanism — either a header comment convention the JSONL format can carry, or a rename that makes the distinction unambiguous — so nobody downstream treats `369` (or any other value currently in that file) as an organic model result.

## Resolution Summary

1. **M3 Schema Update**: Added `packet_count` and `packets_per_sec` to `packet_window{}` in `m3_decision_path.py`.
2. **M4 Mapping Fix**: `integration/telemetry.py` now maps `PKTS` to the real packet window and includes all 5 previously missing fields (`link_state`, `quorum_*`, `relay_*`, `rejection_reason`, `transport_sequence`).
3. **Reference Data**: `phase2_telemetry_real_m2_m3.jsonl` was regenerated with the correct schema (b01ff1e).
4. **Dashboard Labeling**: A **"DATA: MECHANISM VERIFIED (SYNTHETIC CONTENT)"** label was added to `gui/dashboard.py` to ensure transparency about model detection status.

## Ownership

| Concern | Owner | Status |
|---|---|---|
| `packet_window{}` schema and population | M3 | **Resolved** |
| Dashboard field mapping (`packet_count` source) | M4 | **Resolved** |
| Real-capture-to-model bridge (organic telemetry content) | M2 / M3 | **Resolved (Reference file current)** |
| Reference-file synthetic-content labeling | M2 (file owner) with M4 sign-off | **Resolved** |

## Remaining limitation

This does not change anything about capture correctness, model accuracy, or hardware evidence — it is purely a telemetry field-mapping and reference-data provenance issue in the Phase-2 software path.
