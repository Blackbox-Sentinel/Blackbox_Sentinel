# M4 — GUI and Venture Module

> **Owner:** M4 GUI/Venture Lead
>
> **Canonical touchscreen demo:** `gui/dashboard.py`
>
> **Mode:** Simulation first (`SENTINEL_HARDWARE=sim`)

## Purpose

M4 owns the dashboard, operator recovery workflow, and venture-facing project material. The canonical hardware-facing interface is a compact **480×320 PyQt6 dashboard** designed for the Raspberry Pi 3.5-inch touchscreen. The larger Tkinter dashboard under `m4-gui-venture/src/app.py` remains useful for desktop development and detailed simulation.

The new patent-scope requirements make M4 a telemetry and evidence-view layer. The GUI must display controller-reported state and must never create or bypass the trusted security decision. Values that are unknown, stale, rejected, conflicting, or not configured must be shown explicitly rather than represented as successful.

## Quick start

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 gui/dashboard.py
```

For the larger desktop simulation dashboard:

```bash
python3 m4-gui-venture/src/app.py
```

On Ubuntu/Debian, Tkinter may need to be installed separately:

```bash
sudo apt-get install python3-tk
```

The default controlled simulation PIN is `1234`. It can be overridden for local testing with `SENTINEL_PIN`, but this is not a production authentication design.

## Touchscreen target

The current target is a 3.5-inch Raspberry Pi touchscreen with a default working layout of **480×320**. Confirm the exact vendor driver, framebuffer/device path, rotation, touch calibration, and reported resolution before hardware bring-up. The setup script avoids forcing 800×480 HDMI timings because SPI/GPIO touchscreen modules use vendor-specific display drivers.

## Patent-scope evidence visible in the touchscreen dashboard

The compact dashboard displays the following simulation evidence:

| Evidence | Display behavior |
|---|---|
| Controller state | Shows `ARMED`, `ISOLATED`, or `TAMPERED` instead of only a local GUI lock flag |
| Relay state | Separates relay isolation/restoration status and controller acknowledgment |
| Independent signals | Shows known-attack and adaptive-anomaly evidence as a two-signal decision |
| Quorum | Shows `N/A` when multi-node quorum is not configured; it must not fabricate votes |
| Receipt | Shows receipt ID and cryptographic verification status when available |
| Tamper/key state | Shows secure/breached and valid/invalidated states without exposing key material |
| Recovery | Requires the exact configured PIN and reports rejected recovery attempts |

The current simulator backend also exposes normalized controller, signal, quorum, receipt, power, and recovery fields through `/api/state` for the browser simulator and future shared event integration.

## Phase 2 and patent-scope event contract

M2/M3 should provide normalized events containing at least:

```json
{
  "event_type": "containment_decision",
  "controller_state": "ISOLATED",
  "signals": [
    {"type": "known_attack", "source": "m3-known-detector", "auth": "VALID", "freshness": "FRESH"},
    {"type": "adaptive_anomaly", "source": "m3-adaptive-profile", "auth": "VALID", "freshness": "FRESH"}
  ],
  "relay_requested": "ISOLATED",
  "relay_acknowledged": "ISOLATED",
  "quorum": {"required": 0, "received": 0, "decision": "NOT_CONFIGURED"},
  "receipt": {"id": "receipt-00000001", "counter": 1, "verification": "VALID"},
  "key_state": "VALID",
  "power_state": "PRIMARY",
  "recovery_state": "LOCKED"
}
```

The real hardware implementation must authenticate these fields at the controller boundary. The Phase 2 Python controller is a simulation scaffold and is not a substitute for ESP32/security-MCU enforcement.

## Current checklist

- [x] Compact 480×320 touchscreen dashboard.
- [x] Relay, tamper, key, power, controller, signal, quorum, receipt, and recovery indicators.
- [x] Two independent authenticated-signal simulation policy.
- [x] Anti-replay, freshness, and payload-integrity checks in the simulation controller.
- [x] Monotonic containment receipt generation and verification in the simulation controller.
- [x] Wrong-PIN rejection and exact-PIN recovery workflow.
- [x] Hardware simulator state fields for final M4 visibility.
- [x] Automated tests for controller policy and receipt verification.
- [ ] Replace simulation authentication with real controller-side firmware enforcement.
- [ ] Define and implement authenticated peer quorum with M1/M2/M3.
- [ ] Add hardware-backed key invalidation and dedicated hold-up power path.
- [ ] Connect the GUI to live authenticated telemetry instead of local simulation state.

## Directory layout

```text
Blackbox_Sentinel/
├── gui/
│   └── dashboard.py          # Canonical compact 480×320 touchscreen dashboard
├── security/
│   └── trusted_controller.py # Simulation trusted-controller policy and receipts
├── m4-gui-venture/
│   ├── src/app.py            # Larger desktop Tkinter dashboard
│   ├── hw_simulator_server.py# Digital-twin backend and normalized state API
│   └── pitch/                # Venture deliverables
├── m2-systems/os/
│   └── sentinel_touchscreen.sh # Raspberry Pi 3.5-inch setup script
├── docs/
│   └── Patent_Scope_Upgrade_Implementation.md
└── tests/
    └── test_trusted_controller.py
```
