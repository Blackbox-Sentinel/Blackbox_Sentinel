int RELAY_PIN = 4; // GPIO 4

void setup() {
  Serial.begin(115200);
  pinMode(RELAY_PIN, OUTPUT);
  Serial.println("Starting Relay Test...");
}

void loop() {
  Serial.println("Relay: ON (CUTTING NETWORK)");
  digitalWrite(RELAY_PIN, HIGH);
  delay(2000); 

  Serial.println("Relay: OFF (NETWORK SAFE)");
  digitalWrite(RELAY_PIN, LOW);
  delay(2000); 
}
