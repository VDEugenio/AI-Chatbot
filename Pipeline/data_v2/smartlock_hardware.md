---
name: VaughnKey Hardware, Power, and Mechanical Installation
description: Full hardware build — ESP32, capacitive peephole touch sensor, DS-S012 servo, modified power bank, BLE beacon, 3D-printed housing — plus deep-sleep power architecture and servo/mechanical linkage/command-strip installation that makes the retrofit 100%% reversible.
company: personal
topics: [iot, embedded_systems, ble, low_power, hardware_design, deep_sleep, servo, mechanical_linkage, 3d_printing, installation]
skills: [ESP32, C++, BLE, embedded_programming, hardware_integration, servo_control, mechanical_design, 3d_printing]
story_types: [problem_solving, systems_thinking, product_pitch]
related_files: [smartlock_software.md, smartlock_technical_deepdive.md]
---

## Current System Architecture

### Hardware Components

- **ESP32 microcontroller** — Main controller running Arduino framework. Manages deep sleep, capacitive touch detection, BLE scanning, and servo control. Original ESP32 variant (not ESP32-C3 or ESP32-S3).

- **Capacitive touch sensor (GPIO4, T0)** — Utilizes the door's existing metal peephole as the touch surface. The peephole is naturally conductive and requires no modification. This is the only user input mechanism and the only wake source from deep sleep.

- **DS-S012 servo motor (GPIO18)** — Physically actuates the deadbolt through a 3D printed gear mechanism. Selected after testing multiple servos for correct range of motion and sufficient torque to reliably turn the deadbolt.

- **Modified power bank** — Current power source. A standard USB power bank modified to stay on continuously (bypassing the auto-shutoff that normally cuts power when draw is too low). The ESP32's deep sleep draw (~10µA) would normally trigger a power bank's low-current shutoff, so the modification keeps it powered. Lasts approximately 3-4 months with deep sleep optimization.

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

**Current power performance:**
- Modified power bank lasts approximately 3-4 months
- Future iterations will explore a dedicated LiPo or 18650 cell solution for better form factor and rechargeability

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
- Modified power bank (current power source)
- All components enclosed in command strip-mounted assembly

### Mounting System

**Method:** Command strips
**Mounting surface:** Interior door surface around deadbolt
**Removability:** 100% reversible, leaves no permanent marks
**Why this works:** Sufficient holding force for lightweight assembly, no vibration issues observed

### Current Status & Photos

Physical integration is functional and in daily use. Detailed photos of the housing, gearing mechanism, and mounting system will be added to documentation. The assembly wraps around the deadbolt with pins that interface with the thumbturn.
