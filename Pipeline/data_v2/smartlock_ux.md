---
name: VaughnKey User Interaction Model
description: Touch-duration gesture system (tap = unlock, hold = lock), physical interaction flows for arriving home and leaving home, and the asymmetric authentication rationale (unlock requires BLE proximity, lock does not).
company: personal
topics: [iot, embedded_systems, ble, low_power, hardware_design, firmware, touch_sensing, user_experience, interaction_design, asymmetric_auth]
skills: [ESP32, C++, BLE, embedded_programming, hardware_integration, ux_design]
story_types: [problem_solving, systems_thinking, product_pitch, user_experience]
---

## User Interaction Model

### Touch Gesture System

The lock uses **touch duration** (not tap counting) to distinguish lock from unlock commands. This approach proved more reliable than the initial tap-count method.

**Gesture detection:**
- **Quick tap (< 1.0 second):** Triggers `TAP_ACTION`
- **Long hold (≥ 1.0 second):** Triggers `HOLD_ACTION`

**Current mapping:**
```
TAP_ACTION  = UNLOCK  (requires BLE authentication)
HOLD_ACTION = LOCK    (no authentication required)
```

This mapping is configurable via `#define` statements and may be swapped based on user preference testing.

### Physical Interaction Flow

**Scenario 1: Unlocking (arriving home)**
1. User approaches door with BLE beacon in pocket/bag
2. User taps peephole briefly (< 1 second)
3. ESP32 wakes from deep sleep
4. System measures touch duration → detects quick tap
5. BLE scan initiates (1 second active scan)
6. System searches for trusted device "VaughnKey" (will change to UUID 0x2018)
7. If device found AND RSSI ≥ -70 dBm (within ~3 feet):
   - Servo sweeps to UNLOCK_POS (10°), waits 400ms, returns to neutral (90°)
   - User enters apartment
8. If device not found OR too far away:
   - Prints "No trusted phone found — staying locked"
   - Door remains locked, system returns to sleep

**Scenario 2: Locking (leaving home)**
1. User touches and holds peephole (≥ 1.0 second)
2. ESP32 wakes from deep sleep
3. System measures touch duration → detects long hold
4. **No BLE authentication required** (intentional design choice: anyone inside can lock the door)
5. Servo sweeps to LOCK_POS (170°), waits 400ms, returns to neutral (90°)
6. Door is locked, system returns to sleep

### Why Lock Doesn't Require Authentication

The asymmetric authentication model (unlock requires BLE, lock does not) is intentional:
- **Security model:** Protect entry, not exit
- **Use case:** Guests, roommates, or family members inside the apartment should be able to lock the door when leaving
- **Failure mode:** Better to accidentally lock yourself out than accidentally leave the door unlocked
