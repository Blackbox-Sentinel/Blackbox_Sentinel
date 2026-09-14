#!/usr/bin/env python3
"""TouchScreen Calibration Tool — tap each numbered box, log where the click lands."""

import sys
import os
from datetime import datetime
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QFont, QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QGridLayout, QPushButton, QLabel, QVBoxLayout
)

LOG_FILE = "/tmp/touch_calibration.log"

BOXES = [
    ("1 TOP-LEFT",    0, 0),
    ("2 TOP-MID",     0, 1),
    ("3 TOP-RIGHT",   0, 2),
    ("4 MID-LEFT",    1, 0),
    ("5 CENTER",      1, 1),
    ("6 MID-RIGHT",   1, 2),
    ("7 BOT-LEFT",    2, 0),
    ("8 BOT-MID",     2, 1),
    ("9 BOT-RIGHT",   2, 2),
]

COLORS = [
    "#c0392b", "#2980b9", "#27ae60",
    "#8e44ad", "#f39c12", "#16a085",
    "#e67e22", "#2c3e50", "#1abc9c",
]

class CalibBox(QPushButton):
    def __init__(self, label, row, col, on_tap):
        super().__init__(label)
        self._row = row
        self._col = col
        self._on_tap = on_tap
        self._last_pos = None
        font = QFont("Ubuntu Mono", 16, QFont.Weight.Bold)
        self.setFont(font)
        self.setMinimumSize(159, 106)

    def mousePressEvent(self, event):
        pos = event.position()
        global_pos = self.mapToGlobal(event.position().toPoint())
        self._on_tap(self._row, self._col, self.text(),
                     int(pos.x()), int(pos.y()),
                     global_pos.x(), global_pos.y())
        super().mousePressEvent(event)


class CalibWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Touch Calibration")
        self.setFixedSize(480, 320)
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)

        container = QWidget()
        grid = QGridLayout(container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(2)

        for i, (label, row, col) in enumerate(BOXES):
            btn = CalibBox(label, row, col, self._on_tap)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS[i]};
                    color: white;
                    font-size: 14px;
                    font-weight: bold;
                    border: 2px solid #ffffff;
                    border-radius: 4px;
                }}
                QPushButton:pressed {{
                    background-color: white;
                    color: black;
                }}
            """)
            grid.addWidget(btn, row, col)

        self.log_label = QLabel("Tap a box → coordinates will be logged to /tmp/touch_calibration.log")
        self.log_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.log_label.setStyleSheet("background:#111; color:#0f0; font-size:9px; padding:2px;")
        self.log_label.setFixedHeight(22)

        wrapper = QWidget()
        vbox = QVBoxLayout(wrapper)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)
        vbox.addWidget(container)
        vbox.addWidget(self.log_label)

        self.setCentralWidget(wrapper)

        # Clear log
        with open(LOG_FILE, "w") as f:
            f.write(f"=== Touch Calibration Log === {datetime.now()}\n")
            f.write("Format: BOX | local(x,y) | global(x,y)\n\n")

    def _on_tap(self, row, col, label, lx, ly, gx, gy):
        line = f"TAP: {label:20s} | local({lx:4d},{ly:4d}) | global({gx:4d},{gy:4d})"
        ts = datetime.now().strftime("%H:%M:%S")
        full_line = f"[{ts}] {line}"
        print(full_line, flush=True)
        with open(LOG_FILE, "a") as f:
            f.write(full_line + "\n")
        self.log_label.setText(f"Tapped: {label}  @ global({gx},{gy})")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = CalibWindow()
    w.show()
    sys.exit(app.exec())
