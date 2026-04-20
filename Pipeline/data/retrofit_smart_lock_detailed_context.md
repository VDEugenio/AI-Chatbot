# VaughnKey — Retrofit Smart Lock Project

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

## Current System Architecture

### Hardware Components

- **ESP32 microcontroller** — Main controller running Arduino framework. Manages deep sleep, capacitive touch detection, BLE scanning, and servo control. Original ESP32 variant (not ESP32-C3 or ESP32-S3).

- **Capacitive touch sensor (GPIO4, T0)** — Utilizes the door's existing metal peephole as the touch surface. The peephole is naturally conductive and requires no modification. This is the only user input mechanism and the only wake source from deep sleep.

- **DS-S012 servo motor (GPIO18)** — Physically actuates the deadbolt through a 3D printed gear mechanism. Selected after testing multiple servos for correct range of motion and sufficient torque to reliably turn the deadbolt.

- **9V battery (temporary)** — Current power source. Lasts approximately 3-4 months with deep sleep optimization. Plans to upgrade to a more efficient battery solution in future iterations.

- **BLE beacon (nRF51822 iBeacon, ordered)** — Dedicated hardware keychain beacon that will replace phone-based BLE advertising. Constantly advertises on coin cell battery with service UUID 0x2018.

- **3D printed housing and mechanical linkage** — Command strip-mounted enclosure that wraps around the interior deadbolt mechanism. Contains gearing system that engages the deadbolt thumbturn, rotates it, and disengages when the servo returns to neutral position.

### Power Architecture & Deep Sleep Strategy

The entire system design prioritizes battery longevity through aggressive power management:

**Deep sleep state (default):**
- Power draw: ~10µA
- Duration: 99.9%+ of operational time
- Active components: Only the ULP (ultra-low-power) touch sensor peripheral monitoring GPIO4
- All other peripherals: Disabled
- RAM: Wiped (ESP32 boots fresh on every wake)
- GPIO18 (servo pin): Pulled LOW to prevent servo jitter

**Wake conditions:**
- Single wake source: Capacitive touch on T0 (GPIO4)
- Wake trigger: `ESP_SLEEP_WAKEUP_TOUCHPAD`
- No periodic wake timers, no BLE scanning in sleep, no other interrupts

**Why this approach works:**
The capacitive touch peripheral consumes virtually no power while continuously monitoring for touch events. This allows the system to be instantly responsive to user interaction while drawing negligible current between uses. With an estimated 10-15 lock/unlock cycles per day, the active time represents less than 0.1% of total operational hours.

**Current battery performance:**
- 9V battery lasts approximately 3-4 months
- Future iterations will explore LiPo or 18650 cells for better capacity and rechargeability

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

## Servo Mechanical System

### Servo Specifications
- **Model:** DS-S012
- **Selection criteria:** Range of motion and sufficient torque to reliably turn deadbolt
- **Testing process:** Multiple servos tested before finding correct combination of strength and travel

### Servo Positions
- **LOCK_POS:** 170° (+80° from neutral)
- **UNLOCK_POS:** 10° (-80° from neutral)  
- **START_POS/Neutral:** 90°

### Movement Sequence
All servo operations follow the same pattern:
1. Attach servo and move to neutral (90°)
2. Sweep to target position (10° or 170°)
3. Wait 400ms for mechanical movement completion
4. Return to neutral (90°)
5. Detach servo and pull pin LOW

**Why return to neutral:**
The servo is not continuously powered. It moves the deadbolt, returns to center, and gets detached. The 3D printed mechanical linkage between servo horn and deadbolt accommodates this by engaging during rotation and disengaging at neutral. This prevents the servo from fighting the deadbolt position when detached.

### Mechanical Linkage Design

**Components:**
- 3D printed gear system
- 3D printed engagement mechanism that interfaces with deadbolt thumbturn
- Command strip mounting base

**Operation:**
- Servo horn drives gears that rotate engagement mechanism
- Mechanism engages deadbolt thumbturn during rotation
- Returns to neutral position and disengages
- Allows manual operation of deadbolt without interference

**Mounting:**
- Command strips attach housing to interior door surface
- Wraps around existing deadbolt without modification
- Completely removable without leaving marks or damage

**Weight & Durability:**
- Lightweight assembly (exact weight TBD)
- No vibration or durability issues from door slamming observed thus far
- Command strips provide sufficient holding force

### Lock State Awareness

**Current implementation:** Stateless  
The system does not track whether the door is currently locked or unlocked. Each action (lock/unlock) is executed regardless of current state.

**Why this works:**
- Attempting to lock an already-locked door causes no harm
- Attempting to unlock an already-unlocked door causes no harm
- Mechanical linkage allows servo to "push against" an already-engaged deadbolt without damage
- Simplifies code and eliminates need for limit switches or position sensors

**Future consideration:**
Adding lock state awareness (via limit switches or current sensing) could enable:
- Status reporting (is door locked right now?)
- Automatic locking after timeout when unlocked
- Notifications if door left unlocked
- More intelligent behavior (skip unlock action if already unlocked)

## Physical Installation

### Component Layout

**Exterior (hallway side):**
- Metal peephole (unmodified, serves as capacitive touch sensor)
- Wiring runs through peephole opening to interior

**Interior (apartment side):**
- ESP32 microcontroller
- Servo motor
- 3D printed housing and gearing
- 9V battery (current power source)
- All components enclosed in command strip-mounted assembly

### Mounting System

**Method:** Command strips  
**Mounting surface:** Interior door surface around deadbolt  
**Removability:** 100% reversible, leaves no permanent marks  
**Why this works:** Sufficient holding force for lightweight assembly, no vibration issues observed

### Current Status & Photos

Physical integration is functional and in daily use. Detailed photos of the housing, gearing mechanism, and mounting system will be added to documentation. The assembly wraps around the deadbolt with pins that interface with the thumbturn.

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

### 1. Battery Life Optimization

**Challenge:** System needs to run for months on single battery while remaining instantly responsive.

**Solution:**
- Aggressive deep sleep strategy (~10µA draw)
- Single ultra-low-power wake source (capacitive touch)
- No periodic wake timers
- BLE stack only initialized when needed, then deinitialized to free memory
- Servo detached and pin pulled LOW when not in use
- Result: 3-4 months on 9V battery

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

## Remaining Work & Future Enhancements

### In Progress

**1. BLE UUID-based authentication**
- nRF51822 iBeacon hardware ordered
- Code update required: change scan logic from device name to service UUID 0x2018
- Testing and RSSI re-calibration needed once beacon arrives

### Short-term Improvements

**2. Battery management system**
- Add voltage monitoring to track battery state
- Low-battery warnings (LED blink or servo behavior change)
- Upgrade from 9V to LiPo or 18650 cells
- Add USB-C charging port to housing

**3. Physical refinement**
- Document current housing design with detailed photos
- Iterate on mechanical linkage for smoother operation
- Reduce weight and size where possible
- Improve aesthetics of exterior-facing components

### Long-term Feature Wishlist

**4. Automatic presence detection**
- Eliminate need for peephole tap
- Continuously scan for BLE beacon and auto-unlock when RSSI crosses threshold
- **Major constraint:** Requires near-constant BLE scanning, destroying battery life
- **Possible solution:** Larger battery capacity, solar charging, or hardwired power

**5. Remote lock/unlock capability**
- WiFi or cellular connectivity for remote control
- Lock/unlock from phone app anywhere in the world
- Status notifications when door is unlocked
- **Major constraint:** Continuous connectivity requires significant power
- **Possible solution:** Hybrid approach with sleep/wake cycles, or separate always-on bridge device

**6. Enhanced security**
- Encrypted challenge-response authentication
- Rolling codes to prevent replay attacks
- Multi-factor authentication (BLE + PIN via touch patterns)
- Intrusion detection (failed unlock attempts, physical tampering)

**7. Lock state awareness**
- Limit switches or current sensing to know if door is locked/unlocked
- Enable smarter behavior (skip redundant actions)
- Automatic locking after timeout when unlocked
- Status reporting to user

**8. Multi-user support**
- Multiple trusted BLE beacons (roommates, family, guests)
- Temporary access codes with expiration
- Access logging and audit trail

### Edge Cases to Address

**1. Servo stall conditions**
- What if deadbolt is jammed and servo can't turn it?
- Current sensing could detect stall and retry or alert user
- Timeout mechanism to prevent servo from burning out

**2. False touch triggers**
- Vibration, door slam, accidental brushing against peephole
- Current threshold (40) seems reliable, but long-term monitoring needed
- Could add debouncing or require sustained touch

**3. BLE scan timeout behavior**
- What if BLE scan takes longer than expected?
- Current 1-second timeout may be too short in noisy RF environments
- Adjustable scan duration based on environment

**4. Battery failure states**
- What happens when battery is completely dead?
- Manual key override still works (existing lock remains functional)
- Could add mechanical battery access for emergency replacement

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

**9V battery capacity:** ~500mAh (typical alkaline)  
**Theoretical battery life:** 500mAh ÷ 1.63mAh/day = **307 days (~10 months)**

**Observed battery life:** 3-4 months  
**Discrepancy likely due to:**
- 9V alkaline voltage drop under load
- Inefficient voltage regulation
- Self-discharge
- Peak current demands

**Future improvement path:** LiPo or 18650 lithium cells provide better current delivery, lower self-discharge, and 2-3× capacity for similar weight.

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

## Lessons Learned & Design Philosophy

### 1. Constraints Drive Creativity

The rental property restriction (no permanent installation) forced innovative solutions:
- Command strip mounting instead of screws
- Retrofit approach instead of lock replacement
- Capacitive touch through existing hardware (peephole)
- 3D printed engagement mechanism that wraps around deadbolt

**Result:** More creative, more challenging, more interesting than "just buy a smart lock."

### 2. Real-World Use Reveals Edge Cases

Daily usage exposed problems invisible in lab testing:
- iOS background advertising limitation (discovered after weeks of unreliability)
- Gesture detection UX (tap counting was frustrating, duration-based is intuitive)
- Battery life projections vs. reality (theoretical 10 months vs. actual 3-4)

**Takeaway:** No amount of planning substitutes for real-world deployment and iteration.

### 3. Power Budget is Everything

Every design decision returns to power consumption:
- Why deep sleep? → Battery life
- Why single wake source? → Battery life
- Why BLE over WiFi? → Battery life
- Why no continuous presence detection? → Battery life

**In battery-powered IoT, power budget dictates architecture.**

### 4. Security vs. Usability Trade-offs

Current security model is intentionally pragmatic:
- BLE name/UUID scanning is spoofable (known weakness)
- No encryption or rolling codes (future improvement)
- Lock doesn't require authentication (convenience over security)

**Rationale:** Physical security layer (building access, solid core door, quality deadbolt) is primary defense. Smart lock adds convenience without meaningfully degrading security below traditional key-based lock (also trivially defeated by lock picking, bumping, or brute force).

**Future hardening is planned**, but current implementation balances security and usability for personal use case.

### 5. Iterate, Don't Perfect

Project has evolved significantly:
- WiFi → BLE
- Handle sensing → capacitive touch
- Tap counting → duration detection
- Phone app → hardware beacon

**Each iteration simplified, improved, or solved real problems.** Perfect is the enemy of shipped. Better to deploy and learn than endlessly optimize in isolation.

## Project Status Summary

**Current state:**
- ✅ Functional prototype in daily use
- ✅ Battery life: 3-4 months on 9V
- ✅ Reliable lock/unlock via capacitive touch
- ✅ BLE authentication (phone-based, interim solution)
- ✅ Command strip mounted, fully removable
- ✅ Zero permanent installation or door modification

**In progress:**
- 🔄 Transition to nRF51822 iBeacon hardware (ordered, awaiting delivery)
- 🔄 Code update for UUID-based BLE scanning
- 🔄 Documentation with detailed photos of mechanical assembly

**Planned improvements:**
- 📋 Battery upgrade (LiPo or 18650)
- 📋 Voltage monitoring and low-battery warnings
- 📋 Enhanced security (encrypted authentication)
- 📋 Lock state awareness (limit switches)
- 📋 Remote unlock capability (power budget permitting)

**Continuous iteration philosophy:**
This project will never be "done." Vaughn plans to continually refine, improve, and add features as new constraints emerge, new technologies become available, or new use cases develop.

---

## Why This Project Demonstrates Engineering Competence

For recruiters, hiring managers, and technical evaluators, this project showcases:

**1. Full-stack technical breadth:**
- Embedded systems programming (ESP32, Arduino framework)
- Wireless protocols (BLE scanning, RSSI analysis)
- Power management (deep sleep, µA-level optimization)
- Mechanical engineering (3D printed gearing, servo linkage)
- Hardware integration (capacitive touch, servo control, battery management)

**2. Real-world problem-solving:**
- Navigated hard constraints (rental restrictions, battery power, cost)
- Iterated based on real usage patterns (not lab-perfect theory)
- Made pragmatic trade-offs (security vs. usability, features vs. power budget)

**3. Cross-disciplinary thinking:**
- Combined software, hardware, mechanical, and UX design
- Understood interactions between subsystems (power budget affects feature set)
- Made architectural decisions with long-term maintainability in mind

**4. Practical engineering judgment:**
- Knew when to abandon failing approaches (WiFi, handle sensing, tap counting)
- Identified root causes through systematic debugging (iOS background advertising)
- Balanced "perfect" vs. "good enough for now" (security model, battery choice)

**5. User-centric design:**
- Optimized for daily use convenience (quick tap to unlock)
- Anticipated failure modes (manual key override always works)
- Designed for non-technical users (intuitive touch gestures)

**6. Documentation and communication:**
- Comprehensive technical documentation (this document)
- Clear explanation of design rationale and trade-offs
- Ability to communicate complex technical concepts to non-technical audiences

This is not a tutorial-following exercise or a GitHub clone. This is ground-up engineering that demonstrates the ability to take a real-world problem, navigate constraints, make informed architectural decisions, and ship a working solution that is used daily.
