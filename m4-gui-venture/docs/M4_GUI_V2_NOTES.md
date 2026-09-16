# M4 GUI v2 — Advanced Dark-Glass Operator Console

## Design Notes for Team Review

**Author:** M4 (GUI & Operator Interface)  
**Date:** 2026-09-16  
**File:** `app_pi.py` (root level)  
**Display:** 480×320 TFT Touchscreen  
**Framework:** customtkinter (dark mode)

---

## What Changed (UI Layer Only)

### New Color System
| Role | Color | Hex |
|---|---|---|
| Primary Accent | Violet | `#8B5CF6` |
| Alert / Anomaly | Coral | `#FF4F6D` |
| Success / Healthy | Emerald | `#34D399` |
| Warning / Data | Amber | `#F59E0B` |
| Background | Pure Black | `#050508` |
| Card Surface | Dark Glass | `#0C0C14` |

### Layout
- **Header (30px):** Brand logo + node ID + animated status badge
- **Nav Dock (48px, left):** 5 icon buttons with violet glow ring on active
- **Content Area:** View-specific content, fills remaining space
- **Footer (18px):** Version, ledger status, hardware mode

### 5 Views + PIN Overlay
1. **Overview:** Asymmetric metric cards, embedded sparkline, radial threat gauge, system health bar
2. **Signals:** Dual-axis live graph with gradient fills (violet=packets, coral=anomaly), floating value badges, stat chips
3. **Actions:** 2×2 glass-morphism tactical cards with accent borders (C2 Exfil, SYN Flood, Breach, PIN Unlock)
4. **Journal:** Color-coded operation log (red=alert, green=success, amber=warning, violet=system)
5. **Health:** UART5/Ed25519/Relay status pills, controller state key-values, chain integrity ring, privacy footer
6. **PIN Pad:** Frosted-glass overlay with violet border, numeric keypad, CLR/OK buttons

---

## What Did NOT Change (Backend Preserved)

All safety-critical logic is preserved exactly as-is:

- `_apply_containment_logic()` — M3 two-signal evidence gating
- `ContainmentReceiptService` — 12-field Ed25519 signed receipts
- `Ed25519ReceiptSigner` — Cryptographic receipt signing
- `TwoSignalGate` — Independent signal requirement (ml_anomaly + heuristic_rate)
- `SimTrustedController` — UART dispatch to `/dev/ttyAMA5`
- `_pipeline_worker()` — Background packet processing + calibration
- `_handle_tamper_event()` — Key zeroization + containment
- `inject_attack()` — Adversarial injection scheduling
- PIN validation via `pin_security.validate_pin()`
- `on_close()` — Clean shutdown releasing UART
- All imports, path resolution, and HAL initialization

---

## M1 Physical Validation Required

The following must be tested on the Pi + TFT before push:

1. Application fits the physical 480×320 TFT
2. Nav dock icons are touchable on resistive/capacitive screen
3. All 5 views render correctly and switch cleanly
4. Live graph animates smoothly (~10fps canvas redraw)
5. Attack injection triggers the full containment path
6. Signed 12-field receipt is generated with Ed25519
7. Receipt transmits over `/dev/ttyAMA5`
8. ESP32 validates the Ed25519 receipt
9. Casing breach uses the containment path (not a shortcut)
10. PIN override restores the relay and re-arms controller
11. Clean shutdown releases UART without resource leak

---

## Dependencies

```
customtkinter >= 5.0
cryptography
scikit-learn
numpy
joblib
```

No new dependencies were added in this redesign.

---

## Source Validation

```powershell
python -m py_compile .\app_pi.py   # Syntax check
git diff --check                     # Whitespace check
```

Both passed before packaging.
