---
name: VaughnKey Lessons, Future Work, Status, and Engineering Competence
description: Five design-philosophy lessons (constraints-drive-creativity, real-world edge cases, power budget is everything, security/usability tradeoffs, iterate-don't-perfect); remaining work and future enhancements (BLE UUID, battery mgmt, physical refinement, auto-presence, remote, security hardening, state awareness, multi-user); edge cases to address; current project status; and why this project demonstrates engineering competence.
company: personal
topics: [iot, embedded_systems, ble, low_power, hardware_design, firmware, lessons_learned, future_work, project_status, engineering_competence]
skills: [ESP32, C++, BLE, embedded_programming, documentation, project_management, engineering_judgment]
story_types: [problem_solving, systems_thinking, product_pitch, technical_leadership]
related_files: [smartlock_dev_and_challenges.md, smartlock_overview.md, smartlock_technical_deepdive.md]
---

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
