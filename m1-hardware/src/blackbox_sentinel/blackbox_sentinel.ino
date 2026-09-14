/*
 * Blackbox Sentinel - MASTER FIRMWARE v2.1
 * Board: Heltec ESP32 V3
 * 
 * Hardware Responsibilities:
 * 1. Physical Layer 2 isolation (Relay cut-off)
 * 2. Chassis Tamper monitoring (Limit Switch)
 * 3. Out-of-band alerts (SIM800L GSM Module)
 * 4. UART5 Bridge to ML Engine (Raspberry Pi)
 * 
 * v2.1 CHANGES:
 * - All status responses now sent over BOTH Serial (USB debug) AND Serial2 (Pi bridge)
 * - Added heartbeat every 5s over Serial2 so Pi can confirm link is alive
 * - OLED rotation fixed (U8G2_R1 = 90deg CW for vertical mount)
 */

#include <U8g2lib.h>
#include <Wire.h>
#include <Preferences.h>
#include <ArduinoJson.h>
#include <Ed25519.h>

Preferences preferences;

// ==========================================
// USER CONFIGURATION
// ==========================================
String EMERGENCY_PHONE = "+919914551405";

// Tamper Switch Logic:
// Switch is CLOSED (LOW) when lid is secure.
// Switch OPENS (HIGH) when lid is removed -> HIGH = tamper
#define TAMPER_TRIGGER_STATE HIGH 

// ==========================================
// PIN DEFINITIONS
// ==========================================
// Raspberry Pi Bridge UART (Serial2)
#define PI_RX_PIN 19   // ESP32 RX <- Pi GPIO12 TX
#define PI_TX_PIN 20   // ESP32 TX -> Pi GPIO13 RX

// SIM800L GSM UART (Serial1)
#define GSM_RX_PIN 47
#define GSM_TX_PIN 48

// Hardware Defense Pins
#define LIMIT_SWITCH_PIN 14
#define RELAY1_PIN 4   // Channel 1 - Active-Low relay
#define RELAY2_PIN 5   // Channel 2 - Active-Low relay
#define PRG_BUTTON_PIN 0  // Built-in PRG button

// OLED I2C Pins (Heltec V3)
#define OLED_SDA 17
#define OLED_SCL 18
#define OLED_RST 21

// ==========================================
// GLOBAL STATE
// ==========================================
// U8G2_R1 = 90 degree rotation for vertical OLED mount
U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R1, /* reset=*/ OLED_RST, /* clock=*/ OLED_SCL, /* data=*/ OLED_SDA);

bool isAirGapped = false;
unsigned long lastHeartbeat = 0;
unsigned long lastGsmInit = 0;

// ==========================================
// HELPER: Print to BOTH serial ports
// ==========================================
void serialBoth(String msg) {
  Serial.println(msg);
  Serial2.println(msg);
}

// ==========================================
// OLED HELPER
// ==========================================
void updateOLED(String line1, String line2) {
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_ncenB08_tr);
  u8g2.drawStr(5, 15, line1.c_str());
  u8g2.drawStr(5, 35, line2.substring(0, 15).c_str());
  u8g2.sendBuffer();
}

// ==========================================
// MASTER ISOLATION FUNCTION
// ==========================================
void triggerIsolate(String reason) {
  if (isAirGapped) return;
  
  isAirGapped = true;
  
  // Cut the relay (Active-Low: OUTPUT + LOW = relay ON = network cut)
  pinMode(RELAY1_PIN, OUTPUT);
  digitalWrite(RELAY1_PIN, LOW); 
  pinMode(RELAY2_PIN, OUTPUT);
  digitalWrite(RELAY2_PIN, LOW); 
  
  updateOLED("!! ISOLATED !!", reason);
  
  // Notify BOTH USB debug serial AND Pi over Serial2
  serialBoth("{\"event\":\"relay_isolated\",\"reason\":\"" + reason + "\"}");

  // Send out-of-band SMS via SIM800L
  Serial1.println("AT+CMGF=1");
  delay(200);
  Serial1.println("AT+CMGS=\"" + EMERGENCY_PHONE + "\""); 
  delay(200);
  Serial1.print("BLACKBOX ALERT: " + reason + " - NETWORK AIR-GAPPED."); 
  delay(200);
  Serial1.write(26); // Ctrl+Z to send SMS
  
  serialBoth("{\"event\":\"sms_dispatched\",\"phone\":\"" + EMERGENCY_PHONE + "\"}");
}

// ==========================================
// TRUSTED PUBLIC KEY (Ed25519)
// Base64Url: ZI48kNsD__8q2Sp_LJLRzT4W8Iaku8DsmG95Myov66k
// ==========================================
const uint8_t TRUSTED_PUB_KEY[32] = {
    0x5e, 0x4b, 0xb8, 0x49, 0x13, 0x0e, 0x57, 0x3b, 0x14, 0x14, 0x64, 0x5f, 0x19, 0xa0, 0xc9, 0x1b,
    0xa4, 0xe2, 0xb2, 0x63, 0xd7, 0x44, 0xd8, 0xc0, 0x68, 0xc7, 0x36, 0xd1, 0xf5, 0xd3, 0xb6, 0x5b
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

// ==========================================
// PI C2 COMMAND PROCESSOR
// ==========================================
void processC2Message(String msg) {
    if (msg.startsWith("{")) {
        updateOLED("JSON RX", "Verifying...");
        serialBoth("{\"event\":\"receipt_received\",\"len\":" + String(msg.length()) + "}");

        JsonDocument doc;
        DeserializationError err = deserializeJson(doc, msg);
        if (!err) {
            const char* sig_b64 = doc["signature"];
            JsonVariant payload = doc["payload"];
            
            if (sig_b64 && !payload.isNull()) {
                // Build canonical JSON (sorted keys, must match Python sort_keys=True)
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
                
                // Decode and verify signature
                uint8_t sig[64];
                int sig_len = base64UrlDecode(sig_b64, sig);
                
                if (sig_len == 64) {
                    bool isValid = Ed25519::verify(sig, TRUSTED_PUB_KEY, payload_str.c_str(), payload_str.length());
                    if (isValid) {
                        const char* decision = payload["decision"];
                        if (decision && strcmp(decision, "CONTAIN") == 0) {
                            serialBoth("{\"event\":\"sig_valid\",\"action\":\"ISOLATING\"}");
                            if (isAirGapped) {
                                updateOLED("!! ISOLATED !!", "ALREADY DONE");
                            } else {
                                triggerIsolate("SECURE CONTAIN");
                            }
                        } else {
                            serialBoth("{\"event\":\"sig_valid\",\"action\":\"REJECTED_NOT_CONTAIN\"}");
                            updateOLED("REJECTED", "Not CONTAIN");
                        }
                    } else {
                        serialBoth("{\"event\":\"sig_invalid\",\"reason\":\"BAD_ED25519\"}");
                        updateOLED("REJECTED SIG", "Invalid Ed25519");
                    }
                } else {
                    serialBoth("{\"event\":\"sig_invalid\",\"reason\":\"BAD_SIG_LEN\",\"len\":" + String(sig_len) + "}");
                    updateOLED("REJECTED", "Bad Sig Len");
                }
            } else {
                serialBoth("{\"event\":\"parse_error\",\"reason\":\"MISSING_FIELDS\"}");
                updateOLED("REJECTED", "Missing Fields");
            }
        } else {
            serialBoth("{\"event\":\"json_error\",\"reason\":\"" + String(err.c_str()) + "\"}");
            updateOLED("JSON ERROR", err.c_str());
        }
        delay(2000);
        if (!isAirGapped) {
            updateOLED("SYSTEM ARMED", "Monitoring...");
        } else {
            updateOLED("!! ISOLATED !!", "SECURE CONTAIN");
        }
    }
    else if (msg.startsWith("SET_PHONE:")) {
        EMERGENCY_PHONE = msg.substring(10);
        EMERGENCY_PHONE.trim();
        preferences.putString("phone", EMERGENCY_PHONE);
        updateOLED("PHONE SAVED", EMERGENCY_PHONE.c_str());
        serialBoth("{\"event\":\"phone_updated\",\"phone\":\"" + EMERGENCY_PHONE + "\"}");
        delay(2000);
        if (!isAirGapped) updateOLED("SYSTEM ARMED", "Monitoring...");
    }
    else if (msg == "PING") {
        // Simple connectivity check - respond with status
        serialBoth("{\"event\":\"pong\",\"isolated\":" + String(isAirGapped ? "true" : "false") + ",\"tamper\":" + String(digitalRead(LIMIT_SWITCH_PIN) == HIGH ? "true" : "false") + "}");
    }
    else {
        serialBoth("{\"event\":\"rejected\",\"reason\":\"UNSIGNED_CMD\"}");
        updateOLED("REJECTED", "Unsigned");
        delay(2000);
        if (!isAirGapped) updateOLED("SYSTEM ARMED", "Monitoring...");
    }
}

// ==========================================
// SETUP
// ==========================================
void setup() {
  // Power up OLED for Heltec V3
  pinMode(36, OUTPUT);
  digitalWrite(36, LOW); 
  delay(50);

  Wire.begin(OLED_SDA, OLED_SCL);
  u8g2.begin();

  // Initialize Defense Hardware
  pinMode(LIMIT_SWITCH_PIN, INPUT_PULLUP);
  pinMode(RELAY1_PIN, INPUT);  // Floating = relay OFF (network flowing)
  pinMode(RELAY2_PIN, INPUT);

  // Load saved phone from flash
  preferences.begin("sentinel", false);
  String savedPhone = preferences.getString("phone", "");
  if (savedPhone.length() > 0) {
      EMERGENCY_PHONE = savedPhone;
  }

  // USB Debug Serial
  Serial.begin(115200);

  // GSM Shield (Serial1)
  Serial1.begin(115200, SERIAL_8N1, GSM_RX_PIN, GSM_TX_PIN);

  // Pi Bridge (Serial2) - 1024 byte RX buffer for full receipt payloads
  Serial2.setRxBufferSize(1024);
  Serial2.begin(115200, SERIAL_8N1, PI_RX_PIN, PI_TX_PIN);

  updateOLED("SYSTEM ARMED", "All Sensors Live");

  // Send boot message on BOTH ports
  serialBoth("{\"event\":\"boot\",\"firmware\":\"v2.1\",\"phone\":\"" + EMERGENCY_PHONE + "\"}");
}

// ==========================================
// MAIN LOOP
// ==========================================
void loop() {

  // 1. TAMPER MONITOR
  if (digitalRead(LIMIT_SWITCH_PIN) == TAMPER_TRIGGER_STATE) {
      triggerIsolate("CHASSIS TAMPER");
  }

  // 2. PI COMMAND MONITOR (Serial2 = GPIO 19/20)
  if (Serial2.available()) {
      String msg = Serial2.readStringUntil('\n');
      msg.trim();
      if (msg.length() > 0) {
          Serial.println("Pi Bridge Rx: " + msg);
          processC2Message(msg);
      }
  }

  // 3. GSM INCOMING (commented out, enable if needed)
  /*
  if (Serial1.available()) {
      String msg = Serial1.readStringUntil('\n');
      msg.trim();
      if (msg.length() > 0) {
         Serial.println("GSM Rx: " + msg);
         Serial2.println("GSM: " + msg);
      }
  }
  */

  // 4. HEARTBEAT over Serial2 every 5 seconds (Pi can monitor this)
  if (millis() - lastHeartbeat > 5000) {
      lastHeartbeat = millis();
      String hb = "{\"event\":\"heartbeat\",\"uptime\":" + String(millis()/1000) + 
                  ",\"isolated\":" + String(isAirGapped ? "true" : "false") + 
                  ",\"tamper\":" + String(digitalRead(LIMIT_SWITCH_PIN) == HIGH ? "true" : "false") + "}";
      Serial.println(hb);
      Serial2.println(hb);  // Pi will receive this to confirm UART link
  }

  // 5. PRG BUTTON = Physical disarm
  if (digitalRead(PRG_BUTTON_PIN) == LOW) {
      if (isAirGapped) {
          isAirGapped = false;
          pinMode(RELAY1_PIN, INPUT);  // Float = relay OFF = network restored
          pinMode(RELAY2_PIN, INPUT);
          updateOLED("DISARMED", "Relay Restored");
          serialBoth("{\"event\":\"manually_disarmed\",\"by\":\"PRG_BUTTON\"}");
          delay(2000);
          updateOLED("SYSTEM ARMED", "Monitoring...");
      }
  }
}
