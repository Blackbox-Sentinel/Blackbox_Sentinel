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
#include <ArduinoJson.h>
#include <Ed25519.h>

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
#define GSM_RX_PIN 47
#define GSM_TX_PIN 48

// Hardware Defense Pins
#define LIMIT_SWITCH_PIN 14
#define RELAY1_PIN 4  // Channel 1 of the new 2-Channel Relay
#define RELAY2_PIN 5  // Channel 2 of the new 2-Channel Relay
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
  pinMode(RELAY1_PIN, INPUT); // Floating = Relay 1 OFF (Network Flowing)
  pinMode(RELAY2_PIN, INPUT); // Floating = Relay 2 OFF

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



  // Initialize Raspberry Pi Bridge (Serial2) - 1024 byte buffer for full receipt payload
  Serial2.setRxBufferSize(1024);
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
  pinMode(RELAY1_PIN, OUTPUT);
  digitalWrite(RELAY1_PIN, LOW); 
  
  pinMode(RELAY2_PIN, OUTPUT);
  digitalWrite(RELAY2_PIN, LOW); 
  
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



// Trusted Public Key (Base64Url: 3pYnfYvnsd1MUrke1J6MqIj6xd0Dra2kHgrErkz7ids)
const uint8_t TRUSTED_PUB_KEY[32] = {
    0xde, 0x96, 0x27, 0x7d, 0x8b, 0xe7, 0xb1, 0xdd, 0x4c, 0x52, 0xb9, 0x1e, 0xd4, 0x9e, 0x8c, 0xa8, 
    0x88, 0xfa, 0xc5, 0xdd, 0x03, 0xad, 0xad, 0xa4, 0x1e, 0x0a, 0xc4, 0xae, 0x4c, 0xfb, 0x89, 0xdb
};

int base64UrlDecode(const char* input, uint8_t* output) {
    int in_len = strlen(input);
    int out_len = 0;
    int i = 0;
    uint32_t val = 0;
    int valb = -8;
    while (i < in_len) {
        char c = input[i++];
        if (c == '-' || c == '_' || (c >= '0' && c <= '9') || (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z')) {
            uint8_t d;
            if (c >= 'A' && c <= 'Z') d = c - 'A';
            else if (c >= 'a' && c <= 'z') d = c - 'a' + 26;
            else if (c >= '0' && c <= '9') d = c - '0' + 52;
            else if (c == '-') d = 62;
            else if (c == '_') d = 63;
            val = (val << 6) + d;
            valb += 6;
            if (valb >= 0) {
                output[out_len++] = (val >> valb) & 0xFF;
                valb -= 8;
            }
        }
    }
    return out_len;
}

void processC2Message(String msg) {
      if (msg.startsWith("{")) {
          updateOLED("JSON RX", "Verifying...");
          // Parse as JSON for Ed25519 Signed Receipt
          JsonDocument doc;
          DeserializationError err = deserializeJson(doc, msg);
          if (!err) {
              const char* sig_b64 = doc["signature"];
              JsonVariant payload = doc["payload"];
              
              if (sig_b64 && !payload.isNull()) {
                  // Build canonical JSON with sorted keys (must match Python sort_keys=True)
                  // Keys in alphabetical order: algorithm, controller_id, decision, event_hash,
                  // evidence_digest, incident_id, key_epoch, organization_id, quorum,
                  // receipt_sequence, receipt_version, timestamp
                  String payload_str = "{";
                  const char* sorted_keys[] = {
                      "algorithm", "controller_id", "decision", "event_hash",
                      "evidence_digest", "incident_id", "key_epoch", "organization_id",
                      "quorum", "receipt_sequence", "receipt_version", "timestamp"
                  };
                  bool first = true;
                  for (int k = 0; k < 12; k++) {
                      if (payload[sorted_keys[k]].isNull()) continue;
                      if (!first) payload_str += ",";
                      first = false;
                      payload_str += "\"";
                      payload_str += sorted_keys[k];
                      payload_str += "\":";
                      if (payload[sorted_keys[k]].is<const char*>()) {
                          payload_str += "\"";
                          payload_str += payload[sorted_keys[k]].as<const char*>();
                          payload_str += "\"";
                      } else {
                          payload_str += payload[sorted_keys[k]].as<String>();
                      }
                  }
                  payload_str += "}";
                  
                  Serial.println("Canonical: " + payload_str);
                  
                  // Decode signature
                  uint8_t sig[64];
                  int sig_len = base64UrlDecode(sig_b64, sig);
                  
                  if (sig_len == 64) {
                      bool isValid = Ed25519::verify(sig, TRUSTED_PUB_KEY, payload_str.c_str(), payload_str.length());
                      if (isValid) {
                          const char* decision = payload["decision"];
                          if (decision && strcmp(decision, "CONTAIN") == 0) {
                              if (isAirGapped) {
                                  updateOLED("!! ISOLATED !!", "SECURE CONTAIN");
                              } else {
                                  triggerIsolate("SECURE CONTAIN");
                              }
                          } else {
                              updateOLED("REJECTED", "Not CONTAIN");
                              Serial.println("Signature valid, but decision not CONTAIN.");
                          }
                      } else {
                          updateOLED("REJECTED SIG", "Invalid Ed25519");
                          Serial.println("🚨 INVALID Ed25519 SIGNATURE DETECTED! IGNORING COMMAND.");
                      }
                  } else {
                      updateOLED("REJECTED", "Bad Sig Len");
                      Serial.println("Signature length mismatch.");
                  }
              } else {
                  updateOLED("REJECTED", "Missing Fields");
              }
          } else {
              updateOLED("JSON ERROR", err.c_str());
          }
          delay(2000); // Give user time to read the OLED before loop continues
          if (!isAirGapped) {
              updateOLED("SYSTEM ARMED", "Monitoring...");
          } else {
              updateOLED("!! ISOLATED !!", "SECURE CONTAIN");
          }
      }
      // If the Pi dynamically updates the phone number
      else if (msg.startsWith("SET_PHONE:")) {
          EMERGENCY_PHONE = msg.substring(10);
          EMERGENCY_PHONE.trim();
          preferences.putString("phone", EMERGENCY_PHONE); // Save to flash!
          
          updateOLED("PHONE SAVED", EMERGENCY_PHONE.c_str());
          Serial.println("Updated Emergency Number: " + EMERGENCY_PHONE);
          delay(2000);
          if (!isAirGapped) updateOLED("SYSTEM ARMED", "Monitoring...");
      }
      else {
          // If it's a simple legacy command without JSON signing, REJECT it.
          Serial.println("🚨 RAW COMMAND REJECTED. MUST BE SIGNED JSON.");
          updateOLED("REJECTED", "Unsigned");
          delay(2000);
          if (!isAirGapped) updateOLED("SYSTEM ARMED", "Monitoring...");
      }
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
      processC2Message(msg);
  }

  // ==========================================
  // 3. GSM INCOMING SMS MONITOR
  // ==========================================
  /*
  if (Serial1.available()) {
      String msg = Serial1.readStringUntil('\n');
      msg.trim();
      if (msg.length() > 0) {
         Serial.println("GSM Rx: " + msg);
         Serial2.println("GSM: " + msg); // Forward to Pi
      }
  }
  */

  // ==========================================
  // 4. SECRET PHYSICAL DISARM (PRG BUTTON)
  // ==========================================
  // Holding the physical 'PRG' button on the Heltec restores the system
  if (digitalRead(PRG_BUTTON_PIN) == LOW) {
      if (isAirGapped) {
          isAirGapped = false;
          pinMode(RELAY1_PIN, INPUT); // Restore network relay (Float = OFF)
          pinMode(RELAY2_PIN, INPUT); // Restore second relay (Float = OFF)
          
          updateOLED("SYSTEM DISARMED", "Relay Restored");
          Serial.println("⚠️ SYSTEM DISARMED LOCALLY. RELAY RESTORED.");
          
          delay(2000); // Debounce / read time
          
          // Re-arm
          updateOLED("SYSTEM ARMED", "Monitoring...");
      }
  }
}
