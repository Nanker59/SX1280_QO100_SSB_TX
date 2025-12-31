# SX1280_QO100_SSB_TX

**Eksperymentalny nadajnik SSB/Digi na satelitę QO-100 oparty na module SX1280 (2.4 GHz)**

## Opis projektu

Demo nadajnika SSB (Single Sideband) i sygnałów cyfrowych na pasmo 2.4 GHz, przeznaczonego do łączności przez transponder wąskopasmowy satelity geostatycznego **QO-100 (Es'hail 2)**.

Projekt wykorzystuje:
- **Raspberry Pi Pico 2** (RP2350) jako główny kontroler
- **Moduł LoRa1280F27-TCXO** (SX1280 + PA + TCXO) jako źródło RF
- **USB Audio Class 1** do przyjmowania audio z komputera (48 kHz stereo → 8 kHz mono)
- **Transformatę Hilberta** do generacji sygnału SSB (USB)
- **Modulację FM** z ditherowaną mocą wyjściową

### Funkcje

- Transmisja SSB (Upper Sideband) na częstotliwości 2400.050 - 2400.300 MHz
- Przetwarzanie audio: filtr pasmowy 300-2700 Hz, equalizator, kompresor
- Adaptive resampling z interpolacją kubiczną Hermite'a
- Test dwutonowy (1000 Hz + 1900 Hz) do kalibracji
- Test CW do weryfikacji toru RF
- Konfiguracja przez USB CDC (port szeregowy)

## Autor

**Kacper SP8ESA**

Kod w całości wygenerowany przy pomocy **Claude Opus 4** (Anthropic).

## Schemat połączeń

```
Raspberry Pi Pico 2          LoRa1280F27-TCXO Module
==================          =======================
GPIO 16 (SPI0 RX)  ───────── MISO
GPIO 17            ───────── NSS (CS)
GPIO 18 (SPI0 SCK) ───────── SCK
GPIO 19 (SPI0 TX)  ───────── MOSI
GPIO 20            ───────── RESET
GPIO 21            ───────── BUSY
GPIO 22            ───────── TCXO_EN (CRITICAL!)
GPIO 14            ───────── RX_EN
GPIO 15            ───────── TX_EN

3V3                ───────── VCC (3.3V)
GND                ───────── GND

USB                ───────── Do komputera (Audio + CDC)
```

### WAŻNE - Moduł TCXO

Moduł LoRa1280F27-TCXO wymaga **włączenia TCXO_EN PRZED resetem SX1280**!
Sekwencja inicjalizacji:
1. TCXO_EN = HIGH
2. Odczekaj min. 3 ms
3. Reset SX1280 (pulse LOW)
4. Użyj SetStandby(STDBY_XOSC) zamiast STDBY_RC

## Kompilacja

### Wymagania
- Pico SDK 2.2.0+
- CMake 3.13+
- ARM GCC toolchain

### Budowanie

```bash
mkdir build && cd build
cmake .. -G Ninja
ninja
```

### Programowanie

```bash
picotool load SX1280SDR.elf -fx
```

## Komendy CDC

Po podłączeniu USB dostępny jest port szeregowy z komendami:

| Komenda | Opis |
|---------|------|
| `help` | Lista komend |
| `diag` | Diagnostyka SX1280 i buforów |
| `get` | Pokaż aktualną konfigurację |
| `cw` | Start testu CW |
| `stop` | Stop transmisji |
| `enable bp 0/1` | Włącz/wyłącz filtr pasmowy |
| `enable eq 0/1` | Włącz/wyłącz equalizator |
| `enable comp 0/1` | Włącz/wyłącz kompresor |
| `set bp_lo <Hz>` | Dolna częstotliwość filtru |
| `set bp_hi <Hz>` | Górna częstotliwość filtru |
| `set comp_thr <dB>` | Próg kompresora |
| `set comp_ratio <n>` | Współczynnik kompresji |

## Konfiguracja

Główne parametry w `main.c`:

```c
#define USE_TCXO_MODULE     1       // 1 dla modułu z TCXO
#define CENTER_FREQ_HZ      2400100000ULL  // Częstotliwość nośna
#define PWR_MAX_DBM         13      // Max moc (dBm do PA)
#define WAV_SAMPLE_RATE     8000    // Częstotliwość próbkowania DSP

#define USE_TEST_TONE       0       // 1 = test tonowy zamiast USB audio
#define USE_TWO_TONE_TEST   1       // 1 = dwuton, 0 = jednoton
```

## Licencja

MIT License - użycie na własną odpowiedzialność.

## Ostrzeżenie

⚠️ **Transmisja na 2.4 GHz wymaga odpowiedniego pozwolenia radiowego!**

Upewnij się, że posiadasz ważną licencję radioamatorską i przestrzegasz przepisów obowiązujących w Twoim kraju.

---

73 de SP8ESA
