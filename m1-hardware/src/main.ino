/*
 * BlackBox Sentinel — M1 Hardware Firmware
 * ESP32 + SIM800L Network Monitor
 * 
 * Author: M1 Hardware Engineer
 * Branch: m1-dev
 */

#include <WiFi.h>

// ─── Configuration ───────────────────────────────────────────
const char* WIFI_SSID     = "YOUR_SSID";
const char* WIFI_PASSWORD = "YOUR_PASSWORD";

// Promiscuous mode callback
void snifferCallback(void* buf, wifi_promiscuous_pkt_type_t type) {
    // TODO: Parse captured packets
    // TODO: Forward raw bytes over Serial to M2 bridge
    const wifi_promiscuous_pkt_t *pkt = (wifi_promiscuous_pkt_t *)buf;
    Serial.printf("[SNIFF] Type: %d | Len: %d\n", type, pkt->rx_ctrl.sig_len);
}

void setup() {
    Serial.begin(115200);
    delay(1000);
    Serial.println("=== BlackBox Sentinel M1 ===");
    Serial.println("Initializing WiFi promiscuous mode...");

    WiFi.mode(WIFI_STA);
    WiFi.disconnect();
    
    // Enable promiscuous mode
    esp_wifi_set_promiscuous(true);
    esp_wifi_set_promiscuous_rx_cb(&snifferCallback);
    
    Serial.println("Promiscuous mode ACTIVE. Capturing packets...");
}

void loop() {
    // Main loop — packet capture runs via callback
    // TODO: Check for anomaly alerts from M3 → trigger SIM800L SMS
    delay(1000);
}
