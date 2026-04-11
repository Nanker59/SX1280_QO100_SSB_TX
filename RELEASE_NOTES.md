# Release v2.1.1 — 11 April 2026

This release adds initial FM support and GUI controls, plus a few UX improvements and safety notes.

IMPORTANT: DO NOT TRANSMIT FM ON QO-100
- The FM mode in this firmware is intended for use on licensed uplink frequencies outside the QO-100 narrowband transponder. The QO-100 NB transponder is for SSB/CW; transmitting FM will interfere with other users and is prohibited. Always use FM only on appropriate amateur bands and with knowledge of local rules.

What's new in v2.1.1
- Firmware:
  - Added FM transmit mode (mode `fm`) with runtime adjustable deviation (`set fm_dev <Hz>`).
  - Added support for CTCSS sub-audible tones (`set ctcss <freq|0>`). CTCSS is mixed into FM audio.
  - FM now uses a runtime `g_fm_deviation_hz` (default 2500 Hz) instead of a fixed compile-time constant.
  - CDC status push includes `fm_dev` and `ctcss` fields for GUI sync.
  - Encoder UI cycles through USB → CW → FM.
  - Full-band option: GUI + firmware allow operation from 2300–2450 MHz (use with caution & correct hardware).

- GUI:
  - FM mode radio button and FM Settings panel (Deviation slider 200 Hz–100 kHz and CTCSS combobox).
  - Downlink display in GUI/OLED is hidden when operating outside the QO-100 narrowband range.
  - Added a simple Spectrum Analyzer placeholder canvas in the RF & DSP tab (placeholder for future FFT display).

- Misc / housekeeping:
  - Status push format updated so the GUI can reflect FM and CTCSS settings.
  - Small bugfixes and UI polish.

Notes / follow-ups
- The Spectrum Analyzer in the GUI is a placeholder for now; adding a real FFT-based plot will be done in a follow-up change.
- Removed the S-meter / audio level display from the immediate todo list.
- Suggested improvement: add GPSDO (GPS-disciplined oscillator) or a disciplined 10 MHz reference for improved frequency stability and accuracy; recommend adding optional TCXO/GPSDO integration for field use.

Security & Safety
- DO NOT transmit FM on QO-100's narrowband transponder. The firmware contains an explicit warning. The operator is responsible for legal and courteous operation.

How to get v2.1.1
- Tag: `v2.1.1`
- Git: pull from the master branch and/or checkout the `v2.1.1` tag after it is pushed to the remote.

---
SP8ESA / SX1280_QO100_SSB_TX
