# M3 — ML & Ledger Module

> **Owner:** M3 ML Engineer | **Branch:** `m3-dev`

## Overview

This module implements the Isolation Forest anomaly detection model and the hash-chained tamper-proof logging system. It consumes `.pcap` data from M2 and outputs anomaly scores + verified log entries to M4.

## Directory Layout

```
m3-ml-ledger/
├── src/
│   ├── train.py          # Train Isolation Forest on pcap features
│   ├── predict.py        # Real-time anomaly scoring
│   └── ledger.py         # Hash-chained log implementation
├── models/               # Saved model files (.joblib)
├── data/                 # Sample pcap & CSV datasets
└── README.md             # This file
```

## Setup

```bash
python -m venv venv
source venv/bin/activate

pip install scikit-learn pandas numpy scapy joblib
```

## Tasks

- [ ] Extract features from pcap files (packet size, interval, protocol)
- [ ] Train Isolation Forest on sample campus traffic
- [ ] Implement hash-chained log (SHA-256 linked entries)
- [ ] Create prediction API for real-time scoring
- [ ] Validate model with labeled anomaly data
