from fpdf import FPDF
import os

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'BlackBox Sentinel - Complete Hardware Checklist', 0, 1, 'C')
        self.set_font('Arial', 'B', 11)
        self.set_text_color(200, 0, 0)
        self.cell(0, 10, 'TARGET: Patent-Scope Architecture (Raspberry Pi 4 Build)', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(0, 0, 0)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def create_pdf():
    pdf = PDF()
    pdf.add_page()
    
    categories = [
        {
            "title": "1. Core Computing & Display",
            "items": [
                "[ ] Raspberry Pi 4 Model B (8GB RAM)",
                "[ ] Official Raspberry Pi 4 Power Supply (15W / Type-C)",
                "[ ] Raspberry Pi 4 Cooling Case with Fan",
                "[ ] 3.5\" or 4\" SPI Touchscreen Display for Raspberry Pi",
                "[ ] MicroSD Card (32GB or 64GB, Class 10/A1) (x2)"
            ]
        },
        {
            "title": "2. Network & Packet Capture Infrastructure",
            "items": [
                "[ ] USB-to-Ethernet (RJ45) Adapter (Gigabit) (For the inline bridge)",
                "[ ] MT7601U USB Wi-Fi Adapter (For isolated monitor-mode packet capture)",
                "[ ] Standard Ethernet Patch Cables (x2)"
            ]
        },
        {
            "title": "3. 'Trusted Controller' & Patent-Scope Hardware",
            "items": [
                "[ ] ESP32-S3 DevKitC-1 OR ESP32 LoRa SX1278 (with OLED)",
                "[ ] Raspberry Pi UPS HAT (Uninterruptible Power Supply) 5V/3A",
                "[ ] 18650 Lithium-Ion Batteries (x2) (To power the UPS HAT)",
                "[ ] 1-Channel 5V Relay Module (Opto-isolated)",
                "[ ] SIM800L GPRS/GSM Breakout Module OR GSM/GPRS Arduino Shield"
            ]
        },
        {
            "title": "4. Anti-Tamper & Prototyping Consumables",
            "items": [
                "[ ] Zippy Limit Switches OR 4-Pin Tactile Push Buttons (x3)",
                "[ ] Large Breadboard (830 tie-points)",
                "[ ] Dotted Single-Sided PCB (Perfboard) (x2)",
                "[ ] Jumper Wires (Male-to-Male, Male-to-Female, Female-to-Female)",
                "[ ] Standard Resistors (10k Ohm and 4.7k Ohm) (x10 each)",
                "[ ] Large Electrolytic Capacitor (1000 uF) (If using bare SIM800L module)"
            ]
        }
    ]

    for cat in categories:
        pdf.set_font('Arial', 'B', 12)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 10, cat["title"], 0, 1, 'L')
        
        pdf.set_font('Arial', '', 11)
        pdf.set_text_color(0, 0, 0)
        for item in cat["items"]:
            pdf.cell(10) # Indent
            pdf.cell(0, 8, item, 0, 1, 'L')
        pdf.ln(5)

    # Add a notes section
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 10, "Instructions:", 0, 1, 'L')
    pdf.set_font('Arial', 'I', 10)
    pdf.set_text_color(50, 50, 50)
    pdf.multi_cell(0, 6, "Check this entire list against the college inventory. Whatever you CANNOT find in the lab (likely the USB-Ethernet adapter, MT7601U WiFi, and the UPS HAT), you must purchase yourself to fulfill the patent-scope requirements.")

    out_path = r"c:\Users\prajw\Downloads\BlackBox_Sentinel_Pi4_BOM.pdf"
    pdf.output(out_path)
    print(f"PDF saved to: {out_path}")

if __name__ == "__main__":
    create_pdf()
