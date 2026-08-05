# Pitch Deck Outline — BlackBox Sentinel

## Slide 1: Title
- **BlackBox Sentinel**: Real-Time Network Anomaly Detection with Tamper-Proof Logging
- Team Members: M1, M2, M3, M4

## Slide 2: Problem Statement
- Network attacks go undetected for an average of 287 days
- Traditional logging systems can be tampered with by attackers
- Small organizations lack affordable real-time monitoring

## Slide 3: Our Solution
- ESP32-based hardware packet sniffer (low-cost)
- Isolation Forest ML model for zero-day anomaly detection
- SHA-256 hash-chained ledger (tamper-proof by design)
- 800×480 real-time dashboard

## Slide 4: Architecture
- [Insert architecture diagram]
- 4-module pipeline: Capture → Process → Detect → Display

## Slide 5: Demo
- Live demo of packet capture → anomaly alert → SMS notification

## Slide 6: Technical Deep Dive
- Isolation Forest: unsupervised, no labeled data needed
- Hash chain: O(1) append, O(n) full verification
- ESP32: <$5 hardware cost

## Slide 7: Results
- [Insert accuracy metrics, latency benchmarks]

## Slide 8: Future Work
- Cloud dashboard
- Multi-sensor mesh network
- SIEM integration

---

> **Design:** Create final pitch deck in Figma/Canva and link it here.
> **Figma Link:** `[paste your shared Figma URL here]`
