

## Implementation update after patent-scope review

The repository now contains a simulation-only `TrustedController` model under `security/trusted_controller.py`. It models separate `known_attack` and `adaptive_anomaly` evidence, HMAC authentication, payload hashing, freshness checks, replay/out-of-order rejection, controller states, optional quorum configuration, and authenticated monotonic containment receipts. The controller is deliberately labeled as a simulation scaffold; physical enforcement must be implemented in the ESP32 or dedicated security MCU.

The compact 480×320 M4 dashboard in `gui/dashboard.py` now displays controller state, relay acknowledgment, tamper state, key state, primary-power status, independent-signal count, receipt verification, quorum configuration, and recovery status. The hardware simulator state API now exposes matching telemetry fields for controller, signals, quorum, receipt, power, and recovery.

The current simulation configures quorum as `NOT_CONFIGURED` rather than fabricating peer votes. This is honest coverage: the two-signal policy and receipt verification are modeled, while authenticated multi-node quorum, hardware-backed key invalidation, dedicated hold-up power, and ESP32-side enforcement remain team-owned implementation and hardware-validation tasks.
