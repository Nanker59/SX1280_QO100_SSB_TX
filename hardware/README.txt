KiCad symbol + footprint: NiceRF LoRa1280F27-TCXO / LoRa128xF27 series

Zawartość:
  - symbols/NiceRF_RF_Module.kicad_sym
      Symbol: NiceRF_LoRa1280F27_TCXO
  - footprints/NiceRF_RF_Module.pretty/NiceRF_LoRa1280F27_TCXO.kicad_mod
      Footprint: NiceRF_LoRa1280F27_TCXO

Źródła wymiarów:
  - Na podstawie rysunku mechanicznego, który wkleiłeś (31.54 x 15.80 mm) oraz rozkładu pinów.
  - Rozmieszczenie 6 padów (piny 13-18) zostało odtworzone z rysunku (nie jest równomierne).

Ważne:
  - To jest footprint pod moduł z wyprowadzeniami typu castellated/half-hole.
  - Zalecam weryfikację na wydruku 1:1 (PDF z KiCada) i porównanie z fizycznym modułem.
  - Jeśli producent wymaga keepout pod antenę / brak miedzi pod fragmentem modułu, dodaj keepout w PCB wg datasheetu.

Instalacja w KiCad:
  1) W KiCad: Preferences -> Manage Symbol Libraries -> Add (Global lub Project) -> wskaż symbols/NiceRF_RF_Module.kicad_sym
  2) Preferences -> Manage Footprint Libraries -> Add -> wskaż folder footprints/NiceRF_RF_Module.pretty
  3) W schemacie wstaw symbol NiceRF_LoRa1280F27_TCXO, potem w polu Footprint przypisz NiceRF_RF_Module:NiceRF_LoRa1280F27_TCXO

Pinout (TCXO):
  1 VCC
  2 TCXOEN
  3 NRESET
  4 BUSY
  5 DIO1
  6 DIO2
  7 DIO3
  8 NSS
  9 SCK
  10 MOSI
  11 MISO
  12 GND
  13 TXEN
  14 RXEN
  15 GND
  16 GND
  17 ANT
  18 GND


Zmiany footprintu (v3):
  - Skrócone pady krawędziowe: długość (X) 3.00 mm (z zachowaniem tej samej krawędzi zewnętrznej przez przesunięcie padów na zewnątrz).
  - Po stronie z 12 pinami (piny 1–12): zwężone pady: szerokość (Y) 0.90 mm dla większego odstępu między padami.
  - Po stronie z 6 pinami (piny 13–18): szerokość (Y) pozostaje 1.10 mm.


[Footprint orientation note]
This footprint is mirrored LEFT-RIGHT relative to the earlier draft: pin 1 marker is on the TOP-RIGHT in KiCad top view. Pads 1–12 are on the right edge, pads 13–18 on the left edge.
