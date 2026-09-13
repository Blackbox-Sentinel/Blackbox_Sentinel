#!/usr/bin/env python3
import urllib.request, json, time

time.sleep(6)

log = open('/tmp/flask.log').readlines()[-10:]
print("=== Flask Log (last 10 lines) ===")
for l in log: print(l.rstrip())

print("\n=== API Test ===")
try:
    with urllib.request.urlopen("http://localhost:5000/api/system_stats", timeout=5) as r:
        d = json.load(r)
    print(f"✅ Flask responding")
    print(f"   relay_state: {d.get('relay_state','?')}")
    print(f"   hal_mode: {d.get('hal_mode', d.get('mode','?'))}")
    print(f"   uptime: {d.get('uptime','?')}")
    print(f"   anomaly_score: {d.get('anomaly_score','?')}")
except Exception as e:
    print(f"❌ API error: {e}")

print(f"\n🌐 Access UI from your laptop: http://raspberrypi.local:5000")
