---
name: VaughnKey Technical Deep Dive — Power Budget, Capacitive Touch, BLE vs WiFi
description: Quantitative power-budget analysis (~10µA sleep, peak currents, theoretical vs observed battery life), why capacitive touch through the peephole beat every alternative, and why BLE was the right choice over WiFi on power/range/security/complexity grounds.
company: personal
topics: [iot, embedded_systems, ble, low_power, hardware_design, firmware, power_budget, capacitive_touch, protocol_comparison]
skills: [ESP32, C++, BLE, embedded_programming, power_analysis, rssi, protocol_design]
story_types: [problem_solving, systems_thinking, architecture_design]
related_files: [smartlock_hardware.md, smartlock_software.md]
---

## Technical Deep Dive: Why This Works

### Power Budget Analysis

**Deep sleep current draw:** ~10µA
**Active BLE scan (1 second):** ~100mA
**Servo operation (0.8 seconds total):** ~500mA peak

**Estimated daily usage:**
- 10 lock/unlock cycles per day
- 10 seconds total active time (10 × 1 second BLE scan)
- 8 seconds total servo time (10 × 0.8 seconds)

**Daily power consumption:**
- Deep sleep: 24 hours × 10µA = 0.24mAh
- BLE scanning: 10 seconds × 100mA = 0.28mAh
- Servo operation: 8 seconds × 500mA = 1.11mAh
- **Total per day: ~1.63mAh**

**Power source:** Modified power bank (standard USB power bank with auto-shutoff bypass, since the ESP32's deep sleep draw of ~10µA would otherwise trigger the bank's low-current cutoff)
**Observed battery life:** 3-4 months

**Future improvement path:** A dedicated LiPo or 18650 cell solution would provide a cleaner form factor, better current delivery, and built-in rechargeability without needing a modified consumer power bank.

### Why Capacitive Touch is Ideal

**Advantages over alternatives:**

**vs. Physical button:**
- ✅ No hole drilled in door
- ✅ Weatherproof (peephole is already sealed)
- ✅ No mechanical wear
- ✅ Aesthetic (invisible modification)

**vs. Proximity sensor (PIR, ultrasonic, etc.):**
- ✅ No false triggers from passersby in hallway
- ✅ Ultra-low power in standby
- ✅ Intentional gesture required (security benefit)
- ✅ Simpler circuitry

**vs. Keypad:**
- ✅ Simpler user interface
- ✅ No memorization required
- ✅ Faster interaction (tap vs. entering code)
- ✅ Lower power consumption

**Why peephole specifically:**
- Already conductive metal (no modification needed)
- Natural touch point (users know where it is)
- Interior wiring path already exists
- Protected from weather
- Inconspicuous to casual observers

### Why BLE Over WiFi

**Power consumption:**
- BLE scan: ~100mA for 1 second = 0.028mAh per unlock
- WiFi connection: ~200mA for 5+ seconds = 0.28mAh per unlock
- **BLE uses 10× less power**

**Range characteristics:**
- BLE RSSI provides fine-grained proximity control
- WiFi presence is binary (connected or not)
- BLE allows "within 3 feet" authentication vs. "on network"

**Security model:**
- BLE beacon is dedicated to door unlock (single purpose)
- WiFi credentials are shared resource (broader risk if compromised)
- BLE scanning is anonymous (ESP32 doesn't join network)

**Implementation complexity:**
- BLE libraries are simpler for presence detection
- WiFi requires SSID/password management
- BLE beacon requires no configuration (just presence)
