import sys
import random
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
from PyQt6.QtCore import QTimer

class Dashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        # Set the window title and size
        self.setWindowTitle("BlackBox Sentinel - Dashboard")
        self.setGeometry(100, 100, 400, 300)

        # Create a layout to stack items vertically
        layout = QVBoxLayout()

        # 1. Create a Status Label
        self.status_label = QLabel("STATUS: IDLE")
        self.status_label.setStyleSheet("font-size: 24px; color: green; font-weight: bold;")
        layout.addWidget(self.status_label)

        # 2. Create a Traffic Label
        self.traffic_label = QLabel("Traffic: 0 packets/sec")
        self.traffic_label.setStyleSheet("font-size: 18px;")
        layout.addWidget(self.traffic_label)

        # Apply the layout to the main window
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # 3. Create a Timer for Dummy Data
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_dummy_data)
        self.timer.start(1000) # Updates every 1000 milliseconds (1 second)

    def update_dummy_data(self):
        # Generate a random number to simulate network packets
        fake_traffic = random.randint(10, 150)
        self.traffic_label.setText(f"Traffic: {fake_traffic} packets/sec")

def start_gui():
    app = QApplication(sys.argv)
    window = Dashboard()
    window.show()
    sys.exit(app.exec())

# This allows you to test the GUI directly
if __name__ == "__main__":
    start_gui()