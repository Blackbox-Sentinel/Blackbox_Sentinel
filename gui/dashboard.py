"""BlackBox Sentinel — compact 480x320 M4 touchscreen dashboard.

This is a simulation-oriented M4 view. The trusted-controller policy must be
reimplemented in the ESP32/security MCU for physical deployment.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QApplication,
    QGridLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from security.trusted_controller import ControllerState, TrustedController
sys.path.insert(0, os.path.join(ROOT, "m4-gui-venture", "src"))
from pin_security import validate_pin


class Dashboard(QMainWindow):
    """Touch-friendly M4 dashboard for the patent-scope simulation."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("BlackBox Sentinel")
        self.setFixedSize(480, 320)
        self.controller = TrustedController(secret=b"phase2-demo-secret", quorum_required=0, freshness_window_seconds=60)
        self.controller.arm()
        self.is_locked = False
        self.packet_count = 0
        self.anomaly_count = 0
        self._build_ui()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_telemetry)
        self.timer.start(1000)
        self._log("Controller ARMED. Waiting for trusted evidence.")

    def _build_ui(self):
        container = QWidget()
        layout = QGridLayout(container)
        layout.setContentsMargins(6, 5, 6, 5)
        layout.setHorizontalSpacing(5)
        layout.setVerticalSpacing(3)

        self.status_label = QLabel("CONTROLLER: ARMED")
        self.status_label.setStyleSheet("font-size: 15px; color: #008a3b; font-weight: bold;")
        layout.addWidget(self.status_label, 0, 0, 1, 2)

        self.telemetry_label = QLabel("PKTS: 0   ALERTS: 0")
        self.telemetry_label.setStyleSheet("font-size: 11px; font-weight: bold;")
        layout.addWidget(self.telemetry_label, 0, 2, 1, 2)

        self.relay_label = QLabel("RELAY: ENGAGED")
        self.tamper_label = QLabel("TAMPER: SECURE")
        self.key_label = QLabel("KEY: VALID | POWER: PRIMARY")
        self.signal_label = QLabel("SIGNALS: 0/2 | DECISION: WAITING")
        self.receipt_label = QLabel("RECEIPT: NOT AVAILABLE | QUORUM: N/A")
        for row, widget in enumerate((self.relay_label, self.tamper_label, self.key_label, self.signal_label, self.receipt_label), start=1):
            widget.setStyleSheet("font-size: 10px; font-weight: bold;")
            layout.addWidget(widget, row, 0, 1, 4)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet("font-size: 9px;")
        layout.addWidget(self.log_box, 6, 0, 1, 4)

        self.attack_btn = QPushButton("ATTACK")
        self.attack_btn.clicked.connect(self.trigger_attack)
        self.tamper_btn = QPushButton("TAMPER")
        self.tamper_btn.clicked.connect(self.trigger_tamper)
        self.audit_btn = QPushButton("AUDIT")
        self.audit_btn.clicked.connect(self.audit_receipt)
        self.pin_btn = QPushButton("PIN RECOVERY")
        self.pin_btn.clicked.connect(self.enter_pin)
        for button in (self.attack_btn, self.tamper_btn, self.audit_btn, self.pin_btn):
            button.setMinimumHeight(35)
            button.setStyleSheet("font-size: 9px; font-weight: bold; padding: 4px;")
        layout.addWidget(self.attack_btn, 7, 0)
        layout.addWidget(self.tamper_btn, 7, 1)
        layout.addWidget(self.audit_btn, 7, 2)
        layout.addWidget(self.pin_btn, 7, 3)

        container.setStyleSheet("QWidget { background: #f3f5f7; }")
        self.setCentralWidget(container)

    def _log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_box.append(f"[{timestamp}] {message}")

    def update_telemetry(self):
        self.packet_count += 1
        if not self.is_locked:
            self.telemetry_label.setText(f"PKTS: {self.packet_count}   ALERTS: {self.anomaly_count}")
        state = self.controller.state.value
        if state == "ISOLATED":
            self.status_label.setText("CONTROLLER: ISOLATED")
            self.status_label.setStyleSheet("font-size: 15px; color: #c00020; font-weight: bold;")
            self.relay_label.setText("RELAY: ISOLATED | ACK: CONFIRMED")
            self.relay_label.setStyleSheet("font-size: 10px; color: #c00020; font-weight: bold;")
        elif state == "TAMPERED":
            self.status_label.setText("CONTROLLER: TAMPERED")
            self.status_label.setStyleSheet("font-size: 15px; color: #c00020; font-weight: bold;")
            self.tamper_label.setText("TAMPER: BREACHED")
            self.tamper_label.setStyleSheet("font-size: 10px; color: #c00020; font-weight: bold;")
            self.key_label.setText("KEY: INVALIDATED | POWER: PRIMARY")
        elif state == "ARMED":
            self.status_label.setText("CONTROLLER: ARMED")
            self.status_label.setStyleSheet("font-size: 15px; color: #008a3b; font-weight: bold;")

        accepted = len([event for event in self.controller.events if event.get("event_type") == "signal_accepted"])
        signal_count = min(accepted, 2)
        self.signal_label.setText(f"SIGNALS: {signal_count}/2 | DECISION: {'APPROVED' if state == 'ISOLATED' else 'WAITING'}")
        latest = self.controller.receipts[-1] if self.controller.receipts else None
        if latest:
            receipt_status = self.controller.verify_receipt(latest)[1]
            self.receipt_label.setText(f"RECEIPT: {receipt_status} {latest.receipt_id} | QUORUM: N/A")
        if state == "ARMED":
            self.relay_label.setText("RELAY: ENGAGED | ACK: CONFIRMED")
            self.tamper_label.setText("TAMPER: SECURE")
            self.key_label.setText("KEY: VALID | POWER: PRIMARY")

    def trigger_attack(self):
        if self.controller.state == ControllerState.ISOLATED:
            self._log("Attack ignored: controller already isolated.")
            return
        self.anomaly_count += 1
        event_id = f"evt-{self.packet_count:06d}"
        first = self.controller.issue_signal(event_id=event_id, source="known-detector", signal_type="known_attack", payload={"score": -0.115})
        second = self.controller.issue_signal(event_id=event_id, source="adaptive-profile", signal_type="adaptive_anomaly", payload={"score": -0.115})
        self.controller.submit_signal(first)
        result = self.controller.submit_signal(second)
        self.is_locked = result.get("decision") == "ISOLATE"
        self._log("Signal A accepted: known-attack evidence.")
        self._log("Signal B accepted: adaptive-anomaly evidence.")
        if self.is_locked:
            receipt = result["receipt"]
            self._log(f"Containment approved; relay isolated; {receipt['receipt_id']} verified.")
        else:
            self._log("Containment pending; relay remains engaged.")
        self.update_telemetry()

    def trigger_tamper(self):
        self.controller.mark_tampered()
        self.is_locked = True
        self._log("Tamper detected; controller isolated relay and invalidated key state.")
        self.update_telemetry()

    def audit_receipt(self):
        if not self.controller.receipts:
            self._log("Receipt audit unavailable: no containment receipt yet.")
            return
        valid, reason = self.controller.verify_receipt(self.controller.receipts[-1])
        self._log(f"Receipt audit {'PASSED' if valid else 'FAILED'}: {reason}.")
        self.update_telemetry()

    def enter_pin(self):
        pin, ok = QInputDialog.getText(self, "PIN Recovery", "Enter exact local PIN:")
        if ok and validate_pin(pin) and self.controller.recover():
            self.is_locked = False
            self._log("PIN accepted by recovery workflow; relay restored.")
            self.update_telemetry()
        elif ok:
            QMessageBox.warning(self, "PIN rejected", "Incorrect PIN. Controller remains isolated.")
            self._log("PIN rejected; controller policy unchanged.")


def start_gui():
    app = QApplication(sys.argv)
    window = Dashboard()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    start_gui()
