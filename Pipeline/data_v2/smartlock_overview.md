---
name: VaughnKey Smart Lock — Overview, Problem, and Evolution
description: Project overview and constraints (rental apartment, no permanent installation) plus the evolution timeline showing which initial concepts (WiFi ARP, handle-turn sensing) were abandoned and why the current implementation (capacitive touch + BLE, deep sleep) won out. Also covers all tunable firmware parameters.
company: personal
topics: [iot, embedded_systems, ble, low_power, hardware_design, firmware, iteration, requirements_evolution, project_rationale]
skills: [ESP32, C++, BLE, embedded_programming, hardware_integration, requirements_gathering]
story_types: [problem_solving, systems_thinking, product_pitch]
---

# VaughnKey — Retrofit Smart Lock Project

**GitHub:** https://github.com/VDEugenio/VaughnKey

## Project Overview

VaughnKey is a battery-powered, non-invasive retrofit smart lock system built around an ESP32 microcontroller. The project was born from a real-world constraint: Vaughn wanted automated smart lock functionality for his apartment, but his landlord prohibited changing or installing new locks. Rather than accept this limitation, he designed and built a completely removable retrofit solution that mounts via command strips and requires zero permanent installation.

The lock combines capacitive touch sensing through the door's metal peephole with BLE (Bluetooth Low Energy) proximity authentication. A servo motor physically actuates the existing deadbolt. The system is optimized for extreme battery efficiency, staying in deep sleep (~10µA power draw) for the overwhelming majority of its operational life, waking only when the user touches the peephole.

## The Problem Being Solved

**Core constraint:** Rental property with landlord restrictions preventing lock replacement or permanent installation.

**User need:** Automatic lock/unlock capability without fumbling for physical keys.

**Design philosophy:** Modern door locks requiring physical keys are archaic. Smart lock technology should be accessible even in rental situations where permanent modifications are prohibited.

**Solution approach:** A fully reversible, command strip-mounted retrofit that wraps around the existing deadbolt mechanism and can be removed without a trace when the lease ends.

## Why This Project is Interesting to Vaughn

1. **Tight design constraints as creative fuel:** The project operates within several competing constraints (no permanent installation, battery-powered, rental property restrictions, security requirements). Finding elegant solutions within these boundaries is what makes the engineering interesting.

2. **Real-world problem solving:** This isn't a theoretical exercise. Vaughn uses this lock every day. Every design decision has immediate, tangible consequences.

3. **Full-stack hardware/software integration:** The project requires expertise across embedded systems, low-power design, mechanical engineering (3D printed gearing), wireless protocols, and UX design.

4. **Iterative improvement:** The project has evolved significantly from initial concepts (WiFi ARP table detection, handle-turn sensing) to current implementation (BLE proximity, capacitive touch). Vaughn continues to refine and improve it.

## Project Evolution & Design Decisions

### Initial Concepts (Abandoned)

**1. WiFi ARP Table Presence Detection**
- **Idea:** Detect user's phone by scanning WiFi network ARP table
- **Why abandoned:**
  - Requires continuous WiFi scanning (high power consumption)
  - Unreliable phone detection (depends on WiFi auto-connect timing)
  - Security concerns with WiFi-based presence

**2. Handle-Turn Sensing**
- **Idea:** Detect when user manually turns door handle to trigger lock/unlock
- **Why abandoned:**
  - Difficult to reliably distinguish intentional vs. accidental handle movement
  - Requires sensors that complicate mechanical design
  - Capacitive touch proved simpler and more reliable

### Current Implementation Advantages

**Capacitive touch through peephole:**
- ✅ Zero added hardware (peephole already metal and conductive)
- ✅ Intuitive user interface (touch to unlock)
- ✅ Ultra-low power wake source
- ✅ Reliable gesture detection
- ✅ No modification to door hardware

**BLE proximity authentication:**
- ✅ Better range control than WiFi
- ✅ Lower power consumption than continuous WiFi scanning
- ✅ Standard protocol with good library support
- ✅ Keychain beacon form factor (upcoming)

**Deep sleep optimization:**
- ✅ ~10µA draw allows months of battery life
- ✅ Touch sensor remains active during sleep
- ✅ No periodic wake timers needed
- ✅ Instant response to user interaction

## Tunable System Parameters

All critical parameters are defined at the top of the firmware file for easy adjustment:

| Parameter | Current Value | Purpose |
|-----------|---------------|---------|
| `TAP_ACTION` | `UNLOCK` | Action for quick tap (< 1 second) |
| `HOLD_ACTION` | `LOCK` | Action for long hold (≥ 1 second) |
| `TOUCH_THRESHOLD` | 40 | Capacitive sensitivity (lower = more sensitive) |
| `LONG_HOLD_MS` | 1000 | Duration threshold for hold vs. tap (milliseconds) |
| `TRUSTED_DEVICE` | `"VaughnKey"` | BLE device name to authenticate (will change to UUID 0x2018) |
| `BLE_SCAN_TIME` | 1 | Duration of BLE scan when unlocking (seconds) |
| `BLE_RSSI_MIN` | -70 | Minimum signal strength for authentication (dBm) |
| `LOCK_POS` | 170 | Servo angle for locked position (degrees) |
| `UNLOCK_POS` | 10 | Servo angle for unlocked position (degrees) |
| `START_POS` | 90 | Servo neutral/return position (degrees) |

### Parameter Tuning Notes

**TOUCH_THRESHOLD (40):**
- Tuned through experimentation
- Lower values = more sensitive (may false trigger)
- Higher values = less sensitive (may miss intentional touches)
- Current setting reliably detects finger on peephole without false triggers from vibration

**LONG_HOLD_MS (1000ms):**
- Initially tested tap counting (1 tap vs. 3 taps)
- Duration-based detection proved more reliable
- 1 second provides clear distinction between quick tap and intentional hold
- Long enough to feel deliberate, short enough to not be annoying

**BLE_RSSI_MIN (-70 dBm):**
- Calibrated using `rssi_calibration.ino` utility sketch
- Current threshold requires user within ~3 feet of door
- Prevents unlock from outside apartment (hallway)
- Could be adjusted for different proximity requirements
