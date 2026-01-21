#!/usr/bin/env python3
"""
SX1280 QO-100 SSB TX Control GUI
================================
Modern, responsive GUI for controlling the SX1280 SDR transmitter.
Supports all CDC commands and real-time parameter adjustment.

Author: SP8ESA
License: CC BY-NC 4.0
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import queue
import re
from dataclasses import dataclass
from typing import Optional, Callable

# ---- serial
try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    serial = None
    HAS_SERIAL = False


# ============================================================
# CONFIGURATION DATACLASS
# ============================================================

@dataclass
class TxConfig:
    """Mirrors the firmware's audio_cfg_t structure"""
    # RF
    freq_hz: int = 2_400_400_000
    ppm: float = 0.0
    jitter_us: int = 0  # Timing jitter 0-30 µs (reduces 8kHz artifacts)
    tx_power_dbm: int = 13  # Max TX power on SX1280 chip (-18 to +13 dBm)
    
    # Enables
    enable_bp: bool = True
    enable_eq: bool = True
    enable_comp: bool = True
    
    # Bandpass
    bp_lo_hz: float = 50.0
    bp_hi_hz: float = 2900.0
    bp_stages: int = 10  # 1-10, each stage = 12 dB/oct
    
    # EQ
    eq_low_hz: float = 180.0
    eq_low_db: float = 0.0
    eq_high_hz: float = 2380.0
    eq_high_db: float = 24.0
    eq_slope: float = 2.0  # Shelf slope: 0.3=very gentle, 1.0=standard, 2.0=steep
    
    # Compressor
    comp_thr_db: float = -2.5
    comp_ratio: float = 14.0
    comp_attack_ms: float = 161.3
    comp_release_ms: float = 1595.0
    comp_makeup_db: float = 1.0
    comp_knee_db: float = 1.0
    comp_out_limit: float = 0.976
    
    # Power shaping
    amp_gain: float = 2.28
    amp_min_a: float = 0.000002

# ============================================================
# SERIAL BACKEND (CDC)
# ============================================================

class SerialWorker:
    """Thread-safe serial communication handler"""
    
    def __init__(self, rx_queue: queue.Queue):
        self.rx_queue = rx_queue
        self.ser: Optional[serial.Serial] = None
        self.thread: Optional[threading.Thread] = None
        self.stop_evt = threading.Event()
        self.lock = threading.Lock()

    def is_connected(self) -> bool:
        return self.ser is not None and self.ser.is_open

    def connect(self, port: str, baud: int = 115200):
        if not HAS_SERIAL:
            raise RuntimeError("pyserial not installed (pip install pyserial)")
        with self.lock:
            if self.is_connected():
                return
            self.ser = serial.Serial(port=port, baudrate=baud, timeout=0.1, write_timeout=0.5)
            self.stop_evt.clear()
            self.thread = threading.Thread(target=self._rx_loop, daemon=True)
            self.thread.start()

    def disconnect(self):
        with self.lock:
            self.stop_evt.set()
            s = self.ser
            self.ser = None
        if s:
            try:
                s.close()
            except Exception:
                pass

    def send_line(self, line: str):
        line = line.strip()
        if not line:
            return
        data = (line + "\r\n").encode("utf-8", errors="replace")
        with self.lock:
            if not self.is_connected():
                raise RuntimeError("Not connected")
            self.ser.write(data)
            self.ser.flush()

    def _rx_loop(self):
        buf = bytearray()
        while not self.stop_evt.is_set():
            with self.lock:
                s = self.ser
            if not s:
                break
            try:
                chunk = s.read(256)
                if chunk:
                    buf.extend(chunk)
                    while b"\n" in buf:
                        line, _, rest = buf.partition(b"\n")
                        buf = bytearray(rest)
                        txt = line.decode("utf-8", errors="replace").rstrip("\r")
                        self.rx_queue.put(txt)
                else:
                    time.sleep(0.01)
            except Exception as e:
                self.rx_queue.put(f"[SERIAL ERROR] {e}")
                break


# ============================================================
# UI HELPERS
# ============================================================

def list_serial_ports():
    """Get list of available serial ports"""
    if not HAS_SERIAL:
        return []
    ports = []
    for p in serial.tools.list_ports.comports():
        # Prioritize SX1280 device
        if "SX1280" in p.description or "cafe:4073" in str(p.hwid).lower():
            ports.insert(0, (p.device, f"★ {p.device} ({p.description})"))
        else:
            ports.append((p.device, f"{p.device} ({p.description})"))
    return ports


class Debouncer:
    """Debounce rapid function calls"""
    
    def __init__(self, tk_root: tk.Tk, delay_ms: int, fn: Callable):
        self.root = tk_root
        self.delay_ms = delay_ms
        self.fn = fn
        self._after_id = None
        self._last_args = None
        self._last_kwargs = None

    def call(self, *args, **kwargs):
        self._last_args = args
        self._last_kwargs = kwargs
        if self._after_id is not None:
            try:
                self.root.after_cancel(self._after_id)
            except Exception:
                pass
        self._after_id = self.root.after(self.delay_ms, self._fire)

    def _fire(self):
        self._after_id = None
        if self._last_args is not None:
            self.fn(*self._last_args, **(self._last_kwargs or {}))


class LabeledScale(ttk.Frame):
    """Reusable labeled scale widget with value display"""
    
    def __init__(self, parent, label: str, var: tk.Variable, 
                 from_: float, to: float, resolution: float,
                 on_change: Callable, format_str: str = "{:.1f}"):
        super().__init__(parent)
        
        self.var = var
        self.resolution = resolution
        self.on_change = on_change
        self.format_str = format_str
        
        self.columnconfigure(1, weight=1)
        
        # Label
        ttk.Label(self, text=label, width=16, anchor="w").grid(row=0, column=0, sticky="w")
        
        # Scale
        self.scale = ttk.Scale(self, from_=from_, to=to, orient=tk.HORIZONTAL, 
                               variable=var, command=self._on_scale)
        self.scale.grid(row=0, column=1, sticky="ew", padx=(8, 8))
        
        # Value display
        self.value_label = ttk.Label(self, width=10, anchor="e")
        self.value_label.grid(row=0, column=2, sticky="e")
        self._update_value_label()
        
        # Bind for continuous updates
        self.scale.bind("<ButtonRelease-1>", self._on_release)
        
    def _on_scale(self, _val):
        self._update_value_label()
        
    def _on_release(self, _event):
        v = float(self.var.get())
        v = round(v / self.resolution) * self.resolution
        self.var.set(v)
        self._update_value_label()
        self.on_change(v)
        
    def _update_value_label(self):
        v = float(self.var.get())
        if callable(self.format_str):
            text = self.format_str(v)
        else:
            text = self.format_str.format(v)
        self.value_label.config(text=text)


# ============================================================
# MAIN APPLICATION
# ============================================================

class SX1280ControlApp(ttk.Frame):
    """Main application window"""
    
    # RF limits for QO-100 uplink
    FREQ_MIN_HZ = 2_400_000_000
    FREQ_MAX_HZ = 2_400_500_000
    FREQ_STEP_HZ = 100

    def __init__(self, master: tk.Tk):
        super().__init__(master)
        self.master = master
        
        # State
        self.config = TxConfig()
        self.rx_queue: queue.Queue = queue.Queue()
        self.worker = SerialWorker(self.rx_queue)
        
        # Debouncers
        self.debounced_send = Debouncer(master, 150, self._send_cmd_safe)
        self.freq_debouncer = Debouncer(master, 200, self._send_freq)
        
        # Build UI
        self._create_variables()
        self._build_ui()
        self._poll_rx()
        
        # Pack main frame
        self.pack(fill="both", expand=True)

    def _create_variables(self):
        """Create all Tk variables"""
        # Connection
        self.port_var = tk.StringVar()
        self.status_var = tk.StringVar(value="⚫ Disconnected")
        
        # RF
        self.freq_mhz_var = tk.DoubleVar(value=self.config.freq_hz / 1_000_000)
        self.freq_hz_var = tk.StringVar(value=str(self.config.freq_hz))
        self.ppm_var = tk.StringVar(value="0.0")
        self.jitter_var = tk.IntVar(value=self.config.jitter_us)
        self.txpwr_var = tk.IntVar(value=self.config.tx_power_dbm)
        
        # Enables
        self.en_bp_var = tk.BooleanVar(value=self.config.enable_bp)
        self.en_eq_var = tk.BooleanVar(value=self.config.enable_eq)
        self.en_comp_var = tk.BooleanVar(value=self.config.enable_comp)
        
        # Bandpass
        self.bp_lo_var = tk.DoubleVar(value=self.config.bp_lo_hz)
        self.bp_hi_var = tk.DoubleVar(value=self.config.bp_hi_hz)
        self.bp_stages_var = tk.IntVar(value=self.config.bp_stages)
        
        # EQ
        self.eq_low_hz_var = tk.DoubleVar(value=self.config.eq_low_hz)
        self.eq_low_db_var = tk.DoubleVar(value=self.config.eq_low_db)
        self.eq_high_hz_var = tk.DoubleVar(value=self.config.eq_high_hz)
        self.eq_high_db_var = tk.DoubleVar(value=self.config.eq_high_db)
        self.eq_slope_var = tk.DoubleVar(value=self.config.eq_slope)
        
        # Compressor
        self.comp_thr_var = tk.DoubleVar(value=self.config.comp_thr_db)
        self.comp_ratio_var = tk.DoubleVar(value=self.config.comp_ratio)
        self.comp_att_var = tk.DoubleVar(value=self.config.comp_attack_ms)
        self.comp_rel_var = tk.DoubleVar(value=self.config.comp_release_ms)
        self.comp_makeup_var = tk.DoubleVar(value=self.config.comp_makeup_db)
        self.comp_knee_var = tk.DoubleVar(value=self.config.comp_knee_db)
        self.comp_outlim_var = tk.DoubleVar(value=self.config.comp_out_limit)
        
        # Power shaping
        self.amp_gain_var = tk.DoubleVar(value=self.config.amp_gain)
        self.amp_min_a_var = tk.StringVar(value=f"{self.config.amp_min_a:.9f}")

    def _build_ui(self):
        """Build the user interface"""
        self.master.title("SX1280 QO-100 SSB TX Control")
        self.master.geometry("900x800")
        self.master.minsize(600, 500)
        
        # Configure grid weights for responsive layout
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        
        # === Connection Bar ===
        self._build_connection_bar()
        
        # === Main Content (Notebook) ===
        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        # Tab 1: RF & DSP
        self._build_dsp_tab()
        
        # Tab 2: TX Control
        self._build_tx_tab()
        
        # Tab 3: Console
        self._build_console_tab()

    def _build_connection_bar(self):
        """Build the connection toolbar"""
        conn_frame = ttk.Frame(self)
        conn_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        conn_frame.columnconfigure(1, weight=1)
        
        # Port selection
        ttk.Label(conn_frame, text="Port:").grid(row=0, column=0, padx=(0, 5))
        
        ports = list_serial_ports()
        self.port_map = {label: dev for dev, label in ports}
        labels = list(self.port_map.keys()) or ["(no ports found)"]
        self.port_var.set(labels[0] if labels else "")
        
        self.port_combo = ttk.Combobox(conn_frame, textvariable=self.port_var, 
                                        values=labels, state="readonly", width=45)
        self.port_combo.grid(row=0, column=1, sticky="ew", padx=5)
        
        # Buttons
        btn_frame = ttk.Frame(conn_frame)
        btn_frame.grid(row=0, column=2)
        
        ttk.Button(btn_frame, text="🔄", width=3, command=self._refresh_ports).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Connect", command=self._connect).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Disconnect", command=self._disconnect).pack(side="left", padx=2)
        
        # Status
        ttk.Label(conn_frame, textvariable=self.status_var).grid(row=0, column=3, padx=(10, 0))

    def _build_dsp_tab(self):
        """Build the DSP control tab"""
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="RF & DSP")
        
        tab.columnconfigure(0, weight=1)
        
        # === RF Section ===
        rf_frame = ttk.LabelFrame(tab, text="RF / Frequency", padding=10)
        rf_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        rf_frame.columnconfigure(1, weight=1)
        
        # Frequency slider
        ttk.Label(rf_frame, text="Frequency:").grid(row=0, column=0, sticky="w")
        
        freq_slider_frame = ttk.Frame(rf_frame)
        freq_slider_frame.grid(row=0, column=1, sticky="ew", padx=5)
        freq_slider_frame.columnconfigure(0, weight=1)
        
        self.freq_scale = ttk.Scale(freq_slider_frame, 
                                     from_=self.FREQ_MIN_HZ / 1_000_000,
                                     to=self.FREQ_MAX_HZ / 1_000_000,
                                     orient=tk.HORIZONTAL,
                                     variable=self.freq_mhz_var,
                                     command=self._on_freq_slider)
        self.freq_scale.grid(row=0, column=0, sticky="ew")
        
        # Frequency entry
        freq_entry_frame = ttk.Frame(rf_frame)
        freq_entry_frame.grid(row=0, column=2)
        
        self.freq_entry = ttk.Entry(freq_entry_frame, textvariable=self.freq_hz_var, width=14)
        self.freq_entry.pack(side="left")
        self.freq_entry.bind("<Return>", lambda e: self._send_freq_from_entry())
        ttk.Label(freq_entry_frame, text=" Hz").pack(side="left")
        
        # MHz display
        self.freq_mhz_label = ttk.Label(rf_frame, text="2400.1000 MHz", font=("TkDefaultFont", 12, "bold"))
        self.freq_mhz_label.grid(row=1, column=1, sticky="w", padx=5)
        
        # PPM
        ttk.Label(rf_frame, text="PPM correction:").grid(row=2, column=0, sticky="w", pady=(10, 0))
        ppm_frame = ttk.Frame(rf_frame)
        ppm_frame.grid(row=2, column=1, sticky="w", padx=5, pady=(10, 0))
        
        ttk.Entry(ppm_frame, textvariable=self.ppm_var, width=10).pack(side="left")
        ttk.Button(ppm_frame, text="Set", command=self._send_ppm).pack(side="left", padx=5)
        ttk.Label(ppm_frame, text="(-100 to +100)").pack(side="left")
        
        # Timing Jitter
        ttk.Label(rf_frame, text="Timing jitter:").grid(row=3, column=0, sticky="w", pady=(10, 0))
        jitter_frame = ttk.Frame(rf_frame)
        jitter_frame.grid(row=3, column=1, sticky="ew", padx=5, pady=(10, 0))
        jitter_frame.columnconfigure(0, weight=1)
        
        LabeledScale(jitter_frame, "", self.jitter_var, 0, 30, 1,
                     lambda v: self._send_cmd_safe(f"jitter {int(v)}"),
                     lambda v: f"{int(v)} µs (0=off)").pack(fill="x")
        
        # TX Power
        ttk.Label(rf_frame, text="TX Power:").grid(row=4, column=0, sticky="w", pady=(10, 0))
        txpwr_frame = ttk.Frame(rf_frame)
        txpwr_frame.grid(row=4, column=1, sticky="ew", padx=5, pady=(10, 0))
        txpwr_frame.columnconfigure(0, weight=1)
        
        LabeledScale(txpwr_frame, "", self.txpwr_var, -18, 13, 1,
                     lambda v: self._send_cmd_safe(f"txpwr {int(v)}"),
                     lambda v: f"{int(v)} dBm").pack(fill="x")
        
        # === Enable Checkboxes ===
        enable_frame = ttk.LabelFrame(tab, text="DSP Modules", padding=10)
        enable_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        
        ttk.Checkbutton(enable_frame, text="Bandpass Filter", variable=self.en_bp_var,
                        command=lambda: self._send_enable("bp", self.en_bp_var.get())).pack(side="left", padx=20)
        ttk.Checkbutton(enable_frame, text="Equalizer", variable=self.en_eq_var,
                        command=lambda: self._send_enable("eq", self.en_eq_var.get())).pack(side="left", padx=20)
        ttk.Checkbutton(enable_frame, text="Compressor", variable=self.en_comp_var,
                        command=lambda: self._send_enable("comp", self.en_comp_var.get())).pack(side="left", padx=20)
        
        # === Bandpass ===
        bp_frame = ttk.LabelFrame(tab, text="Bandpass Filter", padding=10)
        bp_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        bp_frame.columnconfigure(0, weight=1)
        
        LabeledScale(bp_frame, "Low cutoff (Hz)", self.bp_lo_var, 50, 1500, 10,
                     lambda v: self.debounced_send.call(f"set bp_lo {v:.0f}"),
                     "{:.0f}").pack(fill="x")
        LabeledScale(bp_frame, "High cutoff (Hz)", self.bp_hi_var, 500, 3600, 10,
                     lambda v: self.debounced_send.call(f"set bp_hi {v:.0f}"),
                     "{:.0f}").pack(fill="x")
        LabeledScale(bp_frame, "Steepness (stages)", self.bp_stages_var, 1, 10, 1,
                     lambda v: self.debounced_send.call(f"set bp_stages {int(v)}"),
                     lambda v: f"{int(v)} ({int(v)*12} dB/oct)").pack(fill="x")
        
        # === EQ ===
        eq_frame = ttk.LabelFrame(tab, text="Equalizer (Shelving)", padding=10)
        eq_frame.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        eq_frame.columnconfigure(0, weight=1)
        
        LabeledScale(eq_frame, "Low shelf freq (Hz)", self.eq_low_hz_var, 50, 1000, 10,
                     lambda v: self.debounced_send.call(f"set eq_low_hz {v:.0f}"),
                     "{:.0f}").pack(fill="x")
        LabeledScale(eq_frame, "Low shelf gain (dB)", self.eq_low_db_var, -24, 24, 0.5,
                     lambda v: self.debounced_send.call(f"set eq_low_db {v:.1f}"),
                     "{:.1f}").pack(fill="x")
        LabeledScale(eq_frame, "High shelf freq (Hz)", self.eq_high_hz_var, 500, 3500, 10,
                     lambda v: self.debounced_send.call(f"set eq_high_hz {v:.0f}"),
                     "{:.0f}").pack(fill="x")
        LabeledScale(eq_frame, "High shelf gain (dB)", self.eq_high_db_var, -24, 24, 0.5,
                     lambda v: self.debounced_send.call(f"set eq_high_db {v:.1f}"),
                     "{:.1f}").pack(fill="x")
        LabeledScale(eq_frame, "Shelf slope", self.eq_slope_var, 0.3, 2.0, 0.1,
                     lambda v: self.debounced_send.call(f"set eq_slope {v:.2f}"),
                     lambda v: f"{v:.1f} ({'gentle' if v < 0.7 else 'steep' if v > 1.3 else 'std'})").pack(fill="x")
        
        # === Compressor ===
        comp_frame = ttk.LabelFrame(tab, text="Compressor", padding=10)
        comp_frame.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        comp_frame.columnconfigure(0, weight=1)
        
        LabeledScale(comp_frame, "Threshold (dB)", self.comp_thr_var, -60, 0, 0.5,
                     lambda v: self.debounced_send.call(f"set comp_thr {v:.1f}"),
                     "{:.1f}").pack(fill="x")
        LabeledScale(comp_frame, "Ratio", self.comp_ratio_var, 1, 20, 0.1,
                     lambda v: self.debounced_send.call(f"set comp_ratio {v:.1f}"),
                     "{:.1f}:1").pack(fill="x")
        LabeledScale(comp_frame, "Attack (ms)", self.comp_att_var, 0.1, 200, 0.1,
                     lambda v: self.debounced_send.call(f"set comp_att {v:.1f}"),
                     "{:.1f}").pack(fill="x")
        LabeledScale(comp_frame, "Release (ms)", self.comp_rel_var, 10, 2000, 1,
                     lambda v: self.debounced_send.call(f"set comp_rel {v:.0f}"),
                     "{:.0f}").pack(fill="x")
        LabeledScale(comp_frame, "Makeup gain (dB)", self.comp_makeup_var, 0, 40, 0.5,
                     lambda v: self.debounced_send.call(f"set comp_makeup {v:.1f}"),
                     "{:.1f}").pack(fill="x")
        LabeledScale(comp_frame, "Knee (dB)", self.comp_knee_var, 0, 24, 0.5,
                     lambda v: self.debounced_send.call(f"set comp_knee {v:.1f}"),
                     "{:.1f}").pack(fill="x")
        LabeledScale(comp_frame, "Output limit", self.comp_outlim_var, 0.01, 0.999, 0.001,
                     lambda v: self.debounced_send.call(f"set comp_outlim {v:.3f}"),
                     "{:.3f}").pack(fill="x")
        
        # === Power Shaping ===
        pwr_frame = ttk.LabelFrame(tab, text="Power Shaping", padding=10)
        pwr_frame.grid(row=5, column=0, sticky="ew", pady=(0, 10))
        pwr_frame.columnconfigure(0, weight=1)
        
        LabeledScale(pwr_frame, "Amp gain", self.amp_gain_var, 0.01, 5.0, 0.01,
                     lambda v: self.debounced_send.call(f"set amp_gain {v:.3f}"),
                     "{:.3f}").pack(fill="x")
        
        amp_min_frame = ttk.Frame(pwr_frame)
        amp_min_frame.pack(fill="x", pady=(5, 0))
        ttk.Label(amp_min_frame, text="Amp min A:", width=16).pack(side="left")
        ttk.Entry(amp_min_frame, textvariable=self.amp_min_a_var, width=16).pack(side="left", padx=5)
        ttk.Button(amp_min_frame, text="Set", 
                   command=lambda: self._send_cmd_safe(f"set amp_min_a {self.amp_min_a_var.get()}")
                  ).pack(side="left")

    def _build_tx_tab(self):
        """Build the TX control tab"""
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="TX Control")
        
        tab.columnconfigure(0, weight=1)
        
        # === CW Test ===
        cw_frame = ttk.LabelFrame(tab, text="CW Test Mode", padding=20)
        cw_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        ttk.Label(cw_frame, text="Transmit continuous carrier for testing:").pack(anchor="w")
        
        btn_frame = ttk.Frame(cw_frame)
        btn_frame.pack(pady=10)
        
        self.cw_btn = ttk.Button(btn_frame, text="▶ Start CW", command=self._start_cw, width=15)
        self.cw_btn.pack(side="left", padx=10)
        
        self.stop_btn = ttk.Button(btn_frame, text="⏹ Stop", command=self._stop_cw, width=15)
        self.stop_btn.pack(side="left", padx=10)
        
        # === Quick Commands ===
        cmd_frame = ttk.LabelFrame(tab, text="Quick Commands", padding=20)
        cmd_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        
        quick_btns = ttk.Frame(cmd_frame)
        quick_btns.pack()
        
        ttk.Button(quick_btns, text="GET Config", command=lambda: self._send_cmd_safe("get"), 
                   width=15).pack(side="left", padx=5)
        ttk.Button(quick_btns, text="DIAG", command=lambda: self._send_cmd_safe("diag"),
                   width=15).pack(side="left", padx=5)
        ttk.Button(quick_btns, text="HELP", command=lambda: self._send_cmd_safe("help"),
                   width=15).pack(side="left", padx=5)
        
        # === Manual Command ===
        manual_frame = ttk.LabelFrame(tab, text="Manual Command", padding=10)
        manual_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        manual_frame.columnconfigure(0, weight=1)
        
        self.manual_cmd_var = tk.StringVar()
        cmd_entry = ttk.Entry(manual_frame, textvariable=self.manual_cmd_var)
        cmd_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        cmd_entry.bind("<Return>", lambda e: self._send_manual_cmd())
        
        ttk.Button(manual_frame, text="Send", command=self._send_manual_cmd).grid(row=0, column=1)
        
        # === Status Info ===
        info_frame = ttk.LabelFrame(tab, text="Device Info", padding=10)
        info_frame.grid(row=3, column=0, sticky="nsew", pady=(0, 10))
        tab.rowconfigure(3, weight=1)
        
        self.info_text = tk.Text(info_frame, height=10, wrap="word", state="disabled",
                                  bg="#f5f5f5", font=("Consolas", 10))
        self.info_text.pack(fill="both", expand=True)

    def _build_console_tab(self):
        """Build the console/log tab"""
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Console")
        
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(0, weight=1)
        
        # Log text
        log_frame = ttk.Frame(tab)
        log_frame.grid(row=0, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = tk.Text(log_frame, wrap="word", font=("Consolas", 9))
        self.log_text.grid(row=0, column=0, sticky="nsew")
        
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        # Tag for different message types
        self.log_text.tag_configure("sent", foreground="#0066cc")
        self.log_text.tag_configure("recv", foreground="#006600")
        self.log_text.tag_configure("error", foreground="#cc0000")
        self.log_text.tag_configure("info", foreground="#666666")
        
        # Buttons
        btn_frame = ttk.Frame(tab)
        btn_frame.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        
        ttk.Button(btn_frame, text="Clear Log", command=self._clear_log).pack(side="left")
        ttk.Button(btn_frame, text="Send All Settings", command=self._send_all).pack(side="right")

    # === Connection Methods ===
    
    def _refresh_ports(self):
        ports = list_serial_ports()
        self.port_map = {label: dev for dev, label in ports}
        labels = list(self.port_map.keys()) or ["(no ports found)"]
        self.port_combo["values"] = labels
        if labels:
            self.port_var.set(labels[0])
        self._log("Ports refreshed", "info")

    def _connect(self):
        if not HAS_SERIAL:
            messagebox.showerror("Missing dependency", 
                                "pyserial is required.\nInstall with: pip install pyserial")
            return
        
        label = self.port_var.get()
        port = self.port_map.get(label)
        if not port or "no ports" in label.lower():
            messagebox.showerror("No port", "No serial port selected.")
            return
        
        try:
            self.worker.connect(port)
            self.status_var.set(f"🟢 Connected: {port}")
            self._log(f"Connected to {port}", "info")
            # Request current config
            self.master.after(500, lambda: self._send_cmd_safe("get"))
        except Exception as e:
            messagebox.showerror("Connection failed", str(e))
            self.status_var.set("🔴 Connection failed")

    def _disconnect(self):
        self.worker.disconnect()
        self.status_var.set("⚫ Disconnected")
        self._log("Disconnected", "info")

    # === Command Methods ===
    
    def _send_cmd_safe(self, cmd: str):
        try:
            if not self.worker.is_connected():
                self._log(f"[NOT CONNECTED] {cmd}", "error")
                return
            self.worker.send_line(cmd)
            self._log(f"> {cmd}", "sent")
        except Exception as e:
            self._log(f"[SEND ERROR] {e}", "error")

    def _send_enable(self, which: str, enabled: bool):
        v = "1" if enabled else "0"
        self._send_cmd_safe(f"enable {which} {v}")

    def _on_freq_slider(self, _val):
        mhz = self.freq_mhz_var.get()
        hz = int(round(mhz * 1_000_000))
        hz = self._clamp_freq(hz)
        self.freq_hz_var.set(str(hz))
        self.freq_mhz_label.config(text=f"{hz/1_000_000:.4f} MHz")
        self.freq_debouncer.call(hz)

    def _clamp_freq(self, hz: int) -> int:
        hz = max(self.FREQ_MIN_HZ, min(self.FREQ_MAX_HZ, hz))
        hz = self.FREQ_MIN_HZ + ((hz - self.FREQ_MIN_HZ) // self.FREQ_STEP_HZ) * self.FREQ_STEP_HZ
        return hz

    def _send_freq(self, hz: int):
        self._send_cmd_safe(f"freq {hz}")

    def _send_freq_from_entry(self):
        try:
            hz = int(self.freq_hz_var.get())
            hz = self._clamp_freq(hz)
            self.freq_hz_var.set(str(hz))
            self.freq_mhz_var.set(hz / 1_000_000)
            self.freq_mhz_label.config(text=f"{hz/1_000_000:.4f} MHz")
            self._send_cmd_safe(f"freq {hz}")
        except ValueError:
            messagebox.showerror("Invalid frequency", "Frequency must be an integer in Hz")

    def _send_ppm(self):
        try:
            ppm = float(self.ppm_var.get().replace(",", "."))
            if not -100 <= ppm <= 100:
                raise ValueError("PPM out of range")
            self._send_cmd_safe(f"ppm {ppm}")
        except ValueError as e:
            messagebox.showerror("Invalid PPM", f"PPM must be a number between -100 and +100\n{e}")

    def _start_cw(self):
        self._send_cmd_safe("cw")

    def _stop_cw(self):
        self._send_cmd_safe("stop")

    def _send_manual_cmd(self):
        cmd = self.manual_cmd_var.get().strip()
        if cmd:
            self._send_cmd_safe(cmd)
            self.manual_cmd_var.set("")

    def _send_all(self):
        """Send all current settings to the device"""
        # RF
        hz = self._clamp_freq(int(self.freq_hz_var.get()))
        self._send_cmd_safe(f"freq {hz}")
        
        try:
            ppm = float(self.ppm_var.get().replace(",", "."))
            if -100 <= ppm <= 100:
                self._send_cmd_safe(f"ppm {ppm}")
        except:
            pass
        
        # Jitter
        self._send_cmd_safe(f"jitter {int(self.jitter_var.get())}")
        
        # TX Power
        self._send_cmd_safe(f"txpwr {int(self.txpwr_var.get())}")
        
        # Enables
        self._send_cmd_safe(f"enable bp {'1' if self.en_bp_var.get() else '0'}")
        self._send_cmd_safe(f"enable eq {'1' if self.en_eq_var.get() else '0'}")
        self._send_cmd_safe(f"enable comp {'1' if self.en_comp_var.get() else '0'}")
        
        # Bandpass
        self._send_cmd_safe(f"set bp_lo {self.bp_lo_var.get():.0f}")
        self._send_cmd_safe(f"set bp_hi {self.bp_hi_var.get():.0f}")
        self._send_cmd_safe(f"set bp_stages {int(self.bp_stages_var.get())}")
        
        # EQ
        self._send_cmd_safe(f"set eq_low_hz {self.eq_low_hz_var.get():.0f}")
        self._send_cmd_safe(f"set eq_low_db {self.eq_low_db_var.get():.1f}")
        self._send_cmd_safe(f"set eq_high_hz {self.eq_high_hz_var.get():.0f}")
        self._send_cmd_safe(f"set eq_high_db {self.eq_high_db_var.get():.1f}")
        self._send_cmd_safe(f"set eq_slope {self.eq_slope_var.get():.2f}")
        
        # Compressor
        self._send_cmd_safe(f"set comp_thr {self.comp_thr_var.get():.1f}")
        self._send_cmd_safe(f"set comp_ratio {self.comp_ratio_var.get():.1f}")
        self._send_cmd_safe(f"set comp_att {self.comp_att_var.get():.1f}")
        self._send_cmd_safe(f"set comp_rel {self.comp_rel_var.get():.0f}")
        self._send_cmd_safe(f"set comp_makeup {self.comp_makeup_var.get():.1f}")
        self._send_cmd_safe(f"set comp_knee {self.comp_knee_var.get():.1f}")
        self._send_cmd_safe(f"set comp_outlim {self.comp_outlim_var.get():.3f}")
        
        # Power shaping
        self._send_cmd_safe(f"set amp_gain {self.amp_gain_var.get():.3f}")
        self._send_cmd_safe(f"set amp_min_a {self.amp_min_a_var.get()}")
        
        self._log("All settings sent", "info")

    # === Logging ===
    
    def _log(self, msg: str, tag: str = "recv"):
        self.log_text.insert("end", msg + "\n", tag)
        self.log_text.see("end")
        
        # Also update info text for certain responses
        if "CFG:" in msg or "===" in msg or "Status:" in msg:
            self.info_text.config(state="normal")
            self.info_text.insert("end", msg + "\n")
            self.info_text.see("end")
            self.info_text.config(state="disabled")

    def _clear_log(self):
        self.log_text.delete("1.0", "end")
        self.info_text.config(state="normal")
        self.info_text.delete("1.0", "end")
        self.info_text.config(state="disabled")

    def _poll_rx(self):
        """Poll for received serial data"""
        try:
            while True:
                line = self.rx_queue.get_nowait()
                self._log(line, "recv")
        except queue.Empty:
            pass
        self.master.after(50, self._poll_rx)


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def main():
    root = tk.Tk()
    
    # Try to use a modern theme
    style = ttk.Style(root)
    available_themes = style.theme_names()
    for theme in ["clam", "alt", "default"]:
        if theme in available_themes:
            style.theme_use(theme)
            break
    
    # Custom styles
    style.configure("TLabelframe.Label", font=("TkDefaultFont", 10, "bold"))
    
    app = SX1280ControlApp(root)
    
    # Clean shutdown
    def on_close():
        app.worker.disconnect()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
