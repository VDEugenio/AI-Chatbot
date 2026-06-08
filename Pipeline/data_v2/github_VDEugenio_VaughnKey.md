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

VaughnKey is a retrofit smart lock solution designed for rental properties where replacing the actual door lock isn't permitted. The system wraps around a rounded deadbolt and operates by turning the thumb turn via a servo motor, providing smart lock functionality without modifying the existing hardware.

The project runs on ESP32 firmware and incorporates an innovative tap detection system using capacitive touch on the door's peephole. This allows users to interact with the lock through simple taps on the peephole, creating an intuitive unlocking mechanism.

The Telegram integration serves dual purposes: it provides notifications to keep the user informed of lock activity, and acts as a backup authentication method. When the primary Bluetooth authentication fails, the system sends a Telegram message asking for permission to proceed with unlocking, ensuring the user maintains access even when the primary method isn't working.

This project was motivated by the developer's desire to enhance apartment security and improve the user experience of locking and unlocking their door, while working within the constraints of rental property limitations that prevent lock replacement.