/*
 * Blackbox Sentinel - Hardware Test Firmware v2
 * Board: Heltec ESP32 V3 (HTIT-WB32LAF)
 * 
 * Features:
 * 1. Clicks the Relay on and off every 3 seconds.
 * 2. Displays status on the built-in OLED screen.
 */

#include <U8g2lib.h>
#include <Wire.h>

// --- Pin Definitions ---
const int RELAY_PIN = 4;
const int TAMPER_SW1_PIN = 5;
const int TAMPER_SW2_PIN = 6;

// Heltec V3 OLED Pins
#define OLED_SDA 17
#define OLED_SCL 18
#define OLED_RST 21

// Initialize the OLED display using U8g2
U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, /* reset=*/ OLED_RST, /* clock=*/ OLED_SCL, /* data=*/ OLED_SDA);

void setup() {
  Serial.begin(115200);
  
  // Initialize Relay
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, HIGH); 
  
  // Initialize Display
  Wire.begin(OLED_SDA, OLED_SCL);
  u8g2.begin();
  
  // Show Boot Screen
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_ncenB10_tr);
  u8g2.drawStr(10, 25, "BLACKBOX");
  u8g2.drawStr(10, 45, "SENTINEL");
  u8g2.sendBuffer();
  
  delay(2000); // Hold boot screen
}

void loop() {
  static unsigned long lastRelayToggle = 0;
  static bool relayState = HIGH;

  if (millis() - lastRelayToggle > 3000) {
    lastRelayToggle = millis();
    relayState = !relayState;
    digitalWrite(RELAY_PIN, relayState);
    
    // Update the OLED Display
    u8g2.clearBuffer();
    u8g2.setFont(u8g2_font_ncenB10_tr);
    u8g2.drawStr(5, 20, "SYSTEM LIVE");
    
    u8g2.setFont(u8g2_font_ncenB14_tr);
    if(relayState == LOW) {
      Serial.println("Relay Triggered (CUT)");
      u8g2.drawStr(10, 50, "RELAY: CUT!");
    } else {
      Serial.println("Relay Restored (SAFE)");
      u8g2.drawStr(10, 50, "RELAY: SAFE");
    }
    u8g2.sendBuffer();
  }
}
