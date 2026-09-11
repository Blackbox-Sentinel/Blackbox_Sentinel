# M2 — Systems & Sentinel OS Module

> **Owner:** M2 Systems Engineer | **Branch:** `m2-dev`

## Overview

This module contains the complete **BlackBox Sentinel Operating System architecture**, kernel hardening configuration, transparent inline Layer-2 network bridge, Hardware Abstraction Layer (HAL), and digital twin simulation testbed.

---

## Directory Layout

```
m2-systems/
├── os/                              # Sentinel OS Provisioning & Hardening Suite
│   ├── build_sentinel_os.sh        # Master automated unattended OS provisioner
│   ├── sentinel_sysctl.conf        # Kernel & TCP/IP stack hardening
│   ├── setup_network_bridge.sh     # Transparent L2 inline bridge (br0)
│   ├── security_hardening.sh       # UFW, AppArmor, volatile tmpfs keys, bloat purge
│   ├── sentinel_touchscreen.sh     # 800x480 Framebuffer kiosk display setup
│   └── systemd/                    # Systemd appliance service units
│       ├── sentinel-bridge.service
│       ├── sentinel-core.service
│       ├── sentinel-gui.service
│       └── sentinel.target
├── sim/                             # Simulation-First Testbed & Digital Twin
│   ├── setup_veth_lab.sh           # Linux network namespace testbed (ns_client <-> br0 <-> ns_server)
│   ├── traffic_generator.py        # High-fidelity normal traffic & attack vectors
│   ├── run_simulation.py           # Master digital twin end-to-end simulation runner
│   ├── Dockerfile.sim              # Containerized Sentinel appliance node
│   └── docker-compose.yml          # Multi-node simulation environment
└── src/                             # Core Python evidence transport
    └── evidence_transport.py       # Authenticated evidence envelopes (per-node HMAC)

Note: capture.py and bridge.py were archived in 4d964e3 - the real capture
path is sentinel_pipeline.py at the repo root, which uses
ml/feature_pipeline_v2.py for packet-to-window feature extraction.
```

---

## Hardware Abstraction Layer (HAL)

Located in `common/hal/`, the HAL dynamically abstracts physical vs simulated devices:

- **Mode switch:** Controlled via environment variable `SENTINEL_HARDWARE=real` or `SENTINEL_HARDWARE=sim`.
- **Peripherals:**
  - `RelayInterface` (BCM GPIO 17 / Mock Line Cut)
  - `TamperInterface` (BCM GPIO 27 & 22 / Volatile RAM Key Zeroization)
  - `LEDInterface` (BCM GPIO 23 / Flashing State Indicator)
  - `CellularInterface` (SIM800L UART `/dev/serial0` / OOB SMS Logger)
  - `MeshInterface` (ESP32-S3 `/dev/ttyUSB0` / UDP Mesh Threat Gossip)

---

## Quickstart & Testing

### 1. Run Digital Twin Simulation (No Hardware Needed)
```bash
python m2-systems/sim/run_simulation.py
```

### 2. Run Full Core Pipeline (Simulated Mode)
```bash
python sentinel_pipeline.py
```

### 3. Provision Real Raspberry Pi 4 B Hardware

**Not yet executed on hardware.** These scripts are statically validated
(shellcheck clean, systemd units verified) but have never run on a real Pi.
Treat first provisioning as untested.
Flash microSD card with standard 64-bit Raspberry Pi OS Lite (Debian Bookworm), clone repo, and run:
```bash
sudo bash m2-systems/os/build_sentinel_os.sh
```
