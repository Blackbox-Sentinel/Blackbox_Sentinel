# M4 — GUI & Venture Module

> **Owner:** M4 GUI/Venture Lead | **Branch:** `m4-dev`

## Overview

This module builds the 800×480 Tkinter dashboard interface for real-time anomaly visualization, plus the pitch deck and documentation for project presentation.

## Directory Layout

```
m4-gui-venture/
├── src/
│   ├── app.py            # Main Tkinter application
│   ├── dashboard.py      # Real-time anomaly dashboard widgets
│   └── config.py         # GUI configuration & theme
├── assets/               # Icons, images, fonts
├── pitch/                # Pitch deck (PDF/PPTX), one-pager
│   └── deck.md           # Pitch deck outline
└── README.md             # This file
```

## Setup

```bash
python -m venv venv
source venv/bin/activate

pip install tkinter matplotlib pillow
```

## Tasks

- [ ] Design 800×480 dashboard layout
- [ ] Implement real-time anomaly score display
- [ ] Add hash-chain log viewer panel
- [ ] Create hardware status indicator
- [ ] Build pitch deck (Figma/Canva link)
- [ ] Write project one-pager documentation
