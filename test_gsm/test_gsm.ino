/*
 * Blackbox Sentinel - GSM Final Locked Test
 * Board: Heltec ESP32 V3
 */

#include <U8g2lib.h>
#include <Wire.h>

#define GSM_RX_PIN 47 // Safe isolated pin
#define GSM_TX_PIN 48 // Safe isolated pin

#define OLED_SDA 17
#define OLED_SCL 18
#define OLED_RST 21

U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, /* reset=*/ OLED_RST, /* clock=*/ OLED_SCL, /* data=*/ OLED_SDA);

unsigned long lastSendTime = 0;

void setup() {
  pinMode(36, OUTPUT);
  digitalWrite(36, LOW); 
  delay(50);

  Wire.begin(OLED_SDA, OLED_SCL);
  u8g2.begin();
  u8g2.setFont(u8g2_font_ncenB08_tr);
  
  u8g2.clearBuffer();
  u8g2.drawStr(5, 15, "Testing 115200...");
  u8g2.sendBuffer();

  // Removed INPUT_PULLUP because it interfered with the capacitance fix.

  // We KNOW it is 115200 now!
  Serial1.begin(115200, SERIAL_8N1, GSM_RX_PIN, GSM_TX_PIN);
  delay(2000);
}

void loop() {
  if (millis() - lastSendTime > 1000) {
    
    // Clear buffer
    while(Serial1.available()) Serial1.read();
    
    // Send AT Command
    Serial1.println("AT");
    lastSendTime = millis();
    
    unsigned long timeout = millis() + 500;
    String response = "";
    
    while (millis() < timeout) {
      while (Serial1.available()) {
        char c = Serial1.read();
        if (c >= 32 && c <= 126) {
          response += c;
        }
      }
    }
    
    if (response.indexOf("OK") != -1 || response.indexOf("ok") != -1 || response.indexOf("0") != -1) {
      u8g2.clearBuffer();
      u8g2.drawStr(5, 15, "CONNECTION SOLID!");
      u8g2.setCursor(5, 35);
      u8g2.print("Baud: 115200");
      u8g2.drawStr(5, 55, "Ready for Next Step");
      u8g2.sendBuffer();
      
      // Stop looping on success
      while(true) { delay(1000); }
    } else {
      u8g2.clearBuffer();
      u8g2.drawStr(5, 15, "Testing 115200...");
      u8g2.setCursor(5, 35);
      u8g2.print("Wiggle the wires...");
      u8g2.sendBuffer();
    }
  }
}
