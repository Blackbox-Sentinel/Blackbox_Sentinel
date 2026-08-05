# M1 — Hardware Module

> **Owner:** M1 Hardware Engineer | **Branch:** `m1-dev`

## Overview

This module handles all embedded hardware — the ESP32 microcontroller, SIM800L GSM module, and supporting circuitry for packet sniffing and alert transmission.

## Directory Layout

```
m1-hardware/
├── src/              # Arduino/PlatformIO source code
│   └── main.ino      # Main ESP32 firmware
├── schematics/       # Circuit diagrams, Fritzing files, Wokwi links
│   └── wokwi_link.md # Link to online simulation
└── README.md         # This file
```

## Setup

1. Install [PlatformIO](https://platformio.org/) or Arduino IDE
2. Select board: `ESP32 Dev Module`
3. Install required libraries:
   - `WiFi.h`
   - `SIM800L` (TinyGSM)
4. Flash via USB

## Wokwi Simulation

> 🔗 Add your Wokwi project link in `schematics/wokwi_link.md`

## Tasks

- [ ] Initialize ESP32 WiFi promiscuous mode
- [ ] Implement SIM800L SMS alert on anomaly
- [ ] Design circuit schematic
- [ ] Create Wokwi simulation for team review
