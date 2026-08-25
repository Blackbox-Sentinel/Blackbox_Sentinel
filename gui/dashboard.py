"""BlackBox Sentinel — compact 480x320 M4 Phase 2 dashboard.

The dashboard consumes the normalized telemetry contract emitted by the Phase 2
software slice. It is a view and recovery interface; it is not the trusted
controller and does not claim physical ESP32 relay enforcement.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

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
    QWidget,
)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "m4-gui-venture" / "src"))

from integration.telemetry import JsonlTelemetryReader, NormalizedTelemetry  # noqa: E402
from pin_security import validate_pin  # noqa: E402


class Dashboard(QMainWindow):
    """Touch-friendly M4 view for normalized Phase 2 telemetry."""

    def __init__(self, telemetry_path: str | Path | None = None):
        super().__init__()
        self.setWindowTitle("BlackBox Sentinel — M4")
        self.setFixedSize(480, 320)
        self.telemetry_path = Path(telemetry_path) if telemetry_path else None
        self.reader = JsonlTelemetryReader(self.telemetry_path) if self.telemetry_path else None
        self.latest: NormalizedTelemetry | None = None
        self.is_locked = False
        self._build_ui()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_telemetry)
        self.timer.start(500)
        self._log("M4 dashboard ready; waiting for normalized telemetry.")

    def _build_ui(self) -> None:
        container = QWidget()
        layout = QGridLayout(container)
        layout.setContentsMargins(6, 5, 6, 5)
        layout.setHorizontalSpacing(5)
        layout.setVerticalSpacing(3)

        self.status_label = QLabel("CONTROLLER: WAITING")
        self.status_label.setStyleSheet("font-size: 15px; color: #24557a; font-weight: bold;")
        layout.addWidget(self.status_label, 0, 0, 1, 2)

        self.telemetry_label = QLabel("PKTS: 0   ALERTS: 0")
        self.telemetry_label.setStyleSheet("font-size: 11px; color: #1f2937; font-weight: bold;")
        layout.addWidget(self.telemetry_label, 0, 2, 1, 2)

        self.relay_label = QLabel("RELAY: UNKNOWN")
        self.tamper_label = QLabel("TAMPER: UNKNOWN")
        self.key_label = QLabel("KEY: UNKNOWN | POWER: UNKNOWN")
        self.signal_label = QLabel("SIGNALS: 0 | STATUS: WAITING")
        self.receipt_label = QLabel("RECEIPT: NOT AVAILABLE")
        self.quorum_label = QLabel("QUORUM: NOT CONFIGURED")
        self.recovery_label = QLabel("RECOVERY: NOT REQUIRED")
        for row, widget in enumerate(
            (
                self.relay_label,
                self.tamper_label,
                self.key_label,
                self.signal_label,
                self.receipt_label,
                self.quorum_label,
                self.recovery_label,
            ),
            start=1,
        ):
            widget.setStyleSheet("font-size: 9px; color: #1f2937; font-weight: bold;")
            layout.addWidget(widget, row, 0, 1, 4)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet("font-size: 8px; color: #111827; background: #ffffff;")
        layout.addWidget(self.log_box, 8, 0, 1, 4)

        self.attack_btn = QPushButton("ATTACK")
        self.audit_btn = QPushButton("AUDIT")
        self.pin_btn = QPushButton("RECOVER")
        self.refresh_btn = QPushButton("REFRESH")
        self.attack_btn.clicked.connect(self._demo_hint)
        self.audit_btn.clicked.connect(self.audit_receipt)
        self.pin_btn.clicked.connect(self.enter_pin)
        self.refresh_btn.clicked.connect(self.update_telemetry)
        for button in (self.attack_btn, self.audit_btn, self.pin_btn, self.refresh_btn):
            button.setMinimumHeight(34)
            button.setStyleSheet("font-size: 9px; font-weight: bold; padding: 4px;")
        layout.addWidget(self.attack_btn, 9, 0)
        layout.addWidget(self.audit_btn, 9, 1)
        layout.addWidget(self.pin_btn, 9, 2)
        layout.addWidget(self.refresh_btn, 9, 3)

        container.setStyleSheet(
            "QWidget { background: #f3f5f7; } "
            "QPushButton { color: #111827; background: #e5e7eb; border: 1px solid #9ca3af; }"
        )
        self.setCentralWidget(container)

    def _log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_box.append(f"[{timestamp}] {message}")

    def update_telemetry(self) -> None:
        if not self.reader:
            return
        for telemetry in self.reader.read_new():
            self._apply_telemetry(telemetry)

    def _apply_telemetry(self, telemetry: NormalizedTelemetry) -> None:
        previous_id = self.latest.event_id if self.latest else None
        self.latest = telemetry
        self.is_locked = telemetry.relay_state in {"ISOLATED", "LOCKED"} or telemetry.controller_state in {
            "ISOLATED",
            "TAMPERED",
            "RECOVERY",
        }
        self.telemetry_label.setText(f"PKTS: {telemetry.packet_count}   ALERTS: {telemetry.alert_count}")

        state = telemetry.controller_state
        state_color = "#008a3b" if state in {"ARMED", "SAFE"} else "#c00020" if self.is_locked else "#b36b00"
        self.status_label.setText(f"CONTROLLER: {state} | EVENT: {telemetry.status.upper()}")
        self.status_label.setStyleSheet(f"font-size: 13px; color: {state_color}; font-weight: bold;")

        relay_ack = "ACK" if telemetry.relay_acknowledged else "NO ACK"
        relay_verify = "VERIFIED" if telemetry.relay_verified else "SIM/UNVERIFIED"
        self.relay_label.setText(
            f"RELAY: {telemetry.relay_state} | REQUEST: {telemetry.relay_requested} | {relay_ack} | {relay_verify}"
        )
        self.tamper_label.setText(
            f"TAMPER: {telemetry.tamper_state} | LINK: {telemetry.link_state} | "
            f"AUTH: {telemetry.transport_auth} | FRESH: {telemetry.freshness_status}"
        )
        self.key_label.setText(f"KEY: {telemetry.key_state} | POWER: {telemetry.power_state}")

        auth_count = sum(1 for signal in telemetry.signals if signal.get("authenticated"))
        fresh_count = sum(1 for signal in telemetry.signals if signal.get("fresh"))
        self.signal_label.setText(
            f"SIGNALS: {len(telemetry.signals)} | AUTH {auth_count} | FRESH {fresh_count} | DECISION: {telemetry.decision}"
        )
        receipt_id = telemetry.receipt_id or "NONE"
        self.receipt_label.setText(
            f"RECEIPT: {telemetry.receipt_status} | {receipt_id} | SEQ: {telemetry.receipt_sequence or '-'}"
        )
        self.quorum_label.setText(
            f"QUORUM: {telemetry.quorum_state} | {telemetry.quorum_received}/{telemetry.quorum_required or '-'}"
        )
        self.recovery_label.setText(f"RECOVERY: {telemetry.recovery_state}")

        if previous_id != telemetry.event_id:
            note = telemetry.notes or telemetry.rejection_reason or telemetry.event_type
            self._log(
                f"{telemetry.status.upper()}: {note} "
                f"(seq={telemetry.transport_sequence or '-'}, auth={telemetry.transport_auth})"
            )

    def _demo_hint(self) -> None:
        if self.telemetry_path:
            self._log("Attack test is controlled by the Phase 2 vertical-slice runner.")
        else:
            self._log("Start integration/phase2_vertical_slice.py to emit demo events.")

    def audit_receipt(self) -> None:
        if not self.latest:
            self._log("Receipt audit unavailable: no telemetry received.")
            return
        self._log(
            f"Receipt audit status: {self.latest.receipt_status}; "
            f"sequence={self.latest.receipt_sequence or '-'}; "
            f"event={self.latest.event_id}."
        )

    def enter_pin(self) -> None:
        pin, ok = QInputDialog.getText(self, "PIN Recovery", "Enter exact local PIN:")
        if not ok:
            return
        if validate_pin(pin) and self.latest and self.latest.recovery_state in {
            "AUTHENTICATION_REQUIRED",
            "LOCKED",
        }:
            self._log("PIN accepted locally; waiting for controller recovery acknowledgment.")
        else:
            QMessageBox.warning(self, "PIN rejected", "Incorrect PIN or recovery is not currently required.")
            self._log("PIN rejected; controller telemetry remains unchanged.")


def start_gui(telemetry_path: str | Path | None = None) -> None:
    app = QApplication(sys.argv)
    window = Dashboard(telemetry_path=telemetry_path)
    window.show()
    sys.exit(app.exec())


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the BlackBox Sentinel M4 telemetry dashboard")
    parser.add_argument(
        "--telemetry-file",
        type=Path,
        default=None,
        help="JSONL file emitted by integration/phase2_vertical_slice.py",
    )
    args = parser.parse_args()
    start_gui(args.telemetry_file)


if __name__ == "__main__":
    main()
