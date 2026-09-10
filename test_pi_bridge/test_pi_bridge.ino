/*
 * Blackbox Sentinel - ESP32 <-> Raspberry Pi UART Bridge
 * Board: Heltec ESP32 V3
 */

#include <U8g2lib.h>
#include <Wire.h>

// --- USER CONFIGURABLE PINS ---
#define PI_RX_PIN 19
#define PI_TX_PIN 20

// OLED Pins
#define OLED_SDA 17
#define OLED_SCL 18
#define OLED_RST 21

U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, /* reset=*/ OLED_RST, /* clock=*/ OLED_SCL, /* data=*/ OLED_SDA);

void setup() {
  // Power up OLED
  pinMode(36, OUTPUT);
  digitalWrite(36, LOW); 
  delay(50);

  Wire.begin(OLED_SDA, OLED_SCL);
  u8g2.begin();
  u8g2.setFont(u8g2_font_ncenB08_tr);

  // Initialize USB Serial (For your PC)
  Serial.begin(115200);

  // Initialize Hardware Serial 2 (For the Raspberry Pi)
  Serial2.begin(115200, SERIAL_8N1, PI_RX_PIN, PI_TX_PIN);

  u8g2.clearBuffer();
  u8g2.drawStr(5, 15, "PI BRIDGE ACTIVE");
  u8g2.drawStr(5, 35, "Listening on UART2...");
  u8g2.sendBuffer();
}

void loop() {
  // If the Raspberry Pi sends us a message, print it to the OLED and PC!
  if (Serial2.available()) {
    String piMessage = Serial2.readStringUntil('\n');
    
    Serial.println("From Pi: " + piMessage);
    
    u8g2.clearBuffer();
    u8g2.drawStr(5, 15, "MSG FROM PI:");
    u8g2.setCursor(5, 35);
    u8g2.print(piMessage.substring(0, 15)); // Print first 15 chars to OLED
    u8g2.sendBuffer();
  }

  // If you type something in the PC Serial Monitor, send it to the Pi!
  if (Serial.available()) {
    String myMessage = Serial.readStringUntil('\n');
    Serial2.println(myMessage);
    
    u8g2.clearBuffer();
    u8g2.drawStr(5, 15, "SENT TO PI:");
    u8g2.setCursor(5, 35);
    u8g2.print(myMessage.substring(0, 15));
    u8g2.sendBuffer();
  }
}
