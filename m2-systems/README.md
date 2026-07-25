# M2 — Systems Module

> **Owner:** M2 Systems Engineer | **Branch:** `m2-dev`

## Overview

This module handles network packet capture using Scapy, the bridge between hardware and ML pipeline, and systemd service configurations for persistent monitoring.

## Directory Layout

```
m2-systems/
├── src/              # Python capture & bridge scripts
│   ├── capture.py    # Scapy-based packet sniffer
│   └── bridge.py     # Serial-to-pcap bridge (ESP32 → file)
├── config/           # systemd service files
│   └── sentinel.service
└── README.md         # This file
```

## Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install scapy pyserial
```

## Tasks

- [ ] Implement Scapy packet capture script
- [ ] Build serial bridge (ESP32 USB → pcap)
- [ ] Write systemd service for auto-start
- [ ] Test capture with sample network traffic
