import sys
import random
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout, 
                             QWidget, QTextEdit, QPushButton, QInputDialog, QMessageBox)
from PyQt6.QtCore import QTimer

class Dashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BlackBox Sentinel - Dashboard")
        self.setGeometry(100, 100, 500, 600)

        # Create a layout to stack items vertically
        layout = QVBoxLayout()

        # 1. Status & Traffic Labels
        self.status_label = QLabel("STATUS: IDLE")
        self.status_label.setStyleSheet("font-size: 24px; color: green; font-weight: bold;")
        layout.addWidget(self.status_label)

        self.traffic_label = QLabel("Traffic: 0 packets/sec")
        self.traffic_label.setStyleSheet("font-size: 18px;")
        layout.addWidget(self.traffic_label)

        # 2. Ledger & Alerts Log Box
        layout.addWidget(QLabel("System Logs (Ledger & Alerts):"))
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True) # Make it so the user can't type in it
        layout.addWidget(self.log_box)

        # 3. Simulate Attack Button
        self.attack_btn = QPushButton("Simulate Attack")
        self.attack_btn.setStyleSheet("background-color: orange; font-weight: bold; padding: 10px;")
        self.attack_btn.clicked.connect(self.trigger_attack)
        layout.addWidget(self.attack_btn)

        # 4. PIN Override Button
        self.pin_btn = QPushButton("Enter PIN to Unlock")
        self.pin_btn.setStyleSheet("background-color: gray; font-weight: bold; padding: 10px;")
        self.pin_btn.setEnabled(False) # Disabled until an attack happens
        self.pin_btn.clicked.connect(self.enter_pin)
        layout.addWidget(self.pin_btn)

        # Apply the layout
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Timer for Dummy Data
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_dummy_data)
        self.timer.start(1000)
        
        self.is_locked = False

    def update_dummy_data(self):
        # Stop feeding normal data if the system is locked
        if self.is_locked:
            return 
        
        fake_traffic = random.randint(10, 150)
        self.traffic_label.setText(f"Traffic: {fake_traffic} packets/sec")
        self.log_box.append(f"[INFO] Normal traffic: {fake_traffic} p/s")

    def trigger_attack(self):
        # What happens when a fake attack is detected
        self.is_locked = True
        self.status_label.setText("STATUS: SYSTEM LOCKED")
        self.status_label.setStyleSheet("font-size: 24px; color: red; font-weight: bold;")
        self.log_box.append("[ALERT] Malicious activity detected! System locked.")
        
        # Turn off the attack button and turn on the PIN button
        self.attack_btn.setEnabled(False)
        self.pin_btn.setStyleSheet("background-color: blue; color: white; font-weight: bold; padding: 10px;")
        self.pin_btn.setEnabled(True)

    def enter_pin(self):
        # Pop-up screen for the physical PIN entry
        pin, ok = QInputDialog.getText(self, "PIN Override", "Enter 4-digit PIN (Hint: 1234):")
        
        if ok and pin == "1234":
            self.is_locked = False
            self.status_label.setText("STATUS: IDLE")
            self.status_label.setStyleSheet("font-size: 24px; color: green; font-weight: bold;")
            self.log_box.append("[INFO] System unlocked successfully via PIN.")
            
            # Reset buttons
            self.attack_btn.setEnabled(True)
            self.pin_btn.setStyleSheet("background-color: gray; font-weight: bold; padding: 10px;")
            self.pin_btn.setEnabled(False)
        elif ok:
            QMessageBox.warning(self, "Error", "Incorrect PIN! Access Denied.")
            self.log_box.append("[WARNING] Failed unlock attempt.")

def start_gui():
    app = QApplication(sys.argv)
    window = Dashboard()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    start_gui()