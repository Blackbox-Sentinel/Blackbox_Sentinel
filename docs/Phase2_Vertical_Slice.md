# Phase 2 Software Vertical Slice

## Scope

Phase 2 connects the software modules into one repeatable digital-twin demonstration:

> **M2 transport → M3 authenticated evidence and quorum → containment receipt → M4 dashboard telemetry**

This slice is intentionally hardware-independent. It does not claim that the Raspberry Pi can enforce a physical relay decision or that the ESP32 has already implemented hardware-backed key invalidation, tamper enforcement, or hold-up power.

## Normalized telemetry contract

M2 and M3 may retain their internal classes, but the M4 dashboard consumes `NormalizedTelemetry` from `integration/telemetry.py`. The object is JSON-serializable and includes:

- event identity, event type, status, timestamp, source, and link state;
- controller state, incident ID, packet and alert counts;
- separate evidence signals with source, type, authentication, freshness, and confidence;
- quorum state, threshold, received count, and vote details;
- decision, relay requested/acknowledged/verified/state;
- tamper, key, power, receipt, SMS, and recovery state;
- rejection reason, evidence digest, model profile, and operator-safe notes.

The allowed event statuses are `normal`, `pending`, `approved`, `rejected`, `replay`, `stale`, `conflict`, `receipt`, and `recovery`.

## Run the software slice

From the repository root:

```bash
python3 integration/phase2_vertical_slice.py \
  --output m3-ml-ledger/data/phase2_telemetry.jsonl
```

For a paced demonstration, add a delay between events:

```bash
python3 integration/phase2_vertical_slice.py \
  --output m3-ml-ledger/data/phase2_telemetry.jsonl \
  --sleep 1
```

The runner emits nine events covering calibration, normal traffic, one-signal pending, approved two-signal containment, replay rejection, stale rejection, quorum conflict, receipt audit, and recovery required. It writes the normalized event stream plus simulation ledger and counter files beside the selected output.

In a second terminal, start the 480×320 M4 dashboard and point it to the same file:

```bash
python3 gui/dashboard.py \
  --telemetry-file m3-ml-ledger/data/phase2_telemetry.jsonl
```

The dashboard tails the JSON Lines file and shows the latest normalized state. The `ATTACK` button is intentionally informational in telemetry mode; the vertical-slice runner owns event generation so M4 cannot silently create a separate local decision path.

## Expected demonstration sequence

| Stage | Dashboard expectation |
|---|---|
| Calibration | `ARMED`, normal status, model profile shown |
| Normal traffic | Healthy link, connected relay, no alert |
| One signal | `ALERT_PENDING`, one authenticated/fresh signal, relay remains connected |
| Two signals and quorum | `APPROVED`, `ISOLATED`, receipt valid, mock SMS sent |
| Replay | `REPLAY`, rejection reason `REPLAYED`, prior containment remains visible |
| Stale event | `STALE`, rejection reason `STALE` |
| Mixed votes | `CONFLICT`, no new containment approval |
| Receipt audit | Receipt status and sequence visible |
| Recovery | `RECOVERY`, key/power limitations visible, authentication required |

## Validation

Run the focused Phase 2 and existing security tests:

```bash
python3 -m pytest -q \
  tests/test_phase2_vertical_slice.py \
  tests/test_postmeeting_security_flow.py \
  tests/test_m3_security_contracts.py \
  tests/test_m4_pin_security.py
```

The vertical-slice test confirms that the normalized event stream includes all required statuses and that the approved event includes two signals, an approved quorum, an isolated simulated relay, and a valid receipt.

## Team ownership

M2 owns the eventual real transport and the second independently authenticated signal. M3 owns the evidence decision, quorum state, ledger binding, and receipt contract. M4 owns the dashboard view, safe operator recovery presentation, and display of unknown/rejected/conflicting states. M1 owns binding the same controller/receipt contract to the ESP32 and validating physical relay, tamper, key, and power behavior.

Until M1 completes that hardware validation, reports and presentations must use the wording **software simulation**, **simulated relay**, and **simulation-only key/power behavior**.
