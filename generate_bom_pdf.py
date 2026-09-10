from fpdf import FPDF
import os

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'BlackBox Sentinel - Complete Hardware Checklist', 0, 1, 'C')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 10, 'Target: Patent-Scope Architecture (Pi 3B Budget Route)', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def create_pdf():
    pdf = PDF()
    pdf.add_page()
    
    categories = [
        {
            "title": "1. Core Processing & Display",
            "items": [
                "[ ] Raspberry Pi 3 Model B (or Pi 4 if preferred)",
                "[ ] 3.5\" or 4\" SPI Touchscreen Display for Raspberry Pi",
                "[ ] Raspberry Pi 5V Power Supply (Micro-USB for Pi 3, Type-C for Pi 4)",
                "[ ] MicroSD Card (32GB or 64GB, Class 10)"
            ]
        },
        {
            "title": "2. Network Infrastructure",
            "items": [
                "[ ] USB-to-Ethernet (RJ45) Adapter (Generic 10/100 is fine)",
                "[ ] MT7601U USB Wi-Fi Adapter (For Monitor Mode packet capture)",
                "[ ] Standard Ethernet Patch Cables (x2)"
            ]
        },
        {
            "title": "3. 'Trusted Controller' (Patent-Scope Hardware)",
            "items": [
                "[ ] ESP32-S3 or ESP32 LoRa SX1278 (with OLED)",
                "[ ] 1-Channel 5V Relay Module (Opto-isolated)",
                "[ ] SMARTELEX GSM/GPRS Shield or SIM800L Module",
                "[ ] Pass-Through USB Power Bank (To act as UPS Hold-Up Power)"
            ]
        },
        {
            "title": "4. Anti-Tamper & Prototyping Consumables",
            "items": [
                "[ ] Zippy Limit Switches or 4-Pin Tactile Push Buttons (x3)",
                "[ ] Breadboard (Large 830 tie-points)",
                "[ ] Dotted Single-Sided PCB (Perfboard) (x2)",
                "[ ] Jumper Wires (M-M, M-F, F-F) (1 Pack each)",
                "[ ] Standard Resistors (10k Ohm and 4.7k Ohm) (x10 each)"
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
    pdf.cell(0, 10, "Notes for the Lab Assistant:", 0, 1, 'L')
    pdf.set_font('Arial', 'I', 10)
    pdf.set_text_color(50, 50, 50)
    pdf.multi_cell(0, 6, "Check the 'ESP32 LoRa' boards for the Trusted Controller. Ask for any generic limit switches for the enclosure tamper detection. If a 15W official Pi power supply is available, prioritize that for testing stability.")

    out_path = r"c:\Users\prajw\Downloads\BlackBox_Sentinel_Hardware_Checklist.pdf"
    pdf.output(out_path)
    print(f"PDF saved to: {out_path}")

if __name__ == "__main__":
    create_pdf()
