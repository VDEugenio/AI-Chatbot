---
name: VaughnKey Development Tools and Challenges Overcome
description: Dev tools, project file layout, utility sketches (rssi_calibration, uuid_scanner), required libraries, and five specific engineering challenges Vaughn solved (battery life, auto-lock UX, iOS BLE, servo torque, gesture detection).
company: personal
topics: [iot, embedded_systems, ble, low_power, hardware_design, firmware, development_tools, challenges, debugging]
skills: [ESP32, C++, BLE, embedded_programming, arduino, debugging, calibration, rssi_tuning]
story_types: [problem_solving, systems_thinking, product_pitch]
related_files: [smartlock_overview.md, smartlock_lessons_future_status.md]
---

## Development Tools & Utilities

### Project File Structure
```
doorlock_claude/
  tap_detection/
    tap_detection.ino          # Main lock firmware (all functionality)
  rssi_calibration/
    rssi_calibration.ino       # BLE RSSI measurement and threshold tuning
  uuid_scanner/
    uuid_scanner.ino           # BLE advertisement packet debugging
```

### Utility Sketches

**rssi_calibration.ino:**
- Continuously scans for specific BLE device
- Prints RSSI values with distance labels
- Used to dial in BLE_RSSI_MIN threshold for desired proximity range
- Critical for balancing convenience (unlock far enough from door) vs. security (don't unlock from hallway)

**uuid_scanner.ino:**
- Dumps complete BLE advertisement data for all nearby devices
- Shows service UUIDs, device names, manufacturer data
- Created to debug iOS background advertising behavior
- Revealed that iOS strips UUIDs/names when apps are backgrounded
- Led to decision to use dedicated iBeacon hardware

### Required Libraries

**ESP32Servo:**
- Install via Arduino Library Manager
- Provides servo control tailored for ESP32 hardware
- Handles PWM frequency and pulse width requirements

**BLE Libraries (built into ESP32 Arduino core):**
- `BLEDevice` - Initialize BLE stack
- `BLEScan` - Perform BLE scanning
- `BLEAdvertisedDevice` - Parse advertisement packets

**Deep Sleep (built into ESP32 Arduino core):**
- `esp_sleep.h` - Deep sleep control and wake source configuration

### Development Environment

**Board:** ESP32 (original variant)
**Framework:** Arduino
**Serial baud:** 115200
**IDE:** Arduino IDE (inferred from library usage patterns)

## Challenges Overcome

### 1. Power Life Optimization

**Challenge:** System needs to run for months on a single power source while remaining instantly responsive. A key constraint: the ESP32's deep sleep draw (~10µA) is low enough to trigger a standard USB power bank's auto-shutoff, which cuts power when it detects negligible current draw.

**Solution:**
- Modified power bank with auto-shutoff bypass (small resistive load keeps bank active)
- Aggressive deep sleep strategy (~10µA draw from ESP32)
- Single ultra-low-power wake source (capacitive touch)
- No periodic wake timers
- BLE stack only initialized when needed, then deinitialized to free memory
- Servo detached and pin pulled LOW when not in use
- Result: 3-4 months on modified power bank

### 2. Auto-Lock When Leaving

**Challenge:** How to lock door when leaving apartment without requiring app interaction or second device.

**Solution:**
- Touch-and-hold gesture (≥1 second) triggers lock
- No BLE authentication required for locking (asymmetric security model)
- Intuitive user interface: tap to unlock (coming home), hold to lock (leaving home)
- Capacitive touch remains the only required interaction

### 3. iOS Background BLE Advertising

**Challenge:** iPhone apps (LightBlue, nRF Connect) stop advertising when backgrounded, making phone invisible to ESP32.

**Solution:**
- Identified root cause through uuid_scanner debugging
- Switched approach from phone-based to dedicated iBeacon hardware
- nRF51822 beacon provides always-on presence advertising on coin cell battery
- Required code update to scan by service UUID instead of device name

### 4. Servo Selection & Torque Requirements

**Challenge:** Deadbolt requires significant torque to turn reliably. Initial servos either lacked torque or didn't have sufficient range of motion.

**Solution:**
- Tested multiple servo models
- DS-S012 provided correct balance of torque and 160° travel range
- 3D printed gearing provides mechanical advantage if needed
- Movement delay (400ms) ensures full mechanical engagement before returning to neutral

### 5. Reliable Touch Gesture Detection

**Challenge:** Initial tap-counting approach (1 tap vs. 3 taps) was unreliable and frustrating.

**Solution:**
- Switched to duration-based detection (tap vs. hold)
- Polls touch sensor every 10ms for accurate timing
- 1-second threshold provides clear distinction without feeling sluggish
- More intuitive user model: quick tap = unlock, deliberate hold = lock
