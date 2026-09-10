#include <esp_now.h>
#include <WiFi.h>

// Universal MAC address for broadcasting to all devices
uint8_t broadcastAddress[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

// Structure of the message to send/receive
typedef struct struct_message {
    char command[32]; // e.g., "ISOLATE", "SAFE"
    int node_id;
} struct_message;

struct_message myData;
esp_now_peer_info_t peerInfo;

// Callback when data is sent
#if ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(5, 0, 0)
void OnDataSent(const uint8_t *mac_addr, esp_now_send_status_t status) {
  Serial.print("\r\nLast Packet Send Status:\t");
  Serial.println(status == ESP_NOW_SEND_SUCCESS ? "Delivery Success" : "Delivery Fail");
}
#else
void OnDataSent(const uint8_t *mac_addr, esp_now_send_status_t status) {
  Serial.print("\r\nLast Packet Send Status:\t");
  Serial.println(status == ESP_NOW_SEND_SUCCESS ? "Delivery Success" : "Delivery Fail");
}
#endif

// Callback when data is received
#if ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(5, 0, 0)
void OnDataRecv(const esp_now_recv_info_t *info, const uint8_t *incomingData, int len) {
#else
void OnDataRecv(const uint8_t * mac, const uint8_t *incomingData, int len) {
#endif
  memcpy(&myData, incomingData, sizeof(myData));
  Serial.print("Bytes received: ");
  Serial.println(len);
  Serial.print("Command: ");
  Serial.println(myData.command);
  Serial.print("From Node: ");
  Serial.println(myData.node_id);
  
  if (strcmp(myData.command, "ISOLATE") == 0) {
    Serial.println("[ALERT] Received ISOLATE command from mesh! Initiating lockdown...");
  }
}

void setup() {
  Serial.begin(115200);
  WiFi.mode(WIFI_STA);
  Serial.println("Sentinel ESP32 Node Booting...");
  Serial.print("My MAC Address: ");
  Serial.println(WiFi.macAddress());

  if (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    return;
  }

  // Use type casting to avoid compiler errors on v3
  esp_now_register_send_cb((esp_now_send_cb_t)OnDataSent);
  esp_now_register_recv_cb((esp_now_recv_cb_t)OnDataRecv);
  
  memcpy(peerInfo.peer_addr, broadcastAddress, 6);
  peerInfo.channel = 0;  
  peerInfo.encrypt = false;
  
  if (esp_now_add_peer(&peerInfo) != ESP_OK){
    Serial.println("Failed to add peer");
    return;
  }
}

void loop() {
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    
    if (input == "TEST") {
      strcpy(myData.command, "ISOLATE");
      myData.node_id = 1;
      
      Serial.println("Broadcasting ISOLATE command to mesh...");
      esp_err_t result = esp_now_send(broadcastAddress, (uint8_t *) &myData, sizeof(myData));
      
      if (result == ESP_OK) {
        Serial.println("Sent with success");
      } else {
        Serial.println("Error sending the data");
      }
    }
  }
}
