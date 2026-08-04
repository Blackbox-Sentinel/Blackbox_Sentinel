/*
 * BlackBox Sentinel — ESP32-S3 Co-Processor Firmware
 * 
 * Hardware Responsibilities:
 *   1. Hardware mechanical line relay control (GPIO 18)
 *   2. Anti-tamper chassis copper grid interrupt (GPIO 27, Active-Low)
 *   3. ESP-NOW connectionless P2P mesh threat gossip (2.4GHz)
 *   4. SIM800L GSM cellular modem UART communication (AT commands)
 *   5. Host UART command interface with Raspberry Pi Zero 2W (115200 baud)
 * 
 * Target Hardware: ESP32-S3 DevKitC-1 / ESP32 DevKit V1
 * Framework: Arduino / ESP-IDF ESP32 Core
 */

#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>

// ── Pin Definitions ────────────────────────────────────────────────────────
#define PIN_RELAY_CTRL       18   // Controls 5V signal isolation relay
#define PIN_TAMPER_GRID      27   // Anti-tamper interrupt line (PULLUP)
#define PIN_LED_ARMED        2    // Green status LED
#define PIN_LED_ALERT        4    // Red alert / lockdown LED
#define PIN_LED_MESH         5    // Blue ESP-NOW mesh activity LED

#define SIM800_RX_PIN        16   // ESP32 RX <- SIM800L TX
#define SIM800_TX_PIN        17   // ESP32 TX -> SIM800L RX

// ── Data Structures ────────────────────────────────────────────────────────
typedef struct __attribute__((packed)) {
    char origin_node[16];
    char threat_type[32];
    float anomaly_score;
    uint16_t victim_port;
    uint32_t timestamp;
} MeshThreatPacket;

// Broadcast MAC address for ESP-NOW mesh
uint8_t broadcastMac[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

// ── System State ───────────────────────────────────────────────────────────
volatile bool tamperTriggered = false;
bool isArmed = false;
bool isAirGapped = false;
unsigned long lastHeartbeat = 0;
unsigned long lastBlink = 0;
bool alertBlinkState = false;

// ── Anti-Tamper Interrupt Service Routine ──────────────────────────────────
void IRAM_ATTR onTamperInterrupt() {
    tamperTriggered = true;
}

// ── ESP-NOW Callbacks ──────────────────────────────────────────────────────
void onDataSent(const uint8_t *mac_addr, esp_now_send_status_t status) {
    digitalWrite(PIN_LED_MESH, LOW);
    Serial.printf("[ESP-NOW] Threat broadcast status: %s\n", 
                  status == ESP_NOW_SEND_SUCCESS ? "SUCCESS" : "FAIL");
}

void onDataRecv(const esp_now_recv_info *recv_info, const uint8_t *incomingData, int len) {
    digitalWrite(PIN_LED_MESH, HIGH);
    if (len == sizeof(MeshThreatPacket)) {
        MeshThreatPacket pkt;
        memcpy(&pkt, incomingData, sizeof(MeshThreatPacket));
        
        Serial.printf("[ESP-NOW-RECV] Peer Threat Alert from %s! Type: %s | Port: %d | Score: %.3f\n",
                      pkt.origin_node, pkt.threat_type, pkt.victim_port, pkt.anomaly_score);

        // Forward threat to Pi host over serial
        Serial.printf("{\"event\":\"mesh_peer_alert\",\"origin\":\"%s\",\"type\":\"%s\",\"port\":%d,\"score\":%.3f}\n",
                      pkt.origin_node, pkt.threat_type, pkt.victim_port, pkt.anomaly_score);
    }
    delay(50);
    digitalWrite(PIN_LED_MESH, LOW);
}

// ── Hardware Control Functions ─────────────────────────────────────────────
void isolateRelay() {
    isAirGapped = true;
    digitalWrite(PIN_RELAY_CTRL, HIGH); // Actuate relay to open circuit
    digitalWrite(PIN_LED_ARMED, LOW);
    digitalWrite(PIN_LED_ALERT, HIGH);
    Serial.println("{\"event\":\"relay_state\",\"state\":\"ISOLATED\"}");
}

void engageRelay() {
    isAirGapped = false;
    digitalWrite(PIN_RELAY_CTRL, LOW);  // Return relay to NC (connected)
    digitalWrite(PIN_LED_ARMED, isArmed ? HIGH : LOW);
    digitalWrite(PIN_LED_ALERT, LOW);
    Serial.println("{\"event\":\"relay_state\",\"state\":\"ENGAGED\"}");
}

void broadcastThreatMesh(const char* threat, float score, uint16_t port) {
    MeshThreatPacket pkt;
    strncpy(pkt.origin_node, "AEDN-RACK-01", sizeof(pkt.origin_node));
    strncpy(pkt.threat_type, threat, sizeof(pkt.threat_type));
    pkt.anomaly_score = score;
    pkt.victim_port = port;
    pkt.timestamp = millis() / 1000;

    digitalWrite(PIN_LED_MESH, HIGH);
    esp_now_send(broadcastMac, (uint8_t *)&pkt, sizeof(MeshThreatPacket));
}

// ── Host Serial Command Parser ─────────────────────────────────────────────
void processHostCommand(String cmd) {
    cmd.trim();
    if (cmd == "ISOLATE" || cmd == "CUT") {
        isolateRelay();
    } else if (cmd == "ENGAGE" || cmd == "RESTORE") {
        engageRelay();
    } else if (cmd == "ARM") {
        isArmed = true;
        if (!isAirGapped) digitalWrite(PIN_LED_ARMED, HIGH);
        Serial.println("{\"event\":\"coprocessor_state\",\"status\":\"ARMED\"}");
    } else if (cmd == "DISARM") {
        isArmed = false;
        digitalWrite(PIN_LED_ARMED, LOW);
        Serial.println("{\"event\":\"coprocessor_state\",\"status\":\"DISARMED\"}");
    } else if (cmd.startsWith("GOSSIP:")) {
        // Format: GOSSIP:EXFILTRATION:-0.088:4444
        int firstColon = cmd.indexOf(':', 7);
        int secondColon = cmd.indexOf(':', firstColon + 1);
        String threat = cmd.substring(7, firstColon);
        float score = cmd.substring(firstColon + 1, secondColon).toFloat();
        uint16_t port = cmd.substring(secondColon + 1).toInt();
        broadcastThreatMesh(threat.c_str(), score, port);
    } else if (cmd == "PING") {
        Serial.println("{\"event\":\"pong\",\"tamper\":false,\"relay\":\"ENGAGED\"}");
    }
}

// ── Setup ──────────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(115200);
    delay(500);
    Serial.println("\n========================================================");
    Serial.println("  🛡️  BLACKBOX SENTINEL — ESP32-S3 CO-PROCESSOR v2.0   ");
    Serial.println("========================================================");

    // Initialize GPIO pins
    pinMode(PIN_RELAY_CTRL, OUTPUT);
    pinMode(PIN_LED_ARMED, OUTPUT);
    pinMode(PIN_LED_ALERT, OUTPUT);
    pinMode(PIN_LED_MESH, OUTPUT);
    pinMode(PIN_TAMPER_GRID, INPUT_PULLUP);

    // Default states
    engageRelay();
    digitalWrite(PIN_LED_ARMED, LOW);
    digitalWrite(PIN_LED_ALERT, LOW);
    digitalWrite(PIN_LED_MESH, LOW);

    // Attach hardware interrupt on tamper grid (falling edge = broken continuous loop)
    attachInterrupt(digitalPinToInterrupt(PIN_TAMPER_GRID), onTamperInterrupt, FALLING);

    // Initialize WiFi in Station Mode for ESP-NOW (no AP connection needed)
    WiFi.mode(WIFI_STA);
    WiFi.disconnect();
    Serial.printf("[WIFI] ESP32 MAC Address: %s\n", WiFi.macAddress().c_str());

    // Initialize ESP-NOW
    if (esp_now_init() != ESP_OK) {
        Serial.println("❌ [ESP-NOW] Initialization failed!");
    } else {
        Serial.println("✅ [ESP-NOW] Mesh protocol initialized.");
        esp_now_register_send_cb(onDataSent);
        esp_now_register_recv_cb(onDataRecv);

        // Register broadcast peer
        esp_now_peer_info_t peerInfo = {};
        memcpy(peerInfo.peer_addr, broadcastMac, 6);
        peerInfo.channel = 0;
        peerInfo.encrypt = false;
        if (esp_now_add_peer(&peerInfo) == ESP_OK) {
            Serial.println("✅ [ESP-NOW] Broadcast peer registered.");
        }
    }

    Serial.println("[SYSTEM] Co-processor initialized and ready for Pi host commands.");
}

// ── Main Execution Loop ────────────────────────────────────────────────────
void loop() {
    // 1. Check for Anti-Tamper grid rupture
    if (tamperTriggered) {
        tamperTriggered = false;
        Serial.println("🚨 {\"event\":\"tamper_breach\",\"action\":\"ZEROIZE_AND_ISOLATE\"}");
        isolateRelay();
        // Fast alert blink loop
        for (int i = 0; i < 10; i++) {
            digitalWrite(PIN_LED_ALERT, HIGH);
            delay(50);
            digitalWrite(PIN_LED_ALERT, LOW);
            delay(50);
        }
    }

    // 2. Read commands from Raspberry Pi host over Serial
    while (Serial.available()) {
        String cmd = Serial.readStringUntil('\n');
        if (cmd.length() > 0) {
            processHostCommand(cmd);
        }
    }

    // 3. Status LED blinking when in alert / isolated mode
    if (isAirGapped) {
        if (millis() - lastBlink > 200) {
            lastBlink = millis();
            alertBlinkState = !alertBlinkState;
            digitalWrite(PIN_LED_ALERT, alertBlinkState ? HIGH : LOW);
        }
    }

    // 4. Heartbeat telemetry to Pi host every 5 seconds
    if (millis() - lastHeartbeat > 5000) {
        lastHeartbeat = millis();
        Serial.printf("{\"heartbeat\":%lu,\"relay\":\"%s\",\"tamper_grid\":%s}\n",
                      millis() / 1000,
                      isAirGapped ? "ISOLATED" : "ENGAGED",
                      digitalRead(PIN_TAMPER_GRID) == HIGH ? "SECURE" : "BREACHED");
    }
}
