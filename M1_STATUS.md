# M1 Hardware Status Report
*Last updated: 2026-09-14*

## What's Confirmed Working (Live Hardware)

### ✅ UART5 Relay Trigger (Physical)
- **Tested:** Yes, relay physically fired
- **How:** Pi GPIO12 (TX) → ESP32 GPIO19 (RX) @ 115200 baud, UART5 overlay on `/dev/ttyAMA5`
- **Evidence:** `{"event":"relay_isolated","reason":"SECURE CONTAIN"}` received back over Serial2. Relay clicked. SMS dispatched to +919914551405. OLED showed `!! ISOLATED !!`.
- **Script:** `tools/trigger_relay.py` (use `SENTINEL_ED25519_KEY=<key> python3 tools/trigger_relay.py`)

### ✅ Ed25519 Signing Chain
- New keypair generated on Pi
- Private key: in `/etc/systemd/system/sentinel.service` as `SENTINEL_ED25519_KEY`
- Public key: hardcoded in `m1-hardware/src/blackbox_sentinel/blackbox_sentinel.ino` (`TRUSTED_PUB_KEY`)
- **Both match** — ESP32 accepts signed receipts from the Pi

### ✅ UART Loopback Test
- **Run:** Yes (`tools/test_uart_loopback.py`)
- **Result:** `/dev/ttyAMA5` opens at 115200. PING sent → `{"event":"pong","isolated":false,"tamper":false}` received in < 1s. Bidirectional confirmed.

### ✅ Headless Flask (No Display)
- **Mode:** Fully headless — X11/Chromium/TFT display removed from boot chain
- **Access:** `http://10.27.79.132:5000` (or `http://raspberrypi.local:5000`) from any browser on the same network
- **Service:** `sentinel.service` → `start_sentinel.sh` → `python3 app_web.py` with `SENTINEL_HARDWARE=hw`
- **Log:** `/tmp/flask.log`

### ✅ ESP32 Firmware v2.1
- Responses sent on BOTH `Serial` (USB debug) AND `Serial2` (Pi GPIO bridge)
- Heartbeat every 5s over Serial2 (`{"event":"heartbeat","uptime":...}`)
- `PING` command for quick connectivity test
- OLED rotation fixed for vertical mount (`U8G2_R1`)

---

## M2 Questions — Answered

### 1. UART loopback test — has it actually been run?
**Yes.** Output: PING → pong JSON in < 1s. Full bidirectional confirmed. Relay also physically triggered.

### 2. sentinel.service naming collision
**Fixed.** M2's file is now `m2-systems/config/sentinel-bridge.service`. M1's is `tools/sentinel.service` (installed as `sentinel.service` on the Pi). No collision.

### 3. Read-only FS / OverlayFS
**Still deferred.** Deliberately held until the signing chain and relay are stable. Now that relay is confirmed working, OverlayFS (`tools/enable_readonly.sh`) is the next step.

### 4. Physical relay / quorum test
**Done.** See above. Relay fired, SMS sent, ESP32 confirmed isolation over Serial2.

### 5. Two UNKNOWN fallbacks in drivers_real.py (lines 95/165/248)
**Intentional defaults, not bugs:**
- Line 165: `"UNKNOWN"` only appears when `simulate_tamper()` is called programmatically (no physical GPIO button). When a real button triggers it, `btn.pin.number` is used.  
- Line 248: `default="UNKNOWN"` for `threat_type` — safe fallback if threat payload has no recognized type key. ESP32 firmware uses `.replace(":", "_")` to sanitize it anyway.

---

## What's Next

1. **`tools/enable_readonly.sh`** — enable OverlayFS read-only root (now safe to run)
2. **End-to-end quorum test** — trigger containment from the web UI (not just the CLI script)
3. **M2 bridge service** — M2 can now install `sentinel-bridge.service` independently

---

## Key Credentials / Facts for M2

| Item | Value |
|------|-------|
| Pi IP | 10.27.79.132 |
| UI URL | http://10.27.79.132:5000 |
| SENTINEL_ED25519_KEY | `pTzAdlRSVMXTi2PNIXM1BiONgTEHAxyea2wxPEoR-0Q` |
| ESP32 public key (b64url) | `ZI48kNsD__8q2Sp_LJLRzT4W8Iaku8DsmG95Myov66k` |
| UART device | `/dev/ttyAMA5` |
| Pi TX pin (BCM) | GPIO 12 |
| Pi RX pin (BCM) | GPIO 13 |
| ESP32 RX pin | GPIO 19 |
| ESP32 TX pin | GPIO 20 |
| Baud rate | 115200 |
