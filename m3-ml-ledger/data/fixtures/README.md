# M3 Mock Telemetry Fixtures

`m3_mock_telemetry_approved.json` is a **simulation-only** normalized telemetry event for M4 dashboard development while M2-2 and M2-3 are still being implemented.

The fixture was generated through the real M3 decision path using two simulated authenticated signals, an approved simulated quorum, an Ed25519 signed receipt, simulated-controller acceptance, and a valid ledger binding. It is not real M2 output, not hardware evidence, and must not be used to claim physical relay enforcement.

The M4 dashboard may use this file to develop the accepted/isolated view. The dashboard should also create separate fixtures for pending evidence, quorum conflict, stale/replayed envelopes, receipt failure, controller rejection, and recovery. When M2-2 and M2-3 are complete, replace the mock input with live `DecisionPathResult.telemetry` while keeping the same schema version and field names.
