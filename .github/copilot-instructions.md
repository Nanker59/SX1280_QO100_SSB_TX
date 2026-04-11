# Copilot Instructions - SX1280 QO-100 SSB TX

## Project Overview

SSB/CW/FM transmitter for QO-100 satellite (Es'hail 2) and general 2.4 GHz amateur use, using SX1280 module and Raspberry Pi Pico 2.
USB Audio or MAX4466 microphone input, real-time DSP processing, output via SX1280 RF chip.

**⚠️ FM mode is NOT for QO-100!** The NB transponder is SSB/CW only.

Key constraint: Dual-core real-time system - Core0 handles USB+DSP+MIC, Core1 handles radio TX at 8kHz rate.

## Tech Stack

- C11 (no C++)
- Raspberry Pi Pico SDK 2.x
- TinyUSB (USB Audio Class 1, CDC)
- ARM Cortex-M33 (RP2350)
- SPI @ 18 MHz for SX1280 communication

## Architecture

### Dual-Core Design

```
Core0 (USB + DSP Producer)          Core1 (Radio Consumer)
┌─────────────────────────┐         ┌─────────────────────────┐
│ USB Audio @ 48kHz       │         │ Timer IRQ @ 8kHz        │
│   or MIC ADC @ 8kHz     │         │ Read from block buffer  │
│ Downsample 48k → 8k    │         │ Hilbert transform       │
│ DSP: BP → EQ → Comp    │ ──────► │ I/Q modulation          │
│ MIC: AGC + noise gate   │         │ SX1280 SPI TX           │
│ Write to block buffer   │         │                         │
│ CDC command handler     │         │                         │
└─────────────────────────┘         └─────────────────────────┘
```

### Block Buffer

- Size: 256 samples × 8 blocks
- Single producer (Core0), single consumer (Core1)
- Adaptive resampling to balance buffer fill level

## Project Structure

```
/
├── main.c                  # All application code
├── ssd1306.c               # OLED display driver (I2C + DMA)
├── ssd1306.h               # OLED driver header
├── usb_descriptors.c       # USB device descriptors
├── usb_descriptors.h       # USB descriptor header
├── tusb_config.h           # TinyUSB configuration
├── gui.py                  # Python GUI (tkinter + pyserial)
├── CMakeLists.txt          # Build configuration
├── pico_sdk_import.cmake   # SDK integration
├── external/
│   └── tinyusb/            # TinyUSB submodule
├── WIRING.txt              # Hardware connections
├── README.md               # Documentation
└── LICENSE                 # CC BY-NC 4.0
```

## SX1280 Radio Chip

### Communication

- SPI Mode 0, 18 MHz
- NSS (CS) active low
- BUSY pin must be checked before each command

### Key Commands

```c
#define CMD_SET_STANDBY           0x80
#define CMD_SET_TX                0x83
#define CMD_SET_RF_FREQUENCY      0x86
#define CMD_SET_TX_PARAMS         0x8E
#define CMD_SET_MODULATION_PARAMS 0x8B  // GFSK BT=0.5
#define CMD_WRITE_BUFFER          0x1A
```

### TCXO Module (LoRa1280F27-TCXO)

CRITICAL: TCXO_EN (GPIO22) must be HIGH **before** reset!

```c
gpio_put(PIN_TCXO_EN, 1);  // Enable TCXO first
sleep_ms(5);
gpio_put(PIN_RESET, 0);    // Then reset
sleep_ms(10);
gpio_put(PIN_RESET, 1);
// Use STDBY_XOSC mode, not STDBY_RC
```

## DSP Pipeline

### Signal Flow (PC / USB Audio)

```
Audio 48kHz → Downsample → Bandpass 300-2700Hz → Equalizer → Compressor → Block Buffer
```

### Signal Flow (MIC / ADC)

```
ADC @ 8kHz (timer ISR) → DC removal (IIR HPF) → Ring buffer → AGC + Noise gate → DSP chain → Block Buffer
```

### MIC Subsystem

- Hardware repeating timer ISR at 8 kHz reads ADC0
- DC removal via IIR high-pass (α = 0.995) in ISR
- Samples pushed to `mic_rb` ring buffer (int16_t, 1024 entries)
- Main loop pops from `mic_rb`, applies AGC envelope follower + noise gate
- Timer started/stopped on audio source switch (CDC `src` command, encoder, boot auto-switch)

### Filters

- IIR Biquad filters (second order sections)
- Bandpass: Butterworth, configurable cutoff
- Equalizer: Low/high shelf
- Compressor: Soft-knee with attack/release

### SSB Modulation (Core1)

```c
// Hilbert transform (FIR, 31 taps)
float i_out = hilbert_filter(sample);  // In-phase (delayed)
float q_out = hilbert_90deg(sample);   // Quadrature

// Amplitude and phase for SX1280
float amplitude = sqrtf(i_out*i_out + q_out*q_out);
float phase = atan2f(q_out, i_out);

// Convert to SX1280 frequency steps with phase modulation
```

### FM Modulation (Core0 block producer, g_tx_mode==2)

```c
// CTCSS sub-audible tone mixed into audio (if enabled)
if (g_ctcss_freq > 0.0f) {
    x = x * 0.85f + 0.15f * sinf(ctcss_phase);  // ~15% deviation
    ctcss_phase += 2*PI * g_ctcss_freq / Fs;
}
// Direct frequency modulation: audio → PLL frequency offset
float fm_offset_hz = x * g_fm_deviation_hz;
float fm_steps = fm_offset_hz / PLL_STEP_HZ;
// Sigma-delta dithering for fractional PLL step
// Constant power, TX gating via OR(g_tx_enabled, g_ptt_key)
// Bypasses Hilbert/SSB path entirely (continue after block fill)
```

- `g_fm_deviation_hz` — runtime adjustable, 200–100000 Hz (default 2500 = NBFM)
- `g_ctcss_freq` — 0 = off, or standard tone 67.0–254.1 Hz
- FM stays in CR_ST_IDLE (Core1 processes blocks like SSB, no carrier state machine)

## CDC Commands

Serial interface for configuration:

```
help              - List commands
diag              - SX1280 diagnostics
freq <Hz>         - Set center frequency (2300000000–2450000000)
ppm <value>       - PPM correction
tx 0/1            - Enable/disable TX
mode usb|cw|fm    - Set modulation mode (⚠️ FM not for QO-100!)
src pc|mic        - Switch audio source (PC=USB, MIC=ADC0)
enable bp|eq|comp 0|1 - Enable/disable DSP blocks
set bp_lo <Hz>    - Bandpass low cutoff
set bp_hi <Hz>    - Bandpass high cutoff
set comp_thr <dB> - Compressor threshold
set mic_agc_target <0..1>  - AGC target level
set mic_agc_max_gain <float> - AGC max gain
set mic_gate_thresh <float>  - Noise gate threshold
set fm_dev <200..100000>   - FM deviation in Hz
set ctcss <freq|0>         - CTCSS tone Hz (0=off)
cw                - Start CW test
stop              - Stop transmission
```

## Coding Guidelines

### Memory

- No dynamic allocation (malloc/free)
- Use static buffers with fixed sizes
- Ring buffer must be power of 2

### Real-time Constraints

- Core1 IRQ handler must complete in <125µs (8kHz rate)
- Avoid division in IRQ - use lookup tables or approximations
- No printf/stdio in Core1

### SPI Access

- Only Core1 accesses SPI (no locking needed)
- Always check BUSY pin before commands
- Use inline functions for performance

### Configuration

- Use `volatile` for shared variables between cores
- Use `__compiler_memory_barrier()` when updating config structs

## Frequency Calculations

```c
// SX1280 PLL step = 52 MHz / 2^18 = 198.364 Hz
#define PLL_STEP_HZ 198.36425781f

uint32_t hz_to_steps(uint64_t hz) {
    return (uint32_t)((hz << 18) / 52000000ULL);
}

// With PPM correction
float ppm_factor = 1.0f + (g_ppm_correction / 1000000.0f);
uint32_t steps = (uint32_t)(base_steps * ppm_factor);
```

## Testing

- Two-tone test: Generate sum of two sines (e.g., 700Hz + 1900Hz)
- CW test: Constant carrier for frequency verification
- Monitor with SDR receiver on 10 GHz downlink

## QO-100 Frequencies

- Uplink: 2400.050 - 2400.300 MHz
- Downlink: 10489.550 - 10489.800 MHz
- Full band range (non-QO-100): 2300 - 2450 MHz

## Common Issues

1. **No TX** - Check TCXO_EN sequence, verify BUSY pin
2. **Frequency drift** - Adjust PPM correction
3. **Audio clicks** - Check buffer underrun, adjust adaptive rate
4. **Distortion** - Reduce amp_gain, check compressor settings
