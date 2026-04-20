---
name: VaughnKey Firmware Execution Flow and BLE Authentication
description: Code-level execution flow from wake → touch-duration measurement → action dispatch → servo/BLE → sleep, plus the BLE authentication system (current name-based scan, planned UUID-based scan with nRF51822 iBeacon, and security tradeoffs).
company: personal
topics: [iot, embedded_systems, ble, low_power, firmware, execution_flow, authentication, security, ios_background_ble]
skills: [ESP32, C++, BLE, embedded_programming, arduino, deep_sleep_api, BLEDevice, BLEScan]
story_types: [problem_solving, systems_thinking, architecture_design]
related_files: [smartlock_hardware.md, smartlock_ux.md]
---

## Full Execution Flow (Code-Level Detail)

### 1. Deep Sleep State
```
Power draw: ~10µA
Active components: ULP touch sensor on GPIO4
Waiting for: Touch threshold crossed on T0
```

### 2. Wake on Touch
- Touch event triggers `ESP_SLEEP_WAKEUP_TOUCHPAD`
- ESP32 performs full cold boot into `setup()` (no `loop()` function is used)
- RAM is completely wiped; no state persists across sleep cycles

### 3. Touch Duration Measurement (`measureTouch()`)
```cpp
- Polls touchRead(T0) every 10ms
- Touch threshold: 40 (lower = more sensitive)
- If touch value stays below threshold for >= 1000ms → long hold (returns true)
- If finger lifts before 1000ms → quick tap (returns false)
- Duration printed to Serial for debugging
```

### 4. Action Determination
```cpp
Action action = isLongHold ? HOLD_ACTION : TAP_ACTION;
```

### 5a. Lock Execution (No Authentication)
```cpp
1. servoInit()
   - Attaches servo at 50Hz PWM
   - Pulse range: 500-2500µs
   - Moves to neutral (90°)

2. doAction(LOCK)
   - Sweeps servo to LOCK_POS (170°)
   - Waits 400ms for mechanical movement
   - Returns to START_POS (90°)

3. servoDetach()
   - Detaches servo
   - Pulls GPIO18 LOW (prevents jitter)
```

### 5b. Unlock Execution (BLE Authentication Required)
```cpp
1. bleScanForTrusted()
   - Initializes BLE stack: BLEDevice::init("DoorLock")
   - BLE scan settings:
     * Duration: 1 second
     * Interval: 100ms
     * Window: 99ms (near-continuous scanning)
   - Searches for device with name "VaughnKey"
   - Checks RSSI against BLE_RSSI_MIN (-70 dBm)
   - Returns true only if: device found AND RSSI >= -70 dBm

2. If BLE authentication succeeds:
   - servoInit()
   - doAction(UNLOCK) → sweeps to 10°, returns to 90°
   - servoDetach()

3. If BLE authentication fails:
   - Prints "No trusted phone found — staying locked"
   - Servo does not move
   - Door remains locked
```

### 6. Cleanup & Return to Sleep
```cpp
1. bleDeinit()
   - Calls BLEDevice::deinit(false)
   - Frees ~170KB BLE memory allocation

2. goToSleep()
   - Re-enables touch wakeup: touchSleepWakeUpEnable(T0, 40)
   - Enters deep sleep: esp_deep_sleep_start()

3. Cycle repeats on next touch
```

## BLE Authentication System

### Current Implementation (Interim)

**Method:** Scan by device name ("VaughnKey")
**Device:** iPhone running LightBlue or nRF Connect app in BLE peripheral mode
**Problem discovered:** iOS kills background BLE advertising. When the app is backgrounded, the device name and service UUIDs are stripped from advertisement packets, making the phone invisible to the ESP32.

**Scan parameters:**
- Scan duration: 1 second
- Scan interval: 100ms
- Scan window: 99ms (near-continuous)
- RSSI threshold: -70 dBm (~3 feet maximum distance)

**RSSI calibration process:**
A dedicated calibration sketch (`rssi_calibration.ino`) continuously scans and prints RSSI values with distance labels, allowing precise threshold tuning for desired proximity range.

### Planned Implementation (In Progress)

**Method:** Scan by service UUID (0x2018)
**Device:** nRF51822 iBeacon keychain beacon (hardware ordered)
**Advantages:**
- Dedicated hardware beacon advertises 24/7 on coin cell battery
- No iOS background advertising limitations
- No dependency on phone apps or OS behavior
- Always-on presence broadcasting

**Code update required:**
Change BLE scan logic from device name matching to service UUID matching. A UUID-specific scanner (`uuid_scanner.ino`) has been created for debugging iOS advertisement packet contents.

### Security Considerations

**Current security level:** Low
- Device name scanning is trivially spoofable
- No encrypted challenge-response
- No rolling codes or replay attack protection

**Known vulnerabilities:**
- Anyone with a BLE device advertising as "VaughnKey" can unlock the door
- UUID-based scanning is marginally better but still spoofable
- RSSI can be manipulated with signal amplification

**Future hardening options:**
- Encrypted challenge-response authentication
- Rolling codes with synchronized time-based tokens
- Multi-factor authentication (BLE + PIN entry via touch patterns)
- Encrypted communication channel for remote unlock features

**Current risk assessment:**
For a personal apartment lock, the current security model is acceptable during prototype phase. Physical security (door, lock quality, building access) remains the primary security layer. BLE proximity authentication adds convenience without significantly degrading security below a traditional key-based lock (which is also trivially pickable/bumpable).
