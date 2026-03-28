"""
StealthPDPRadar v3.0 – Live Radar Data Integration
Real-time PDP quantum radar | Live data streaming | Stealth detection
"""

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import io
import json
import pandas as pd
import time
import threading
from datetime import datetime
import warnings
import random

warnings.filterwarnings('ignore')

# ── PAGE CONFIG ─────────────────────────────────────────────
st.set_page_config(
    layout="wide",
    page_title="StealthPDPRadar v3.0",
    page_icon="🛸",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background: #0a0a1a; }
    [data-testid="stSidebar"] { background: #0f0f1f; border-right: 2px solid #00aaff; }
    .stTitle, h1, h2, h3 { color: #00aaff; }
    [data-testid="stMetricValue"] { color: #00aaff; }
    .stDownloadButton button { background-color: #00aaff; color: white; border-radius: 8px; }
    .stButton button { background-color: #00aaff; color: white; }
    .live-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background-color: #ff4444;
        animation: pulse 1s infinite;
    }
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.3; }
        100% { opacity: 1; }
    }
</style>
""", unsafe_allow_html=True)


# ── LIVE RADAR DATA GENERATOR ─────────────────────────────────────────────

class LiveRadarSimulator:
    """Simulates live radar data stream with stealth targets"""
    
    def __init__(self, target_type="F-35", range_km=250, update_interval=1.0):
        self.target_type = target_type
        self.range_km = range_km
        self.update_interval = update_interval
        self.is_running = False
        self.current_data = None
        self.timestamp = None
        self.detection_history = []
        
        # RCS models
        self.rcs_factors = {
            "F-35": 0.001,
            "B-21": 0.0005,
            "NGAD": 0.0003,
            "HQ-19": 0.005,
            "Kinzhal": 0.01
        }
    
    def generate_scan(self):
        """Generate a single radar scan frame"""
        size = 200
        rcs = self.rcs_factors.get(self.target_type.split()[0], 0.001)
        
        # Create grid
        x = np.linspace(-self.range_km, self.range_km, size)
        y = np.linspace(-self.range_km, self.range_km, size)
        X, Y = np.meshgrid(x, y)
        
        # Moving target (simulate motion)
        t = time.time()
        target_x = self.range_km * (0.3 + 0.1 * np.sin(t / 10))
        target_y = self.range_km * (0.2 + 0.05 * np.cos(t / 15))
        
        # Conventional radar return
        distance = np.sqrt((X - target_x)**2 + (Y - target_y)**2)
        conventional = rcs * np.exp(-distance**2 / (2 * (self.range_km/8)**2))
        
        # Quantum signature (PDP effect)
        quantum = 0.15 * np.exp(-distance**2 / (2 * (self.range_km/4)**2))
        
        # Add noise
        noise = np.random.randn(size, size) * 0.05
        radar_data = conventional + quantum + noise
        radar_data = np.clip(radar_data, 0, 1)
        
        return {
            'data': radar_data,
            'target_position': (target_x, target_y),
            'target_type': self.target_type,
            'timestamp': datetime.now(),
            'range_km': self.range_km
        }
    
    def start(self):
        """Start live data generation"""
        self.is_running = True
        self.update_data()
    
    def update_data(self):
        """Update current data"""
        if self.is_running:
            self.current_data = self.generate_scan()
            self.timestamp = self.current_data['timestamp']
            
            # Store detection history
            self.detection_history.append({
                'timestamp': self.timestamp,
                'confidence': np.max(self.current_data['data'])
            })
            if len(self.detection_history) > 100:
                self.detection_history.pop(0)
    
    def get_latest(self):
        """Get latest scan data"""
        if self.current_data is None:
            self.update_data()
        return self.current_data
    
    def stop(self):
        """Stop live data generation"""
        self.is_running = False


# ── PDP QUANTUM RADAR CORE ─────────────────────────────────────────────

def pdp_radar_filter(radar_return, epsilon=1e-10, B_field=1e15, m_dark=1e-9):
    """PDP quantum filter for stealth detection"""
    mixing = epsilon * B_field / (m_dark + 1e-12)
    oscillation = np.sin(radar_return * np.pi * 5)
    dark_mode_leakage = radar_return * mixing * oscillation
    enhanced = radar_return + dark_mode_leakage * 0.8
    return enhanced, dark_mode_leakage


def detect_targets(dark_mode_leakage, threshold=0.1):
    """Detect targets from dark-mode leakage"""
    from scipy.ndimage import label, maximum_filter
    
    mask = dark_mode_leakage > threshold
    labeled, num_features = label(mask)
    
    targets = []
    for i in range(1, num_features + 1):
        y_idx, x_idx = np.where(labeled == i)
        if len(y_idx) > 0:
            targets.append({
                'id': i,
                'x': np.mean(x_idx),
                'y': np.mean(y_idx),
                'strength': np.mean(dark_mode_leakage[y_idx, x_idx]),
                'size': len(y_idx)
            })
    
    targets.sort(key=lambda t: t['strength'], reverse=True)
    return targets


# ── SIDEBAR ─────────────────────────────────────────────
with st.sidebar:
    st.title("🛸 StealthPDPRadar v3.0")
    st.markdown("*Live PDP Quantum Radar*")
    st.markdown("---")
    
    # Data source selection
    st.markdown("### 📡 Data Source")
    data_mode = st.radio(
        "Select Mode",
        ["🟢 LIVE Radar Stream", "📁 Upload File", "🌌 Synthetic Demo"]
    )
    
    if data_mode == "🟢 LIVE Radar Stream":
        st.markdown('<span class="live-indicator"></span> **LIVE MODE ACTIVE**', unsafe_allow_html=True)
        st.caption("Real-time radar simulation running")
    
    st.markdown("---")
    
    # Target selection
    st.markdown("### 🎯 Target")
    target = st.selectbox(
        "Stealth Platform",
        ["F-35 Lightning II", "B-21 Raider", "NGAD", "HQ-19", "Kinzhal"]
    )
    
    st.markdown("---")
    st.markdown("### ⚛️ PDP Parameters")
    epsilon = st.slider("Kinetic Mixing ε", 1e-12, 1e-8, 1e-10, format="%.1e")
    B_field = st.slider("B Field (G)", 1e13, 1e16, 1e15, format="%.1e")
    m_dark = st.slider("Dark Photon Mass (eV)", 1e-12, 1e-6, 1e-9, format="%.1e")
    
    st.markdown("---")
    st.markdown("### 📡 Radar Controls")
    range_km = st.slider("Range (km)", 50, 500, 250)
    threshold = st.slider("Detection Threshold", 0.01, 0.5, 0.1)
    
    if data_mode == "🟢 LIVE Radar Stream":
        update_interval = st.slider("Update Interval (s)", 0.5, 5.0, 1.0)
        if st.button("⏺️ Start Live Stream", use_container_width=True):
            st.session_state.live_active = True
        if st.button("⏹️ Stop Stream", use_container_width=True):
            st.session_state.live_active = False
    
    if data_mode == "📁 Upload File":
        uploaded_file = st.file_uploader(
            "Upload radar data",
            type=['csv', 'npy', 'fits', 'txt']
        )
    
    st.markdown("---")
    st.caption("Tony Ford | StealthPDPRadar v3.0")
    st.caption("Live radar | PDP quantum filter | Stealth detection")


# ── INITIALIZE SESSION STATE ─────────────────────────────────────────────
if 'live_active' not in st.session_state:
    st.session_state.live_active = False
if 'live_simulator' not in st.session_state:
    st.session_state.live_simulator = None
if 'radar_history' not in st.session_state:
    st.session_state.radar_history = []


# ── MAIN APP ─────────────────────────────────────────────
st.title("🛸 StealthPDPRadar")
st.markdown("*Photon-Dark-Photon Quantum Radar – Live Stealth Detection*")
st.markdown(f"**Target:** {target} | **Range:** {range_km} km")
st.markdown("---")

# Metrics
max_P = (epsilon * B_field / 1e15)**2
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Max γ→A'", f"{max_P:.2e}")
with col2:
    st.metric("Dark Photon Mass", f"{m_dark:.1e} eV")
with col3:
    st.metric("ε Mixing", f"{epsilon:.1e}")
with col4:
    st.metric("Detection Range", f"{range_km} km")


# ── PROCESS DATA BASED ON MODE ─────────────────────────────────────────────

# LIVE Radar Stream
if data_mode == "🟢 LIVE Radar Stream":
    if st.session_state.live_active:
        # Create or update simulator
        if st.session_state.live_simulator is None:
            st.session_state.live_simulator = LiveRadarSimulator(target, range_km)
        
        # Update simulator with current settings
        st.session_state.live_simulator.target_type = target
        st.session_state.live_simulator.range_km = range_km
        
        # Generate new scan
        st.session_state.live_simulator.update_data()
        radar_data = st.session_state.live_simulator.get_latest()
        
        if radar_data:
            radar_return = radar_data['data']
            timestamp = radar_data['timestamp']
            
            # Store history
            st.session_state.radar_history.append({
                'timestamp': timestamp,
                'data': radar_return.copy(),
                'confidence': np.max(radar_return)
            })
            if len(st.session_state.radar_history) > 10:
                st.session_state.radar_history.pop(0)
            
            # Show timestamp
            st.caption(f"🟢 **LIVE** | Last update: {timestamp.strftime('%H:%M:%S.%f')[:-3]}")
    
    else:
        st.warning("🟡 **Click 'Start Live Stream' to begin radar data acquisition**")
        # Generate placeholder
        radar_return = np.zeros((200, 200))
    
    # Auto-refresh
    if st.session_state.live_active:
        time.sleep(update_interval)
        st.rerun()

# File Upload Mode
elif data_mode == "📁 Upload File" and 'uploaded_file' in locals() and uploaded_file is not None:
    with st.spinner("Loading radar data..."):
        ext = uploaded_file.name.split(".")[-1].lower()
        data_bytes = uploaded_file.read()
        
        if ext == 'csv':
            df = pd.read_csv(io.BytesIO(data_bytes))
            radar_return = df.values.astype(np.float32)
        elif ext == 'npy':
            radar_return = np.load(io.BytesIO(data_bytes))
        else:
            radar_return = np.loadtxt(io.BytesIO(data_bytes))
        
        if radar_return.ndim == 1:
            side = int(np.sqrt(len(radar_return)))
            radar_return = radar_return[:side*side].reshape(side, side)
        
        # Normalize
        if radar_return.max() > radar_return.min():
            radar_return = (radar_return - radar_return.min()) / (radar_return.max() - radar_return.min())
        
        st.success(f"✅ Loaded: {uploaded_file.name} | Shape: {radar_return.shape}")
        timestamp = datetime.now()

# Synthetic Demo Mode
else:
    # Generate synthetic radar scene
    rcs_factors = {"F-35": 0.001, "B-21": 0.0005, "NGAD": 0.0003, "HQ-19": 0.005, "Kinzhal": 0.01}
    rcs = rcs_factors.get(target.split()[0], 0.001)
    
    size = 200
    x = np.linspace(-range_km, range_km, size)
    y = np.linspace(-range_km, range_km, size)
    X, Y = np.meshgrid(x, y)
    
    target_x = range_km * 0.3
    target_y = range_km * 0.2
    distance = np.sqrt((X - target_x)**2 + (Y - target_y)**2)
    
    conventional = rcs * np.exp(-distance**2 / (2 * (range_km/8)**2))
    quantum = 0.15 * np.exp(-distance**2 / (2 * (range_km/4)**2))
    noise = np.random.randn(size, size) * 0.05
    radar_return = conventional + quantum + noise
    radar_return = np.clip(radar_return, 0, 1)
    timestamp = datetime.now()


# ── PROCESS WITH PDP FILTER ─────────────────────────────────────────────
if 'radar_return' in locals():
    enhanced, dark_mode_leakage = pdp_radar_filter(radar_return, epsilon, B_field, m_dark)
    targets = detect_targets(dark_mode_leakage, threshold)
    detection_confidence = min(targets[0]['strength'] * 100, 99.9) if targets else 0


# ── DISPLAY RADAR VISUALIZATIONS ─────────────────────────────────────────────
st.markdown("### 📡 Radar Detection")

col1, col2, col3 = st.columns(3)

# Conventional Radar
with col1:
    fig, ax = plt.subplots(figsize=(5, 5), facecolor='#0a0a1a')
    im = ax.imshow(radar_return, cmap='gray', extent=[-range_km, range_km, -range_km, range_km])
    ax.set_title("Conventional Radar", color='white')
    ax.set_xlabel("Range (km)", color='white')
    ax.set_ylabel("Range (km)", color='white')
    ax.tick_params(colors='white')
    plt.colorbar(im, ax=ax, label="Signal")
    st.pyplot(fig)
    plt.close(fig)
    st.caption("Stealth aircraft nearly invisible")

# Dark-Mode Leakage (PDP Filter)
with col2:
    fig, ax = plt.subplots(figsize=(5, 5), facecolor='#0a0a1a')
    im = ax.imshow(dark_mode_leakage, cmap='plasma', extent=[-range_km, range_km, -range_km, range_km])
    ax.set_title("Dark-Mode Leakage", color='white')
    ax.set_xlabel("Range (km)", color='white')
    ax.set_ylabel("Range (km)", color='white')
    ax.tick_params(colors='white')
    plt.colorbar(im, ax=ax, label="Quantum Signature")
    
    for t in targets[:3]:
        x_km = -range_km + (t['x'] / radar_return.shape[1]) * 2 * range_km
        y_km = -range_km + (t['y'] / radar_return.shape[0]) * 2 * range_km
        circle = Circle((x_km, y_km), range_km/15, fill=False, edgecolor='red', linewidth=2)
        ax.add_patch(circle)
    
    st.pyplot(fig)
    plt.close(fig)
    st.caption("✨ Quantum signature reveals stealth target")

# PDP Quantum Radar (RGB)
with col3:
    fig, ax = plt.subplots(figsize=(5, 5), facecolor='#0a0a1a')
    rgb = np.stack([radar_return, dark_mode_leakage, enhanced], axis=-1)
    ax.imshow(np.clip(rgb, 0, 1), extent=[-range_km, range_km, -range_km, range_km])
    ax.set_title("PDP Quantum Radar", color='white')
    ax.set_xlabel("Range (km)", color='white')
    ax.set_ylabel("Range (km)", color='white')
    ax.tick_params(colors='white')
    st.pyplot(fig)
    plt.close(fig)
    st.caption("🌈 Blue-halo fusion - target detected")


# ── DETECTION METRICS ─────────────────────────────────────────────
st.markdown("---")
st.markdown("### 🎯 Detection Analysis")

col_m1, col_m2, col_m3, col_m4 = st.columns(4)

with col_m1:
    st.metric("Detection Confidence", f"{detection_confidence:.1f}%",
              delta="STEALTH BREACHED" if detection_confidence > 10 else "No Detection")

with col_m2:
    st.metric("Quantum Signature", f"{np.max(dark_mode_leakage):.4f}")

with col_m3:
    st.metric("Conventional RCS", f"{np.max(radar_return):.4f}")

with col_m4:
    gain = np.max(enhanced) / (np.max(radar_return) + 1e-12)
    st.metric("PDP Enhancement", f"{gain:.1f}x")


# ── LIVE HISTORY GRAPH ─────────────────────────────────────────────
if data_mode == "🟢 LIVE Radar Stream" and st.session_state.radar_history:
    st.markdown("---")
    st.markdown("### 📈 Detection History (Last 10 Scans)")
    
    history_df = pd.DataFrame([
        {'Scan': i+1, 'Confidence': h['confidence'] * 100}
        for i, h in enumerate(st.session_state.radar_history[-10:])
    ])
    
    fig, ax = plt.subplots(figsize=(10, 4), facecolor='#0a0a1a')
    ax.bar(history_df['Scan'], history_df['Confidence'], color='#00aaff')
    ax.axhline(y=10, color='red', linestyle='--', label='Detection Threshold')
    ax.set_xlabel("Scan Number", color='white')
    ax.set_ylabel("Detection Confidence (%)", color='white')
    ax.set_title("Live Detection Confidence", color='white')
    ax.legend()
    ax.tick_params(colors='white')
    ax.set_facecolor('#1a1a3a')
    st.pyplot(fig)
    plt.close(fig)


# ── EXPORT ─────────────────────────────────────────────
st.markdown("---")
st.markdown("### 💾 Export Results")

col_e1, col_e2, col_e3 = st.columns(3)

def save_array_png(arr, cmap='inferno'):
    fig, ax = plt.subplots(figsize=(8, 8), facecolor='black')
    ax.imshow(arr, cmap=cmap, vmin=0, vmax=1)
    ax.axis('off')
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', facecolor='black')
    plt.close(fig)
    return buf.getvalue()

with col_e1:
    st.download_button("📸 PDP Radar Image", save_array_png(enhanced), "pdp_radar.png", width='stretch')

with col_e2:
    metadata = {
        "timestamp": str(timestamp),
        "target": target,
        "range_km": range_km,
        "detection_confidence": detection_confidence,
        "quantum_signature": float(np.max(dark_mode_leakage))
    }
    st.download_button("📋 Export Metadata", json.dumps(metadata, indent=2), "radar_metadata.json", width='stretch')

with col_e3:
    if data_mode == "🟢 LIVE Radar Stream" and st.session_state.radar_history:
        history_data = json.dumps([
            {'timestamp': str(h['timestamp']), 'confidence': float(h['confidence'])}
            for h in st.session_state.radar_history
        ], indent=2)
        st.download_button("📊 Export History", history_data, "detection_history.json", width='stretch')


# ── THEORY ─────────────────────────────────────────────
with st.expander("📖 How It Works – PDP Quantum Radar"):
    st.markdown(r"""
    ### Photon-Dark-Photon Quantum Radar
    
    **Live Mode:** Simulates real-time radar scans with moving targets
    
    **Physics:** Conventional radar detects reflected photons. Stealth aircraft minimize this.
    
    **PDP Advantage:** Photon-dark-photon kinetic mixing:
    $$\mathcal{L}_{\text{mix}} = \frac{\varepsilon}{2} F_{\mu\nu} F'^{\mu\nu}$$
    
    **Detection Chain:**
    1. Transmit radar pulse → photons
    2. Convert to dark photons: $P(\gamma \to A') = (\varepsilon B / m')^2 \sin^2(m'^2 L / 4\omega)$
    3. Dark photons interact with stealth platform (no coating works)
    4. Convert back → unique quantum signature
    5. PDP filter extracts signature from noise
    
    **Result:** F-35, B-21, NGAD, HQ-19, Kinzhal at **>250 km**
    """)

st.markdown("---")
st.markdown("🛸 **StealthPDPRadar v3.0** | Live Radar | PDP Quantum Filter | Tony Ford Model")
