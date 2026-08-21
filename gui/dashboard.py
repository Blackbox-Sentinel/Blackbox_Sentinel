import sys
import random
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QGridLayout, 
                             QWidget, QTextEdit, QPushButton, QInputDialog, QMessageBox)
from PyQt6.QtCore import QTimer

class Dashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BlackBox Sentinel")
        # HARDWARE FIX: Lock the exact size to the Pi 3.5" screen (480x320)
        self.setFixedSize(480, 320)

        # Use a Grid Layout for tighter spacing on a tiny screen
        layout = QGridLayout()

        # Row 0: Status & Traffic
        self.status_label = QLabel("STATUS: IDLE")
        self.status_label.setStyleSheet("font-size: 16px; color: green; font-weight: bold;")
        layout.addWidget(self.status_label, 0, 0)

        self.traffic_label = QLabel("Traffic: 0 p/s")
        self.traffic_label.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.traffic_label, 0, 1)

        # Row 1: Compact Log Box
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet("font-size: 10px;") # Smaller text to fit the logs
        layout.addWidget(self.log_box, 1, 0, 1, 2) # Span across two columns

        # Row 2: Touch-friendly Buttons
        self.attack_btn = QPushButton("Sim Attack")
        self.attack_btn.setStyleSheet("background-color: orange; font-weight: bold; padding: 15px;")
        self.attack_btn.clicked.connect(self.trigger_attack)
        layout.addWidget(self.attack_btn, 2, 0)

        self.pin_btn = QPushButton("UNLOCK SYSTEM")
        self.pin_btn.setStyleSheet("background-color: gray; font-weight: bold; padding: 15px;")
        self.pin_btn.setEnabled(False) 
        self.pin_btn.clicked.connect(self.enter_pin)
        layout.addWidget(self.pin_btn, 2, 1)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_dummy_data)
        self.timer.start(1000)
        self.is_locked = False

    def update_dummy_data(self):
        if self.is_locked:
            return 
        fake_traffic = random.randint(10, 150)
        self.traffic_label.setText(f"Traffic: {fake_traffic} p/s")
        # Shortened log string to fit the small screen width
        self.log_box.append(f"Normal: {fake_traffic} p/s")

    def trigger_attack(self):
        self.is_locked = True
        self.status_label.setText("LOCKED")
        self.status_label.setStyleSheet("font-size: 16px; color: red; font-weight: bold;")
        self.log_box.append("ALERT! System locked.")
        self.attack_btn.setEnabled(False)
        self.pin_btn.setStyleSheet("background-color: blue; color: white; font-weight: bold; padding: 15px;")
        self.pin_btn.setEnabled(True)

    def enter_pin(self):
        # We will eventually need a custom on-screen numpad for the Pi, 
        # but the standard input dialog works for laptop testing right now.
        pin, ok = QInputDialog.getText(self, "PIN", "Enter PIN:")
        
        if ok and pin == "1234":
            self.is_locked = False
            self.status_label.setText("STATUS: IDLE")
            self.status_label.setStyleSheet("font-size: 16px; color: green; font-weight: bold;")
            self.log_box.append("Unlocked via PIN.")
            self.attack_btn.setEnabled(True)
            self.pin_btn.setStyleSheet("background-color: gray; font-weight: bold; padding: 15px;")
            self.pin_btn.setEnabled(False)
        elif ok:
            QMessageBox.warning(self, "Error", "Access Denied.")
            self.log_box.append("Failed unlock.")

def start_gui():
    app = QApplication(sys.argv)
    window = Dashboard()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    start_gui()