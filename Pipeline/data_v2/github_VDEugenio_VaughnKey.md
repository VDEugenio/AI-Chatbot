---
name: VaughnKey (GitHub Repository)
company: github
topics: [github, portfolio, open_source]
skills: []
story_types: [project]
---

## Recent Activity

- [2026-04-10] Update README with improved project description
- [2026-04-10] Clarify Telegram ability in README
- [2026-04-10] Updated README
- [2026-04-10] Use TLS certificate validation for Telegram API
- [2026-04-10] Initial commit: tap detection telegram firmware

## File Structure

- tap_detection_telegram/

## Developer Notes

VaughnKey is a retrofit smart lock solution designed to work within rental constraints where permanent modifications aren't allowed. The system addresses the common problem of wanting smart lock functionality without being able to replace existing hardware. The core innovation is using the door's metal peephole as a touch-sensitive interface - a simple tap unlocks the door while a longer hold locks it.

The hardware consists of an ESP32 microcontroller connected to a servo motor that physically turns the existing deadbolt. The entire system mounts using removable command strips and runs on a modified power bank, utilizing deep sleep functionality to maximize battery life. Before unlocking, the system verifies the user's phone is nearby via BLE authentication.

The firmware is implemented in C++ using the Arduino framework for ESP32, leveraging standard Arduino libraries alongside ESP32-specific APIs for deep sleep management and BLE functionality. This approach provides a more accessible development environment compared to working directly with ESP-IDF.

Telegram integration serves dual purposes: providing real-time notifications for all lock/unlock events and BLE authentication results, and offering a backup control method when BLE authentication fails. Users receive prompts through Telegram to manually authorize unlocking when the primary BLE verification doesn't succeed, ensuring reliable access while maintaining security.