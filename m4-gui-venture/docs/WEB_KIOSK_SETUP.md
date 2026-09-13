# M4 Web Kiosk Setup

This frontend replaces the obsolete Tkinter/CustomTkinter display path. The intended architecture is **Flask on localhost:5000** serving HTML/CSS/JavaScript to **Chromium in kiosk mode** on the Raspberry Pi 4.

## Files

| File | Purpose |
|---|---|
| `app_web.py` | Existing Flask backend and API routes. |
| `templates/index.html` | Flask-served Field Desk shell. |
| `static/sentinel.css` | 480×320 touch-first visual system. |
| `static/sentinel.js` | Navigation, telemetry polling, graph rendering, actions, and PIN dialog. |

The frontend does not implement containment logic. It calls the existing backend routes, and the backend remains responsible for M3 evidence, the trusted controller, the signed receipt, and hardware enforcement.

## API contract used by the frontend

| Route | Method | Purpose |
|---|---|---|
| `/api/telemetry` | `GET` | Polls state, packet count, anomalies, blocks, uptime, logs, rate history, and score history. |
| `/api/inject` | `POST` | Sends `{ "attack": "EXFILTRATION" }` or `{ "attack": "SYN_FLOOD" }` to the existing simulator route. |
| `/api/tamper` | `POST` | Exercises the existing tamper route. |
| `/api/pin` | `POST` | Sends `{ "pin": "...." }` to the existing recovery route. |

The frontend does not send the obsolete plain `ANOMALY\n` message and does not open a serial port. UART, signed containment receipts, Ed25519, and `/dev/ttyAMA5` remain backend/hardware responsibilities.

## Local test on the Pi

From the repository root:

```bash
python3 -m pip install -r requirements.txt
python3 app_web.py
```

Open a second terminal and confirm the local service:

```bash
curl http://127.0.0.1:5000/
curl http://127.0.0.1:5000/api/telemetry
```

Then launch Chromium on the Pi display:

```bash
chromium-browser --kiosk --app=http://127.0.0.1:5000/ --noerrdialogs --disable-infobars
```

If the device uses the Chromium binary name `chromium`, use:

```bash
chromium --kiosk --app=http://127.0.0.1:5000/ --noerrdialogs --disable-infobars
```

## Physical validation owned by M1

M1 should verify the 480×320 layout, touchscreen hit areas, Signal Room graph updates, Containment Desk behavior, Field Journal updates, Node Health display, signed 12-field receipt path, `/dev/ttyAMA5`, ESP32 validation, and clean shutdown. A source-code check is not a hardware approval.

## Git procedure

Do not commit the old Tkinter `app_pi.py` redesign as the web migration. First make sure the local branch is current and review the new files:

```bash
git pull origin main
git status --short
python3 -m py_compile app_web.py
node --check static/sentinel.js
git diff --check
```

After M1 approves the physical kiosk test:

```bash
git add app_web.py templates/index.html static/sentinel.css static/sentinel.js m4-gui-venture/docs/WEB_KIOSK_SETUP.md
git commit -m "Migrate M4 GUI to a touch-first Flask web kiosk"
git push origin main
git status
```

Do not stage runtime keys, logs, `__pycache__`, screenshots, ZIP files, or local backups.
