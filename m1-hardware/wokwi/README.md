# BlackBox Sentinel — ESP32 Hardware Simulation (Wokwi)

This directory contains the ready-to-run **Wokwi** simulation schematic for the **ESP32-S3 Co-Processor**.

## 🔌 Simulated Components
1. **ESP32-S3 DevKit v4**: Runs the co-processor firmware (`../src/esp32_coprocessor.ino`).
2. **5V Signal Isolation Relay**: Connected to GPIO 18 (normally closed/engaged).
3. **Anti-Tamper Microswitch / Grid**: Connected to GPIO 27 (active-low interrupt with internal pullup).
4. **Status LEDs**:
   - 🟢 **Green (GPIO 2)**: Solid when node is `ARMED`.
   - 🔴 **Red (GPIO 4)**: Rapid flashing when in `ALERT / LOCKDOWN` or when chassis is tampered.
   - 🔵 **Blue (GPIO 5)**: Pulses during `ESP-NOW Mesh Threat Gossip` TX/RX.
5. **UART Serial**: Connects to the host Raspberry Pi / Terminal at 115200 baud.

---

## 🚀 How to Run the Simulation

### Option A: In the Browser (Zero Install)
1. Go to [https://wokwi.com/projects/new/esp32](https://wokwi.com/projects/new/esp32).
2. Copy the contents of `diagram.json` into the **diagram.json** tab.
3. Copy the contents of `../src/esp32_coprocessor.ino` into the **sketch.ino** tab.
4. Click **Play (▶)** to run!

### Option B: Inside VS Code
1. Install the **Wokwi Simulator** extension in VS Code.
2. Press `F1` and select **Wokwi: Start Simulator**.
3. Open `diagram.json` to view the live animated circuit.

---

## 🕹️ Interactive Test Commands in Serial Monitor
Type these commands into the Serial Monitor to test hardware reactions:

| Command | Action | Expected Hardware Reaction |
|---|---|---|
| `ARM` | Arm the co-processor | 🟢 Green LED turns ON |
| `DISARM` | Disarm node | 🟢 Green LED turns OFF |
| `ISOLATE` | Threat detected | ⚡ Relay clicks open, 🔴 Red LED flashes |
| `ENGAGE` | PIN override accepted | ⚡ Relay clicks closed, 🔴 Red LED turns OFF, 🟢 Green ON |
| `GOSSIP:EXFILTRATION:-0.088:4444` | Broadcast threat | 🔵 Blue LED pulses, ESP-NOW packet sent |
| `Click Red Button (Tamper)` | Breach enclosure | 🚨 Tamper interrupt triggers, keys zeroized, relay isolated |
