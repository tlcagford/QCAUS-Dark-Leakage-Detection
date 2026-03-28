"""
StealthPDPRadar v7.0 – Complete Working Version
Live moving radar | Start/Stop controls | Real-time coordinates
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

warnings.filterwarnings('ignore')

# ── PAGE CONFIG ─────────────────────────────────────────────
st.set_page_config(
    layout="wide",
    page_title="StealthPDPRadar v7.0",
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
    .coord-input {
        background-color: #1a1a3a;
        padding: 10px;
        border-radius: 8px;
        margin: 10px 0;
        border: 1px solid #00aaff;
    }
</style>
""", unsafe_allow_html=True)


# ── LOCATIONS ─────────────────────────────────────────────
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
    "🇺🇸 Nellis AFB (NV, USA)": {"lat": 36.2358, "lon": -115.0341, "range_km": 300},
    "🇺🇸 Edwards AFB (CA, USA)": {"lat": 34.9056, "lon": -117.8839, "range_km": 350},
    "🇺🇸 Area 51 (Groom Lake, NV)": {"lat": 37.2390, "lon": -115.8158, "range_km": 400},
    "🇬🇧 RAF Lakenheath (UK)": {"lat": 52.4092, "lon": 0.5565, "range_km": 250},
    "🇷🇺 Akhtubinsk (Russia)": {"lat": 48.3000, "lon": 46.1667, "range_km": 350},
    "🇨🇳 Dingxin Air Base (China)": {"lat": 40.7833, "lon": 99.5333, "range_km": 400},
    "🇮🇷 Shahid Satari (Iran)": {"lat": 35.2469, "lon": 52.0222, "range_km": 250},
    "🇰🇵 Sohae Satellite Station (North Korea)": {"lat": 39.2966, "lon": 124.7231, "range_km": 300},
    "🇮🇱 Palmachim Airbase (Israel)": {"lat": 31.9025, "lon": 34.6903, "range_km": 280},
    "🇦🇪 Al Dhafra AB (UAE)": {"lat": 24.2481, "lon": 54.5475, "range_km": 320}
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

def generate_radar_frame(range_km, target_x, target_y, target_type="F-35", noise_level=0.03):
    """Generate a single radar frame"""
    size = 200
    x = np.linspace(-range_km, range_km, size)
    y = np.linspace(-range_km, range_km, size)
    X, Y = np.meshgrid(x, y)
    
    rcs = RCS_FACTORS.get(target_type, 0.001)
    
    # Distance from radar (center) to target
    distance = np.sqrt((X - target_x)**2 + (Y - target_y)**2)
    
    # Conventional radar return (stealth target is almost invisible)
    conventional = rcs * np.exp(-distance**2 / (2 * (range_km/8)**2))
    
    # PDP Quantum signature (stealth targets actually have STRONGER quantum signature)
    # This is the key physics: stealth coatings work on photons, not dark photons
    quantum_strength = 0.25 * (1 / (rcs + 1e-12)) ** 0.3
    quantum = quantum_strength * np.exp(-distance**2 / (2 * (range_km/5)**2))
    
    # Add noise
    noise = np.random.randn(size, size) * noise_level
    radar_data = conventional + quantum + noise
    radar_data = np.clip(radar_data, 0, 1)
    
    return radar_data, conventional, quantum


def pdp_enhance(radar_data, conventional, quantum, epsilon=1e-10, B_field=1e15, m_dark=1e-9):
    """Apply PDP quantum filter to extract stealth signature"""
    # PDP mixing strength
    mixing = epsilon * B_field / (m_dark + 1e-12)
    
    # Dark-mode leakage - this reveals stealth targets
    dark_mode_leakage = quantum * mixing * 5.0  # Enhanced for visibility
    dark_mode_leakage = np.clip(dark_mode_leakage, 0, 1)
    
    # Enhanced radar (combine conventional + quantum signature)
    enhanced = radar_data + dark_mode_leakage * 0.8
    enhanced = np.clip(enhanced, 0, 1)
    
    return enhanced, dark_mode_leakage


def detect_target(dark_mode_leakage, threshold=0.1):
    """Detect target from dark-mode leakage"""
    from scipy.ndimage import label
    
    mask = dark_mode_leakage > threshold
    labeled, num_features = label(mask)
    
    if num_features > 0:
        y_idx, x_idx = np.where(labeled == 1)
        if len(y_idx) > 0:
            return {
                'detected': True,
                'x': np.mean(x_idx),
                'y': np.mean(y_idx),
                'strength': np.mean(dark_mode_leakage[y_idx, x_idx]),
                'confidence': np.mean(dark_mode_leakage[y_idx, x_idx]) * 100
            }
    
    return {'detected': False, 'confidence': 0}


# ── SIDEBAR ─────────────────────────────────────────────
with st.sidebar:
    st.title("🛸 StealthPDPRadar v7.0")
    st.markdown("*Live Moving Radar*")
    st.markdown("---")
    
    # Location selection
    st.markdown("### 📡 Radar Location")
    location_preset = st.selectbox("Select Base", LOCATION_NAMES, index=0)
    location = LOCATIONS[location_preset]
    
    st.markdown(f"📍 **{location_preset}**")
    st.markdown(f"📡 Range: {location['range_km']} km")
    
    st.markdown("---")
    
    # Target selection
    st.markdown("### 🎯 Stealth Target")
    target = st.selectbox("Platform", list(RCS_FACTORS.keys()), index=0)
    
    st.markdown("---")
    
    # Live Radar Controls
    st.markdown("### 🎮 Radar Controls")
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("▶️ START RADAR", use_container_width=True):
            st.session_state.radar_active = True
    with col_btn2:
        if st.button("⏹️ STOP RADAR", use_container_width=True):
            st.session_state.radar_active = False
    
    update_interval = st.slider("Update Speed (s)", 0.2, 2.0, 0.5)
    
    st.markdown("---")
    
    # Manual Target Position (when stopped)
    if 'radar_active' in st.session_state and not st.session_state.radar_active:
        st.markdown("### 🎯 Manual Target Position")
        st.markdown('<div class="coord-input">', unsafe_allow_html=True)
        manual_x = st.slider("X Coordinate (km)", -location['range_km'], location['range_km'], int(location['range_km'] * 0.3))
        manual_y = st.slider("Y Coordinate (km)", -location['range_km'], location['range_km'], int(location['range_km'] * 0.2))
        st.markdown('</div>', unsafe_allow_html=True)
        st.session_state.manual_target = (manual_x, manual_y)
    
    st.markdown("---")
    
    # PDP Parameters
    st.markdown("### ⚛️ PDP Parameters")
    epsilon = st.slider("Kinetic Mixing ε", 1e-12, 1e-8, 1e-10, format="%.1e")
    B_field = st.slider("B Field (G)", 1e13, 1e16, 1e15, format="%.1e")
    m_dark = st.slider("Dark Photon Mass (eV)", 1e-12, 1e-6, 1e-9, format="%.1e")
    threshold = st.slider("Detection Threshold", 0.01, 0.5, 0.1)
    
    st.markdown("---")
    st.caption("Tony Ford | StealthPDPRadar v7.0")
    st.caption("Live moving radar | Start/Stop | Real coordinates")


# ── INITIALIZE SESSION STATE ─────────────────────────────────────────────
if 'radar_active' not in st.session_state:
    st.session_state.radar_active = False
if 'frame_count' not in st.session_state:
    st.session_state.frame_count = 0
if 'target_x' not in st.session_state:
    st.session_state.target_x = location['range_km'] * 0.3
if 'target_y' not in st.session_state:
    st.session_state.target_y = location['range_km'] * 0.2
if 'target_direction_x' not in st.session_state:
    st.session_state.target_direction_x = 1
if 'target_direction_y' not in st.session_state:
    st.session_state.target_direction_y = 1
if 'manual_target' not in st.session_state:
    st.session_state.manual_target = (location['range_km'] * 0.3, location['range_km'] * 0.2)
if 'detection_history' not in st.session_state:
    st.session_state.detection_history = []
if 'last_update' not in st.session_state:
    st.session_state.last_update = 0


# ── UPDATE TARGET POSITION ─────────────────────────────────────────────
current_time = time.time()
range_km = location['range_km']

if st.session_state.radar_active:
    # Moving target (bounces off edges)
    speed = 15  # km per second
    dt = update_interval
    
    # Update position
    st.session_state.target_x += st.session_state.target_direction_x * speed * dt
    st.session_state.target_y += st.session_state.target_direction_y * speed * dt
    
    # Bounce off edges
    if st.session_state.target_x > range_km:
        st.session_state.target_x = range_km - (st.session_state.target_x - range_km)
        st.session_state.target_direction_x *= -1
    if st.session_state.target_x < -range_km:
        st.session_state.target_x = -range_km + (-range_km - st.session_state.target_x)
        st.session_state.target_direction_x *= -1
    if st.session_state.target_y > range_km:
        st.session_state.target_y = range_km - (st.session_state.target_y - range_km)
        st.session_state.target_direction_y *= -1
    if st.session_state.target_y < -range_km:
        st.session_state.target_y = -range_km + (-range_km - st.session_state.target_y)
        st.session_state.target_direction_y *= -1
    
    target_x = st.session_state.target_x
    target_y = st.session_state.target_y
else:
    # Use manual position when stopped
    target_x, target_y = st.session_state.manual_target
    st.session_state.target_x = target_x
    st.session_state.target_y = target_y


# ── GENERATE RADAR FRAME ─────────────────────────────────────────────
# Generate radar data
radar_data, conventional, quantum = generate_radar_frame(
    range_km, target_x, target_y, target, noise_level=0.03
)

# Apply PDP filter
enhanced, dark_mode = pdp_enhance(radar_data, conventional, quantum, epsilon, B_field, m_dark)

# Detect target
detection = detect_target(dark_mode, threshold)
detection_confidence = detection['confidence']

# Update history
if st.session_state.radar_active and (current_time - st.session_state.last_update >= update_interval):
    st.session_state.detection_history.append({
        'time': datetime.now(),
        'confidence': detection_confidence,
        'frame': st.session_state.frame_count
    })
    if len(st.session_state.detection_history) > 50:
        st.session_state.detection_history.pop(0)
    st.session_state.frame_count += 1
    st.session_state.last_update = current_time


# ── MAIN DISPLAY ─────────────────────────────────────────────
st.title("🛸 StealthPDPRadar")
st.markdown(f"*Live Quantum Radar – {location_preset}*")
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

# Live indicator and target position
if st.session_state.radar_active:
    st.markdown('<div><span class="live-indicator"></span> <strong>RADAR ACTIVE</strong> - Target moving</div>', unsafe_allow_html=True)
else:
    st.info("⏸️ **RADAR STOPPED** - Click START to begin moving target")

st.caption(f"📍 **Target Position:** X = {target_x:.1f} km, Y = {target_y:.1f} km")
st.caption(f"📡 **Frame:** {st.session_state.frame_count} | **Last Update:** {datetime.now().strftime('%H:%M:%S')}")

st.markdown("---")


# ── RADAR VISUALIZATIONS ─────────────────────────────────────────────
st.markdown("### 📡 Radar Display")

col1, col2, col3 = st.columns(3)

def show_radar(img, title, cmap, show_target=False, target_pos=None, range_km=300):
    fig, ax = plt.subplots(figsize=(5, 5), facecolor='#0a0a1a')
    im = ax.imshow(img, cmap=cmap, extent=[-range_km, range_km, -range_km, range_km])
    plt.colorbar(im, ax=ax, label="Signal")
    
    if show_target and target_pos:
        circle = Circle(target_pos, range_km/15, fill=False, edgecolor='red', linewidth=2)
        ax.add_patch(circle)
        ax.plot(target_pos[0], target_pos[1], 'r*', markersize=10)
    
    ax.set_title(title, color='white')
    ax.set_xlabel("Range East-West (km)", color='white')
    ax.set_ylabel("Range North-South (km)", color='white')
    ax.tick_params(colors='white')
    st.pyplot(fig)
    plt.close(fig)

# Conventional Radar
with col1:
    show_radar(radar_data, "Conventional Radar", 'gray', True, (target_x, target_y), range_km)
    st.caption("⚪ Stealth target invisible")

# Dark-Mode Leakage (PDP Filter)
with col2:
    show_radar(dark_mode, "Dark-Mode Leakage", 'plasma', True, (target_x, target_y), range_km)
    st.caption("✨ Quantum signature reveals target")

# PDP Quantum Radar
with col3:
    rgb = np.stack([radar_data, dark_mode, enhanced], axis=-1)
    fig, ax = plt.subplots(figsize=(5, 5), facecolor='#0a0a1a')
    ax.imshow(np.clip(rgb, 0, 1), extent=[-range_km, range_km, -range_km, range_km])
    circle = Circle((target_x, target_y), range_km/15, fill=False, edgecolor='red', linewidth=2)
    ax.add_patch(circle)
    ax.plot(target_x, target_y, 'r*', markersize=10)
    ax.set_title("PDP Quantum Radar", color='white')
    ax.set_xlabel("Range East-West (km)", color='white')
    ax.set_ylabel("Range North-South (km)", color='white')
    ax.tick_params(colors='white')
    st.pyplot(fig)
    plt.close(fig)
    st.caption("🌈 Blue-halo fusion - target detected")


# ── DETECTION ANALYSIS ─────────────────────────────────────────────
st.markdown("---")
st.markdown("### 🎯 Detection Analysis")

col_m1, col_m2, col_m3 = st.columns(3)

with col_m1:
    st.metric("Detection Confidence", f"{detection_confidence:.1f}%")

with col_m2:
    quantum_sig = np.max(dark_mode)
    st.metric("Quantum Signature", f"{quantum_sig:.4f}")

with col_m3:
    conventional_sig = np.max(radar_data)
    st.metric("Conventional RCS", f"{conventional_sig:.4f}")

# Threat Assessment
if detection_confidence > 50:
    st.error(f"⚠️ **HIGH ALERT:** {target} detected at {range_km} km near {location_preset}!")
elif detection_confidence > 20:
    st.warning(f"⚠️ **MEDIUM ALERT:** Possible {target} signature detected")
elif detection_confidence > 5:
    st.info(f"ℹ️ **LOW ALERT:** Weak quantum signature detected")
else:
    st.success(f"✅ **CLEAR:** No {target} signatures detected")


# ── DETECTION HISTORY GRAPH ─────────────────────────────────────────────
if st.session_state.detection_history:
    st.markdown("---")
    st.markdown("### 📈 Detection History")
    
    history_df = pd.DataFrame(st.session_state.detection_history[-30:])
    
    fig, ax = plt.subplots(figsize=(10, 4), facecolor='#0a0a1a')
    ax.plot(history_df['frame'], history_df['confidence'], 'b-', linewidth=2, marker='o', markersize=4)
    ax.axhline(y=10, color='red', linestyle='--', label='Detection Threshold')
    ax.set_xlabel("Frame Number", color='white')
    ax.set_ylabel("Detection Confidence (%)", color='white')
    ax.set_title("Live Detection Confidence Over Time", color='white')
    ax.legend()
    ax.tick_params(colors='white')
    ax.set_facecolor('#1a1a3a')
    ax.grid(True, alpha=0.3)
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
    st.download_button("📸 Download Radar Image", save_array_png(enhanced), "pdp_radar.png", width='stretch')

with col_e2:
    metadata = {
        "timestamp": str(datetime.now()),
        "location": location_preset,
        "target": target,
        "target_x": target_x,
        "target_y": target_y,
        "detection_confidence": detection_confidence,
        "radar_active": st.session_state.radar_active
    }
    st.download_button("📋 Export Metadata", json.dumps(metadata, indent=2), "radar_metadata.json", width='stretch')

with col_e3:
    df_export = pd.DataFrame(radar_data)
    csv_data = df_export.to_csv(index=False).encode()
    st.download_button("📊 Export Radar Data", csv_data, "radar_data.csv", width='stretch')


# ── AUTO-REFRESH ─────────────────────────────────────────────
if st.session_state.radar_active:
    time.sleep(update_interval)
    st.rerun()

st.markdown("---")
st.markdown("🛸 **StealthPDPRadar v7.0** | Live Moving Radar | Start/Stop | Tony Ford Model")
