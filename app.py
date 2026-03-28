"""
StealthPDPRadar v5.0 – Live Radar with Start/Stop Controls
Real-world location presets | Live streaming | Full export
"""

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import io
import json
import pandas as pd
import time
from datetime import datetime
import warnings
import threading

warnings.filterwarnings('ignore')

# ── PAGE CONFIG ─────────────────────────────────────────────
st.set_page_config(
    layout="wide",
    page_title="StealthPDPRadar v5.0",
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
    .location-card {
        background-color: #1a1a3a;
        padding: 10px;
        border-radius: 8px;
        margin: 5px 0;
        border-left: 3px solid #00aaff;
    }
    .live-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background-color: #ff4444;
        animation: pulse 1s infinite;
        margin-right: 8px;
    }
    @keyframes pulse {
        0% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.5; transform: scale(1.2); }
        100% { opacity: 1; transform: scale(1); }
    }
    .detection-high {
        background-color: #ff4444;
        color: white;
        padding: 10px;
        border-radius: 8px;
        text-align: center;
        font-weight: bold;
        margin: 10px 0;
    }
    .detection-medium {
        background-color: #ffaa44;
        color: black;
        padding: 10px;
        border-radius: 8px;
        text-align: center;
        font-weight: bold;
        margin: 10px 0;
    }
    .detection-low {
        background-color: #44ff44;
        color: black;
        padding: 10px;
        border-radius: 8px;
        text-align: center;
        font-weight: bold;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)


# ── REAL-WORLD LOCATION DATABASE ─────────────────────────────────────────────
LOCATION_NAMES = [
    "🇺🇸 Nellis AFB (NV, USA)",
    "🇺🇸 Edwards AFB (CA, USA)",
    "🇺🇸 Area 51 (Groom Lake, NV)",
    "🇬🇧 RAF Lakenheath (UK)",
    "🇷🇺 Akhtubinsk (Russia)",
    "🇨🇳 Dingxin Air Base (China)",
    "🇮🇷 Shahid Satari (Iran)",
    "🇰🇵 Sohae Satellite Station (North Korea)",
    "🇮🇱 Palmachim Airbase (Israel)",
    "🇦🇪 Al Dhafra AB (UAE)"
]

LOCATIONS = {
    "🇺🇸 Nellis AFB (NV, USA)": {
        "lat": 36.2358, "lon": -115.0341,
        "range_km": 300, "description": "Home of Red Flag exercises, F-35 testing",
        "stealth_presence": "High"
    },
    "🇺🇸 Edwards AFB (CA, USA)": {
        "lat": 34.9056, "lon": -117.8839,
        "range_km": 350, "description": "Air Force Test Center, B-21 testing",
        "stealth_presence": "Very High"
    },
    "🇺🇸 Area 51 (Groom Lake, NV)": {
        "lat": 37.2390, "lon": -115.8158,
        "range_km": 400, "description": "Classified test site, NGAD development",
        "stealth_presence": "Classified"
    },
    "🇬🇧 RAF Lakenheath (UK)": {
        "lat": 52.4092, "lon": 0.5565,
        "range_km": 250, "description": "US F-35A base in Europe",
        "stealth_presence": "High"
    },
    "🇷🇺 Akhtubinsk (Russia)": {
        "lat": 48.3000, "lon": 46.1667,
        "range_km": 350, "description": "Russian Su-57 testing center",
        "stealth_presence": "Medium"
    },
    "🇨🇳 Dingxin Air Base (China)": {
        "lat": 40.7833, "lon": 99.5333,
        "range_km": 400, "description": "PLAAF test range, J-20 operations",
        "stealth_presence": "High"
    },
    "🇮🇷 Shahid Satari (Iran)": {
        "lat": 35.2469, "lon": 52.0222,
        "range_km": 250, "description": "Iranian drone and missile test site",
        "stealth_presence": "Medium"
    },
    "🇰🇵 Sohae Satellite Station (North Korea)": {
        "lat": 39.2966, "lon": 124.7231,
        "range_km": 300, "description": "Missile test facility",
        "stealth_presence": "Low"
    },
    "🇮🇱 Palmachim Airbase (Israel)": {
        "lat": 31.9025, "lon": 34.6903,
        "range_km": 280, "description": "Israeli F-35I operations",
        "stealth_presence": "High"
    },
    "🇦🇪 Al Dhafra AB (UAE)": {
        "lat": 24.2481, "lon": 54.5475,
        "range_km": 320, "description": "US F-35 deployment",
        "stealth_presence": "Medium"
    }
}

RCS_FACTORS = {
    "F-35 Lightning II": 0.001,
    "B-21 Raider": 0.0005,
    "NGAD": 0.0003,
    "HQ-19": 0.005,
    "Kinzhal": 0.01,
    "Su-57": 0.01,
    "J-20": 0.008,
    "Drone": 0.02
}


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
    from scipy.ndimage import label
    
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


def generate_radar_data(location_name, range_km, target_x, target_y, target_type="F-35"):
    """Generate radar data for a specific location"""
    size = 200
    x = np.linspace(-range_km, range_km, size)
    y = np.linspace(-range_km, range_km, size)
    X, Y = np.meshgrid(x, y)
    
    rcs = RCS_FACTORS.get(target_type, 0.001)
    
    # Conventional radar return
    distance = np.sqrt((X - target_x)**2 + (Y - target_y)**2)
    conventional = rcs * np.exp(-distance**2 / (2 * (range_km/8)**2))
    
    # Quantum signature (stronger for stealthier targets)
    quantum_strength = 0.15 * (1 / (rcs + 1e-12)) ** 0.25
    quantum = quantum_strength * np.exp(-distance**2 / (2 * (range_km/4)**2))
    
    # Add realistic noise
    noise = np.random.randn(size, size) * 0.03
    radar_data = conventional + quantum + noise
    radar_data = np.clip(radar_data, 0, 1)
    
    return radar_data, target_x, target_y


class RadarSimulator:
    """Live radar simulator with start/stop controls"""
    
    def __init__(self):
        self.is_running = False
        self.scan_count = 0
        self.history = []
        self.current_data = None
    
    def start(self):
        self.is_running = True
    
    def stop(self):
        self.is_running = False
    
    def update(self, location, range_km, target_x, target_y, target_type, epsilon, B_field, m_dark):
        if not self.is_running:
            return None
        
        radar_return, tx, ty = generate_radar_data(location, range_km, target_x, target_y, target_type)
        enhanced, dark_mode = pdp_radar_filter(radar_return, epsilon, B_field, m_dark)
        targets = detect_targets(dark_mode, 0.1)
        confidence = min(targets[0]['strength'] * 100, 99.9) if targets else 0
        
        self.scan_count += 1
        self.current_data = {
            'scan': self.scan_count,
            'timestamp': datetime.now(),
            'radar_return': radar_return,
            'enhanced': enhanced,
            'dark_mode': dark_mode,
            'targets': targets,
            'confidence': confidence,
            'target_x': tx,
            'target_y': ty
        }
        
        self.history.append({
            'scan': self.scan_count,
            'timestamp': datetime.now(),
            'confidence': confidence,
            'target_x': tx,
            'target_y': ty
        })
        
        if len(self.history) > 50:
            self.history.pop(0)
        
        return self.current_data


# ── SIDEBAR ─────────────────────────────────────────────
with st.sidebar:
    st.title("🛸 StealthPDPRadar v5.0")
    st.markdown("*Live Radar with Start/Stop*")
    st.markdown("---")
    
    # Location Preset
    st.markdown("### 🌍 Select Radar Station")
    location_preset = st.selectbox("Location", LOCATION_NAMES, index=0)
    location_info = LOCATIONS[location_preset]
    
    st.markdown(f"""
    <div class="location-card">
    📍 **{location_preset}**<br>
    📝 {location_info['description']}<br>
    🎯 Stealth Presence: {location_info['stealth_presence']}<br>
    📡 Max Range: {location_info['range_km']} km
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Target selection
    st.markdown("### 🎯 Target")
    target = st.selectbox("Stealth Platform", list(RCS_FACTORS.keys()), index=0)
    
    st.markdown("---")
    st.markdown("### ⚛️ PDP Parameters")
    epsilon = st.slider("Kinetic Mixing ε", 1e-12, 1e-8, 1e-10, format="%.1e")
    B_field = st.slider("B Field (G)", 1e13, 1e16, 1e15, format="%.1e")
    m_dark = st.slider("Dark Photon Mass (eV)", 1e-12, 1e-6, 1e-9, format="%.1e")
    
    st.markdown("---")
    st.markdown("### 📡 Radar Controls")
    range_km = st.slider("Range (km)", 50, 500, location_info['range_km'])
    threshold = st.slider("Detection Threshold", 0.01, 0.5, 0.1)
    update_interval = st.slider("Update Interval (s)", 0.5, 5.0, 1.0)
    
    st.markdown("---")
    
    # START/STOP buttons
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("▶️ START RADAR", use_container_width=True):
            if 'radar_sim' not in st.session_state:
                st.session_state.radar_sim = RadarSimulator()
            st.session_state.radar_sim.start()
            st.session_state.radar_active = True
    with col_btn2:
        if st.button("⏹️ STOP RADAR", use_container_width=True):
            if 'radar_sim' in st.session_state:
                st.session_state.radar_sim.stop()
            st.session_state.radar_active = False
    
    st.markdown("---")
    
    # Target position (only visible when radar is stopped)
    if 'radar_active' not in st.session_state or not st.session_state.radar_active:
        st.markdown("### 🎯 Manual Target Position")
        target_x = st.slider("X (km)", -range_km, range_km, int(range_km * 0.3))
        target_y = st.slider("Y (km)", -range_km, range_km, int(range_km * 0.2))
    
    st.markdown("---")
    st.caption("Tony Ford | StealthPDPRadar v5.0")
    st.caption("Start/Stop | Live Radar | Full Export")


# ── MAIN APP ─────────────────────────────────────────────
st.title("🛸 StealthPDPRadar")
st.markdown(f"*Live Quantum Radar Simulation – {location_preset}*")
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

# Live indicator
if 'radar_active' in st.session_state and st.session_state.radar_active:
    st.markdown('<div><span class="live-indicator"></span> <strong>LIVE RADAR ACTIVE</strong> - Scanning in real-time</div>', unsafe_allow_html=True)
else:
    st.info("⏸️ **RADAR STOPPED** - Click 'START RADAR' to begin live scanning")

st.markdown("---")


# ── INITIALIZE SESSION STATE ─────────────────────────────────────────────
if 'radar_sim' not in st.session_state:
    st.session_state.radar_sim = RadarSimulator()
if 'radar_active' not in st.session_state:
    st.session_state.radar_active = False
if 'current_scan' not in st.session_state:
    st.session_state.current_scan = None
if 'last_update' not in st.session_state:
    st.session_state.last_update = time.time()


# ── UPDATE RADAR (if active) ─────────────────────────────────────────────
current_time = time.time()

if st.session_state.radar_active and (current_time - st.session_state.last_update >= update_interval):
    # Get current target position from session or use default
    if 'target_x' in locals():
        tx, ty = target_x, target_y
    else:
        tx, ty = range_km * 0.3, range_km * 0.2
    
    # Update radar
    scan_data = st.session_state.radar_sim.update(
        location_preset, range_km, tx, ty, target, epsilon, B_field, m_dark
    )
    
    if scan_data:
        st.session_state.current_scan = scan_data
        st.session_state.last_update = current_time
    
    # Auto-rerun for next frame
    st.rerun()

# Get current scan data
if st.session_state.current_scan:
    scan = st.session_state.current_scan
    radar_return = scan['radar_return']
    enhanced = scan['enhanced']
    dark_mode_leakage = scan['dark_mode']
    targets = scan['targets']
    detection_confidence = scan['confidence']
    current_target_pos = (scan['target_x'], scan['target_y'])
    scan_number = scan['scan']
    
    conventional_strength = np.max(radar_return)
    quantum_signature = np.max(dark_mode_leakage)
    enhancement_gain = np.max(enhanced) / (conventional_strength + 1e-12)
else:
    # Generate initial static data
    if 'target_x' in locals():
        tx, ty = target_x, target_y
    else:
        tx, ty = range_km * 0.3, range_km * 0.2
    
    radar_return, _, _ = generate_radar_data(location_preset, range_km, tx, ty, target)
    enhanced, dark_mode_leakage = pdp_radar_filter(radar_return, epsilon, B_field, m_dark)
    targets = detect_targets(dark_mode_leakage, threshold)
    detection_confidence = min(targets[0]['strength'] * 100, 99.9) if targets else 0
    conventional_strength = np.max(radar_return)
    quantum_signature = np.max(dark_mode_leakage)
    enhancement_gain = np.max(enhanced) / (conventional_strength + 1e-12)
    current_target_pos = (tx, ty)
    scan_number = 0


# ── DISPLAY RADAR VISUALIZATIONS ─────────────────────────────────────────────
st.markdown("### 📡 Radar Detection")

def safe_display_plot(fig):
    st.pyplot(fig)
    plt.close(fig)

col1, col2, col3 = st.columns(3)

# Conventional Radar
with col1:
    fig, ax = plt.subplots(figsize=(5, 5), facecolor='#0a0a1a')
    im = ax.imshow(radar_return, cmap='gray', extent=[-range_km, range_km, -range_km, range_km])
    plt.colorbar(im, ax=ax, label="Signal")
    ax.set_title(f"Conventional Radar\nScan #{scan_number}", color='white')
    ax.set_xlabel("Range East-West (km)", color='white')
    ax.set_ylabel("Range North-South (km)", color='white')
    ax.tick_params(colors='white')
    safe_display_plot(fig)
    st.caption("⚪ Conventional radar sees almost nothing")

# Dark-Mode Leakage
with col2:
    fig, ax = plt.subplots(figsize=(5, 5), facecolor='#0a0a1a')
    im = ax.imshow(dark_mode_leakage, cmap='plasma', extent=[-range_km, range_km, -range_km, range_km])
    plt.colorbar(im, ax=ax, label="Quantum Signature")
    
    for t in targets[:3]:
        x_km = -range_km + (t['x'] / radar_return.shape[1]) * 2 * range_km
        y_km = -range_km + (t['y'] / radar_return.shape[0]) * 2 * range_km
        circle = Circle((x_km, y_km), range_km/12, fill=False, edgecolor='red', linewidth=2)
        ax.add_patch(circle)
    
    ax.set_title(f"Dark-Mode Leakage\nPDP Filter", color='white')
    ax.set_xlabel("Range East-West (km)", color='white')
    ax.set_ylabel("Range North-South (km)", color='white')
    ax.tick_params(colors='white')
    safe_display_plot(fig)
    st.caption("✨ PDP filter reveals stealth target via quantum signature")

# PDP Quantum Radar
with col3:
    fig, ax = plt.subplots(figsize=(5, 5), facecolor='#0a0a1a')
    rgb = np.stack([radar_return, dark_mode_leakage, enhanced], axis=-1)
    ax.imshow(np.clip(rgb, 0, 1), extent=[-range_km, range_km, -range_km, range_km])
    ax.set_title(f"PDP Quantum Radar\nScan #{scan_number}", color='white')
    ax.set_xlabel("Range East-West (km)", color='white')
    ax.set_ylabel("Range North-South (km)", color='white')
    ax.tick_params(colors='white')
    safe_display_plot(fig)
    st.caption("🌈 Blue-halo fusion - target clearly visible")

# Show target coordinates and scan info
st.caption(f"📍 **Target Position:** X = {current_target_pos[0]:.1f} km, Y = {current_target_pos[1]:.1f} km")
st.caption(f"📡 **Scan #{scan_number}** | Last update: {datetime.now().strftime('%H:%M:%S')}")


# ── DETECTION ANALYSIS ─────────────────────────────────────────────
st.markdown("---")
st.markdown("### 🎯 Detection Analysis")

col_m1, col_m2, col_m3, col_m4 = st.columns(4)

with col_m1:
    st.metric("Detection Confidence", f"{detection_confidence:.1f}%")

with col_m2:
    st.metric("Quantum Signature", f"{quantum_signature:.4f}")

with col_m3:
    st.metric("Conventional RCS", f"{conventional_strength:.4f}")

with col_m4:
    st.metric("PDP Enhancement", f"{enhancement_gain:.1f}x")

# Threat Assessment
if detection_confidence > 50:
    st.markdown(f'<div class="detection-high">⚠️ HIGH ALERT: {target} detected at {range_km} km near {location_preset}!</div>', unsafe_allow_html=True)
elif detection_confidence > 20:
    st.markdown(f'<div class="detection-medium">⚠️ MEDIUM ALERT: Possible {target} signature detected near {location_preset}</div>', unsafe_allow_html=True)
elif detection_confidence > 5:
    st.markdown(f'<div class="detection-low">ℹ️ LOW ALERT: Weak quantum signature - investigate further</div>', unsafe_allow_html=True)
else:
    st.markdown(f'<div class="detection-low">✅ CLEAR: No stealth signatures detected near {location_preset}</div>', unsafe_allow_html=True)


# ── DETECTION HISTORY GRAPH ─────────────────────────────────────────────
if st.session_state.radar_sim.history:
    st.markdown("---")
    st.markdown("### 📈 Detection History")
    
    history_df = pd.DataFrame(st.session_state.radar_sim.history[-20:])
    
    fig, ax = plt.subplots(figsize=(10, 4), facecolor='#0a0a1a')
    ax.bar(history_df['scan'], history_df['confidence'] * 100, color='#00aaff')
    ax.axhline(y=10, color='red', linestyle='--', label='Detection Threshold')
    ax.set_xlabel("Scan Number", color='white')
    ax.set_ylabel("Detection Confidence (%)", color='white')
    ax.set_title(f"Live Detection History - {location_preset}", color='white')
    ax.legend()
    ax.tick_params(colors='white')
    ax.set_facecolor('#1a1a3a')
    st.pyplot(fig)
    plt.close(fig)


# ── EXPORT RESULTS ─────────────────────────────────────────────
st.markdown("---")
st.markdown("### 💾 Export Results")

col_e1, col_e2, col_e3, col_e4 = st.columns(4)

def save_array_png(arr, cmap='inferno'):
    fig, ax = plt.subplots(figsize=(8, 8), facecolor='black')
    ax.imshow(arr, cmap=cmap, vmin=0, vmax=1)
    ax.axis('off')
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', facecolor='black')
    plt.close(fig)
    return buf.getvalue()

with col_e1:
    st.download_button("📸 Current Radar Image", save_array_png(enhanced), f"pdp_radar_scan{scan_number}.png", width='stretch')

with col_e2:
    metadata = {
        "timestamp": str(datetime.now()),
        "location": location_preset,
        "target": target,
        "range_km": range_km,
        "detection_confidence": detection_confidence,
        "scan_number": scan_number,
        "target_x": current_target_pos[0],
        "target_y": current_target_pos[1]
    }
    st.download_button("📋 Export Metadata", json.dumps(metadata, indent=2), "radar_metadata.json", width='stretch')

with col_e3:
    df_export = pd.DataFrame(radar_return)
    csv_data = df_export.to_csv(index=False).encode()
    st.download_button("📊 Export Radar Data", csv_data, f"radar_data_scan{scan_number}.csv", width='stretch')

with col_e4:
    if st.session_state.radar_sim.history:
        history_json = json.dumps(st.session_state.radar_sim.history[-50:], indent=2, default=str)
        st.download_button("📈 Export History", history_json, "detection_history.json", width='stretch')


# ── THEORY ─────────────────────────────────────────────
with st.expander("📖 How It Works – PDP Quantum Radar"):
    st.markdown(r"""
    ### Photon-Dark-Photon Quantum Radar
    
    **Live Mode:** Click **START RADAR** to begin real-time scanning
    
    **Controls:**
    - **START RADAR** – Begins live scanning with automatic updates
    - **STOP RADAR** – Pauses scanning (adjust target position when stopped)
    - **Update Interval** – Controls scan rate (0.5-5 seconds)
    
    **Physics:**
    - Conventional radar: $P_{\text{conv}} \propto \text{RCS} \cdot e^{-(r/r_0)^2}$
    - PDP quantum filter: $P(\gamma \to A') = (\varepsilon B / m')^2 \sin^2(m'^2 L / 4\omega)$
    
    **Detection Chain:**
    1. Radar pulse transmitted
    2. Photon-dark-photon mixing creates quantum signature
    3. Dark photons interact with stealth target
    4. Unique quantum signature returns
    5. PDP filter extracts signature from noise
    
    **Result:** Detection of stealth platforms at >250 km range
    """)

st.markdown("---")
st.markdown("🛸 **StealthPDPRadar v5.0** | Start/Stop | Live Radar | Full Export | Tony Ford Model")
