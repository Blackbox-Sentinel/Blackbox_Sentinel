# BlackBox Sentinel

BlackBox Sentinel is a physical network intrusion appliance on a Raspberry Pi: it inline-captures traffic, flags anomalies via Isolation Forest, and physically cuts the data line on detection. Events go to a tamper-evident hash-chained log, alerts fire via SMS, and recovery requires a physical touchscreen PIN — no remote override possible.

## Project structure

```
BlackBox-Sentinel/
    firmware/
    net/
    ml/
    ledger/
    gui/
    drivers/
        sim/
        real/
    tests/
    config.py
    main.py
    requirements.txt
    README.md
```

## Phase 0 — Setup

1. Clone the repo and open it in VS Code.
2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Run in simulation mode (default):
   ```
   python main.py
   ```

   You should see:
   ```
   Starting BlackBox Sentinel...
   Running in Simulation Mode...
   Heartbeat...
   Heartbeat...
   Heartbeat...
   ```

## Hardware mode switch

`config.py` reads the `HARDWARE` environment variable:
- `HARDWARE=sim` (default) — loads fake drivers from `drivers/sim/`, no real hardware needed.
- `HARDWARE=real` — loads real drivers from `drivers/real/`.

This is the only switch that should change to move between simulation and real hardware.
