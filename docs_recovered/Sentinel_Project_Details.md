# BlackBox Sentinel: System Architecture & Project Details

![System Architecture](C:/Users/prajw/.gemini/antigravity/brain/270a84f9-03b4-4aad-8d00-59894c48d25a/architecture_diagram.png)

## 1. Executive Summary
BlackBox Sentinel is a cyber-physical network intrusion prevention system (IPS) designed to physically air-gap networks upon detecting an active threat. Unlike traditional software firewalls, Sentinel uses a hardware-enforced mechanical relay to physically sever the Ethernet data line, making remote bypass impossible.

## 2. Dual-Processor Trust Architecture
The core innovation of the system is the cryptographic decoupling of threat detection from physical actuation.

*   **Untrusted Host (Raspberry Pi 4):** Connects to the network, captures traffic, and runs an Isolation Forest machine learning model to detect anomalies. If compromised, it **cannot** directly trigger network isolation.
*   **Trusted Coprocessor (ESP32-S3):** An electrically isolated microcontroller that exclusively commands the physical relay. It only accepts isolation requests from the Pi if they are wrapped in a cryptographically signed, timestamped evidence envelope. 

## 3. Quorum-Gated Authorization (Patent Claim A)
The mechanical relay will not fire based on a simple software command. The system requires **Quorum Consensus**:
1.  Pi's ML engine detects an anomaly and generates a threat score.
2.  Pi signs the threat score and timestamp with a private key.
3.  Pi sends the payload over an isolated serial link to the ESP32.
4.  ESP32 validates the signature, ensures the timestamp is not a replay attack, and checks physical tamper switches.
5.  Only if all checks pass does the ESP32 actuate the relay.

## 4. Zero-Remote Recovery (Patent Claim B)
Once the relay is triggered and the network is air-gapped, the ESP32 enters a hardware-locked state. 
*   It will ignore all subsequent commands from the Pi to reconnect the network.
*   There is no remote API, cloud dashboard, or SSH recovery path.
*   **Recovery requires physical presence:** An authorized user must physically interact with the touchscreen interface on the device chassis to input a cryptographic PIN to disengage the relay.

## 5. Bill of Materials (BOM) & Physical Layout
The system is housed in a custom 3D-printed, tamper-resistant enclosure.

| Component | Role in System | 
| :--- | :--- | 
| **Raspberry Pi 4 (8GB)** | Runs Linux, captures traffic, runs ML inference |
| **ESP32-S3 (Heltec V3)** | Trusted Coprocessor, relay actuation, hardware root of trust |
| **5V Mechanical Relay** | Physically cuts the Ethernet copper data lines |
| **3.5" TFT Touchscreen** | Interface for the physical-only PIN recovery |
| **Micro Limit Switches (2x)** | Anti-tamper chassis breach detection |
| **GSM/GPRS Shield (SIM800)**| Out-of-band cellular alerts via SMS |
| **Dual-18650 PMIC Shield** | Uninterruptible Power Supply (UPS) for all components |

## 6. Anti-Tamper Security
The physical enclosure is lined with micro limit switches connected directly to the trusted ESP32. If an attacker attempts to open the chassis to bypass the relay manually, the ESP32 detects the breach, immediately fires the relay (fail-secure), and initiates cryptographic zeroization of all stored keys.
