# SX1280_QO100_SSB_TX

**Eksperymentalny nadajnik SSB/Digi na satelitę QO-100 oparty na module SX1280 (2.4 GHz)**

## Opis projektu

Demo nadajnika SSB (Single Sideband) i sygnałów cyfrowych na pasmo 2.4 GHz, przeznaczonego do łączności przez transponder wąskopasmowy satelity geostatycznego **QO-100 (Es'hail 2)**.

### Funkcje

- Transmisja SSB (Upper Sideband) na częstotliwości 2400.000 - 2400.500 MHz
- Przetwarzanie audio: filtr pasmowy 300-2700 Hz, equalizer, kompresor
- Konfiguracja przez USB CDC (port szeregowy)

## Autor

**Kacper Kidała SP8ESA**

Kod wygenerowany przy pomocy **Claude Opus 4.5** i **GPT 5.2** .

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

## Komendy CDC

Po podłączeniu USB dostępny jest port szeregowy z komendami:

### Komendy podstawowe

| Komenda | Opis |
|---------|------|
| `help` | Lista komend |
| `get` | Pokaż aktualną konfigurację |
| `diag` | Diagnostyka SX1280 i buforów |
| `cw` | Start testu CW |
| `stop` | Stop transmisji CW |

### Konfiguracja częstotliwości

| Komenda | Opis |
|---------|------|
| `freq <Hz>` | Ustaw częstotliwość centralną (np. `freq 2400100000`) |
| `ppm <value>` | Korekcja PPM oscylatora (np. `ppm -1.5`) |

### Włączanie/wyłączanie bloków DSP

| Komenda | Opis |
|---------|------|
| `enable bp 0/1` | Włącz/wyłącz filtr pasmowy |
| `enable eq 0/1` | Włącz/wyłącz equalizator |
| `enable comp 0/1` | Włącz/wyłącz kompresor |

### Ustawienia filtru pasmowego

| Komenda | Opis |
|---------|------|
| `set bp_lo <Hz>` | Dolna częstotliwość filtru (domyślnie 300 Hz) |
| `set bp_hi <Hz>` | Górna częstotliwość filtru (domyślnie 2700 Hz) |

### Ustawienia equalizera

| Komenda | Opis |
|---------|------|
| `set eq_low_hz <Hz>` | Częstotliwość niskiego pasma |
| `set eq_low_db <dB>` | Wzmocnienie niskiego pasma |
| `set eq_high_hz <Hz>` | Częstotliwość wysokiego pasma |
| `set eq_high_db <dB>` | Wzmocnienie wysokiego pasma |

### Ustawienia kompresora

| Komenda | Opis |
|---------|------|
| `set comp_thr <dB>` | Próg kompresora |
| `set comp_ratio <n>` | Współczynnik kompresji |
| `set comp_att <ms>` | Czas ataku |
| `set comp_rel <ms>` | Czas powrotu |
| `set comp_makeup <dB>` | Wzmocnienie makeup |
| `set comp_knee <dB>` | Szerokość knee |
| `set comp_outlim <0..1>` | Limiter wyjściowy |

### Ustawienia wzmacniacza

| Komenda | Opis |
|---------|------|
| `set amp_gain <float>` | Wzmocnienie końcowe |
| `set amp_min_a <float>` | Minimalna amplituda


## Ostrzeżenie

⚠️ **Transmisja na 2.4 GHz wymaga odpowiedniego pozwolenia radiowego!**

Upewnij się, że posiadasz ważną licencję radioamatorską i przestrzegasz przepisów obowiązujących w Twoim kraju.

---

73 de SP8ESA
