# SX1280 QO-100 SSB TX

**Experimental SSB/Digital transmitter for QO-100 satellite based on SX1280 module (2.4 GHz)**

[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)

## Project Description

SSB (Single Sideband) and digital modes transmitter for the 2.4 GHz band, designed for communication via the narrowband transponder of the geostationary satellite **QO-100 (Es'hail 2)**.

### Features

- 📻 **USB Audio** - Pico acts as USB sound card, audio input directly from computer
- 📡 **Output power up to +27 dBm** - Built-in PA in LoRa1280F27 module
- 🎛️ **Real-time DSP** - Bandpass filter, equalizer, compressor
- 🔧 **USB CDC configuration** - Serial port for parameter control
- 🎯 **PPM correction** - Precise frequency tuning
- ⏱️ **Beacon mode** - Automatic CW when USB disconnected (after 10s)
- 🔬 **Two-tone test** - For linearity adjustment

## Author

**Kacper Kidała SP8ESA**

Code generated with assistance from **Claude Opus 4.5** and **GPT 5.2**.

## Hardware

### Required Components

| Component | Description |
|-----------|-------------|
| Raspberry Pi Pico 2 | RP2350 microcontroller |
| LoRa1280F27-TCXO | SX1280 module with PA (+27 dBm) and TCXO |
| 2.4 GHz Antenna | SMA or u.FL connector |

## Wiring Diagram

```
Raspberry Pi Pico 2          LoRa1280F27-TCXO Module
===================          =======================
GPIO 16 (SPI0 RX)  ───────── MISO
GPIO 17            ───────── NSS (CS)
GPIO 18 (SPI0 SCK) ───────── SCK
GPIO 19 (SPI0 TX)  ───────── MOSI
GPIO 20            ───────── RESET
GPIO 21            ───────── BUSY
GPIO 22            ───────── TCXO_EN (CRITICAL!)
GPIO 14            ───────── RX_EN
GPIO 15            ───────── TX_EN

VBUS (5V)          ───────── VCC
GND                ───────── GND

USB                ───────── To computer (Audio + CDC)
```

### IMPORTANT - TCXO Module

The LoRa1280F27-TCXO module requires **TCXO_EN to be HIGH BEFORE SX1280 reset**!

## Building

### Requirements
- Pico SDK 2.0+
- CMake 3.13+
- ARM GCC toolchain

### Build
```bash
mkdir build && cd build
cmake ..
make -j4
```

### Flash
```bash
# Hold BOOTSEL and connect USB
cp SX1280SDR.uf2 /media/$USER/RPI-RP2/
```

## Usage

### USB Audio
1. Connect Pico to computer
2. Select "SX1280 QO-100 SSB TX" as audio output device
3. Transmit using any software (SDR, WSJT-X, fldigi, etc.)

### Beacon Mode
If USB is not connected within 10 seconds of startup, the device automatically starts CW transmission on 2400.300 MHz at full power.

## CDC Commands

After connecting USB, a serial port is available with the following commands:

### Basic Commands

| Command | Description |
|---------|-------------|
| `help` | List commands |
| `get` | Show current configuration |
| `diag` | SX1280 and buffer diagnostics |
| `cw` | Start CW test |
| `stop` | Stop CW transmission |

### Frequency Configuration

| Command | Description |
|---------|-------------|
| `freq <Hz>` | Set center frequency (e.g. `freq 2400100000`) |
| `ppm <value>` | Oscillator PPM correction (e.g. `ppm -1.5`) |

### DSP Block Enable/Disable

| Command | Description |
|---------|-------------|
| `enable bp 0/1` | Enable/disable bandpass filter |
| `enable eq 0/1` | Enable/disable equalizer |
| `enable comp 0/1` | Enable/disable compressor |

### Bandpass Filter Settings

| Command | Description |
|---------|-------------|
| `set bp_lo <Hz>` | Lower filter frequency (default 300 Hz) |
| `set bp_hi <Hz>` | Upper filter frequency (default 2700 Hz) |

### Equalizer Settings

| Command | Description |
|---------|-------------|
| `set eq_low_hz <Hz>` | Low band frequency |
| `set eq_low_db <dB>` | Low band gain |
| `set eq_high_hz <Hz>` | High band frequency |
| `set eq_high_db <dB>` | High band gain |

### Compressor Settings

| Command | Description |
|---------|-------------|
| `set comp_thr <dB>` | Compressor threshold |
| `set comp_ratio <n>` | Compression ratio |
| `set comp_att <ms>` | Attack time |
| `set comp_rel <ms>` | Release time |
| `set comp_makeup <dB>` | Makeup gain |
| `set comp_knee <dB>` | Knee width |
| `set comp_outlim <0..1>` | Output limiter |

### Amplifier Settings

| Command | Description |
|---------|-------------|
| `set amp_gain <float>` | Final gain |
| `set amp_min_a <float>` | Minimum amplitude |

## Technical Specifications

| Parameter | Value |
|-----------|-------|
| Frequency range | 2400-2500 MHz |
| Output power | up to +27 dBm |
| Modulation | SSB (USB), CW |
| Audio sample rate | 48 kHz (USB) → 8 kHz (DSP) |
| TCXO stability | ±0.5 ppm |

## QO-100 Uplink

QO-100 Narrowband Transponder:
- **Uplink:** 2400.050 - 2400.300 MHz
- **Downlink:** 10489.550 - 10489.800 MHz

## Warning

⚠️ **Transmission on 2.4 GHz requires appropriate radio license!**

Make sure you have a valid amateur radio license and comply with regulations in your country.

## License

This project is licensed under **CC BY-NC 4.0** (Creative Commons Attribution-NonCommercial).

- ✅ Non-commercial use (including amateur radio)
- ✅ Modifications allowed
- ❌ Commercial use requires author's permission

This project uses:
- [TinyUSB](https://github.com/hathach/tinyusb) - MIT License
- [Raspberry Pi Pico SDK](https://github.com/raspberrypi/pico-sdk) - BSD-3-Clause

---

73 de SP8ESA 📻🛰️
