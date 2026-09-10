/*
 * Blackbox Sentinel - MASTER FIRMWARE
 * Board: Heltec ESP32 V3
 * 
 * Hardware Responsibilities:
 * 1. Physical Layer 2 isolation (Relay cut-off)
 * 2. Chassis Tamper monitoring (Limit Switch)
 * 3. Out-of-band alerts (SIM800L GSM Module)
 * 4. UART5 Bridge to ML Engine (Raspberry Pi)
 */

#include <U8g2lib.h>
#include <Wire.h>
#include <Preferences.h>

Preferences preferences;

// ==========================================
// 🚨 USER CONFIGURATION - EDIT THESE! 🚨
// ==========================================

// This is the default emergency phone number if one hasn't been set yet.
String EMERGENCY_PHONE = "+919914551405";

// Tamper Switch Logic:
// The user specified: "when it is pressed it is closed".
// Since the lid presses the switch when secure, it is closed (LOW) when safe.
// When the lid is removed, the switch opens, and the internal PULLUP pulls it to HIGH.
#define TAMPER_TRIGGER_STATE HIGH 

// ==========================================
// PIN DEFINITIONS
// ==========================================
// Raspberry Pi Bridge UART (Serial2)
#define PI_RX_PIN 19
#define PI_TX_PIN 20

// SIM800L GSM UART (Serial1)
#define GSM_RX_PIN 44
#define GSM_TX_PIN 43

// Hardware Defense Pins
#define LIMIT_SWITCH_PIN 14
#define RELAY_PIN 4
#define PRG_BUTTON_PIN 0 // Built-in "PRG" button on Heltec ESP32 V3

// OLED I2C Pins
#define OLED_SDA 17
#define OLED_SCL 18
#define OLED_RST 21

// ==========================================
// GLOBAL STATE
// ==========================================
U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, /* reset=*/ OLED_RST, /* clock=*/ OLED_SCL, /* data=*/ OLED_SDA);

bool isAirGapped = false;
unsigned long lastGsmInit = 0;

void setup() {
  // Power up OLED explicitly for Heltec V3
  pinMode(36, OUTPUT);
  digitalWrite(36, LOW); 
  delay(50);

  // Initialize Screen
  Wire.begin(OLED_SDA, OLED_SCL);
  u8g2.begin();
  u8g2.setFont(u8g2_font_ncenB08_tr);

  // Initialize Defense Hardware
  pinMode(LIMIT_SWITCH_PIN, INPUT_PULLUP);
  // To safely turn OFF a 5V Active-Low relay with a 3.3V ESP32, 
  // we must float the pin (INPUT) instead of driving it HIGH (3.3V), 
  // because 3.3V is not high enough to turn the 5V relay off!
  pinMode(RELAY_PIN, INPUT); // Floating = Relay OFF (Network Flowing)

  // Load saved phone number from flash memory
  preferences.begin("sentinel", false);
  String savedPhone = preferences.getString("phone", "");
  if (savedPhone.length() > 0) {
      EMERGENCY_PHONE = savedPhone;
  }

  // Initialize USB Debug Serial
  Serial.begin(115200);

  // Initialize GSM Shield (Serial1)
  Serial1.begin(115200, SERIAL_8N1, GSM_RX_PIN, GSM_TX_PIN);

  // Initialize Raspberry Pi Bridge (Serial2)
  Serial2.begin(115200, SERIAL_8N1, PI_RX_PIN, PI_TX_PIN);

  // Boot sequence complete
  updateOLED("SYSTEM ARMED", "All Sensors Live");
  Serial.println("\n=== BLACKBOX SENTINEL : MASTER FIRMWARE ===");
  Serial.println("System Armed. Monitoring...");
}

// Helper to quickly draw to OLED
void updateOLED(String line1, String line2) {
  u8g2.clearBuffer();
  u8g2.drawStr(5, 15, line1.c_str());
  u8g2.drawStr(5, 35, line2.substring(0, 15).c_str()); // Prevent off-screen wrap
  u8g2.sendBuffer();
}

// Master Isolation Function
void triggerIsolate(String reason) {
  if (isAirGapped) return; // Already triggered, do nothing
  
  isAirGapped = true;
  
  // 1. Physically cut the network relay!
  // To turn it ON, we drive it to GROUND (0V)
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW); 
  
  // 2. Update screen
  updateOLED("!! ISOLATED !!", reason);
  Serial.println("\n🚨 CRITICAL EVENT: " + reason);
  Serial.println("🚨 RELAY AIR-GAPPED!");

  // 3. Send out-of-band SMS via GSM
  Serial1.println("AT+CMGF=1"); // Set text mode
  delay(200);
  Serial1.println("AT+CMGS=\"" + EMERGENCY_PHONE + "\""); 
  delay(200);
  Serial1.print("BLACKBOX ALERT: " + reason + " - NETWORK AIR-GAPPED."); 
  delay(200);
  Serial1.write(26); // ASCII Ctrl+Z to send the SMS
  
  Serial.println("🚨 SMS DISPATCHED.");
}

void loop() {
  // ==========================================
  // 1. PHYSICAL TAMPER MONITOR
  // ==========================================
  if (digitalRead(LIMIT_SWITCH_PIN) == TAMPER_TRIGGER_STATE) {
      triggerIsolate("CHASSIS TAMPER");
  }

  // ==========================================
  // 2. ML THREAT MONITOR (From Raspberry Pi)
  // ==========================================
  if (Serial2.available()) {
      String msg = Serial2.readStringUntil('\n');
      msg.trim();
      
      Serial.println("Pi Bridge Rx: " + msg);
      
      // If the Pi transmits an explicit threat classification
      if (msg.indexOf("ANOMALY") >= 0 || msg.indexOf("THREAT") >= 0) {
          triggerIsolate("ML THREAT DETECT");
      }
      
      // If the Pi dynamically updates the phone number
      else if (msg.startsWith("SET_PHONE:")) {
          EMERGENCY_PHONE = msg.substring(10);
          EMERGENCY_PHONE.trim();
          preferences.putString("phone", EMERGENCY_PHONE); // Save to flash!
          
          updateOLED("PHONE UPDATED", EMERGENCY_PHONE);
          Serial.println("✅ New Phone Number Saved: " + EMERGENCY_PHONE);
          delay(2000);
          updateOLED("SYSTEM ARMED", "Monitoring...");
      }
  }

  // ==========================================
  // 3. GSM INCOMING SMS MONITOR
  // ==========================================
  if (Serial1.available()) {
      String msg = Serial1.readStringUntil('\n');
      msg.trim();
      if (msg.length() > 0) {
         Serial.println("GSM Rx: " + msg);
         Serial2.println("GSM: " + msg); // Forward to Pi
      }
  }

  // ==========================================
  // 4. SECRET PHYSICAL DISARM (PRG BUTTON)
  // ==========================================
  // Holding the physical 'PRG' button on the Heltec restores the system
  if (digitalRead(PRG_BUTTON_PIN) == LOW) {
      if (isAirGapped) {
          isAirGapped = false;
          pinMode(RELAY_PIN, INPUT); // Restore network relay (Float = OFF)
          
          updateOLED("SYSTEM DISARMED", "Relay Restored");
          Serial.println("⚠️ SYSTEM DISARMED LOCALLY. RELAY RESTORED.");
          
          delay(2000); // Debounce / read time
          
          // Re-arm
          updateOLED("SYSTEM ARMED", "Monitoring...");
      }
  }
}
