"""
StealthPDPRadar v4.1 – Fixed Dropdowns & Enhanced Controls
Real-world location presets | Working menus | Stealth detection
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
    page_title="StealthPDPRadar v4.1",
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
    .location-card {
        background-color: #1a1a3a;
        padding: 10px;
        border-radius: 8px;
        margin: 5px 0;
        border-left: 3px solid #00aaff;
    }
</style>
""", unsafe_allow_html=True)


# ── REAL-WORLD LOCATION DATABASE ─────────────────────────────────────────────
# Defined as a simple list to ensure dropdown works
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
    
    # RCS based on target type
    rcs_factors = {
        "F-35 Lightning II": 0.001,
        "B-21 Raider": 0.0005,
        "NGAD": 0.0003,
        "HQ-19": 0.005,
        "Kinzhal": 0.01,
        "Su-57": 0.01,
        "J-20": 0.008,
        "Drone": 0.02
    }
    rcs = rcs_factors.get(target_type, 0.001)
    
    # Conventional radar return
    distance = np.sqrt((X - target_x)**2 + (Y - target_y)**2)
    conventional = rcs * np.exp(-distance**2 / (2 * (range_km/8)**2))
    
    # Quantum signature
    quantum_strength = 0.15 * (1 / rcs) ** 0.3
    quantum = quantum_strength * np.exp(-distance**2 / (2 * (range_km/4)**2))
    
    # Add noise
    noise = np.random.randn(size, size) * 0.05
    radar_data = conventional + quantum + noise
    radar_data = np.clip(radar_data, 0, 1)
    
    return radar_data


# ── SIDEBAR ─────────────────────────────────────────────
with st.sidebar:
    st.title("🛸 StealthPDPRadar v4.1")
    st.markdown("*Real-World Radar Detection*")
    st.markdown("---")
    
    # Location Preset - FIXED DROPDOWN
    st.markdown("### 🌍 Select Radar Station")
    
    # Simple selectbox with location names
    location_preset = st.selectbox(
        "Location",
        LOCATION_NAMES,
        index=0,
        key="location_selector"
    )
    
    # Get location info
    location_info = LOCATIONS[location_preset]
    
    # Display location card
    st.markdown(f"""
    <div class="location-card">
    📍 **{location_preset}**<br>
    📝 {location_info['description']}<br>
    🎯 Stealth Presence: {location_info['stealth_presence']}<br>
    📡 Max Range: {location_info['range_km']} km
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Data source selection
    st.markdown("### 📡 Data Source")
    data_mode = st.radio(
        "Mode",
        ["🌌 Synthetic Demo", "📁 Upload File"],
        index=0,
        key="data_mode"
    )
    
    st.markdown("---")
    
    # Target selection
    st.markdown("### 🎯 Target")
    target_options = ["F-35 Lightning II", "B-21 Raider", "NGAD", "HQ-19", "Kinzhal", "Su-57", "J-20", "Drone"]
    target = st.selectbox("Stealth Platform", target_options, index=0, key="target_selector")
    
    st.markdown("---")
    st.markdown("### ⚛️ PDP Parameters")
    epsilon = st.slider("Kinetic Mixing ε", 1e-12, 1e-8, 1e-10, format="%.1e", key="epsilon")
    B_field = st.slider("B Field (G)", 1e13, 1e16, 1e15, format="%.1e", key="B_field")
    m_dark = st.slider("Dark Photon Mass (eV)", 1e-12, 1e-6, 1e-9, format="%.1e", key="m_dark")
    
    st.markdown("---")
    st.markdown("### 📡 Radar Controls")
    
    # Use location's range as default
    range_km = st.slider("Range (km)", 50, 500, location_info['range_km'], key="range")
    threshold = st.slider("Detection Threshold", 0.01, 0.5, 0.1, key="threshold")
    
    st.markdown("---")
    st.caption("Tony Ford | StealthPDPRadar v4.1")
    st.caption("Real-world location presets | PDP quantum filter")


# ── MAIN APP ─────────────────────────────────────────────
st.title("🛸 StealthPDPRadar")
st.markdown(f"*Quantum Radar Simulation – {location_preset}*")
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

st.markdown("---")

# Target position controls
st.markdown("### 🎯 Target Position")
col_x, col_y = st.columns(2)
with col_x:
    target_x = st.slider("X Coordinate (km)", -range_km, range_km, int(range_km * 0.3), key="target_x")
with col_y:
    target_y = st.slider("Y Coordinate (km)", -range_km, range_km, int(range_km * 0.2), key="target_y")

# Generate radar data
with st.spinner(f"Processing radar data from {location_preset}..."):
    radar_return = generate_radar_data(location_preset, range_km, target_x, target_y, target)
    timestamp = datetime.now()

# Process with PDP filter
enhanced, dark_mode_leakage = pdp_radar_filter(radar_return, epsilon, B_field, m_dark)
targets = detect_targets(dark_mode_leakage, threshold)
detection_confidence = min(targets[0]['strength'] * 100, 99.9) if targets else 0
conventional_strength = np.max(radar_return)
quantum_signature = np.max(dark_mode_leakage)
enhancement_gain = np.max(enhanced) / (conventional_strength + 1e-12)


# ── DISPLAY RADAR VISUALIZATIONS ─────────────────────────────────────────────
st.markdown("### 📡 Radar Detection")

col1, col2, col3 = st.columns(3)

def safe_display_plot(fig):
    st.pyplot(fig)
    plt.close(fig)

# Conventional Radar
with col1:
    fig, ax = plt.subplots(figsize=(5, 5), facecolor='#0a0a1a')
    im = ax.imshow(radar_return, cmap='gray', extent=[-range_km, range_km, -range_km, range_km])
    plt.colorbar(im, ax=ax, label="Signal")
    ax.set_title(f"Conventional Radar\n{location_preset}", color='white', fontsize=10)
    ax.set_xlabel("Range (km)", color='white')
    ax.set_ylabel("Range (km)", color='white')
    ax.tick_params(colors='white')
    safe_display_plot(fig)
    st.caption("Stealth aircraft nearly invisible")

# Dark-Mode Leakage (PDP Filter)
with col2:
    fig, ax = plt.subplots(figsize=(5, 5), facecolor='#0a0a1a')
    im = ax.imshow(dark_mode_leakage, cmap='plasma', extent=[-range_km, range_km, -range_km, range_km])
    plt.colorbar(im, ax=ax, label="Quantum Signature")
    
    # Mark detected targets
    for t in targets[:3]:
        x_km = -range_km + (t['x'] / radar_return.shape[1]) * 2 * range_km
        y_km = -range_km + (t['y'] / radar_return.shape[0]) * 2 * range_km
        circle = Circle((x_km, y_km), range_km/15, fill=False, edgecolor='red', linewidth=2)
        ax.add_patch(circle)
    
    ax.set_title(f"Dark-Mode Leakage\nPDP Quantum Filter", color='white', fontsize=10)
    ax.set_xlabel("Range (km)", color='white')
    ax.set_ylabel("Range (km)", color='white')
    ax.tick_params(colors='white')
    safe_display_plot(fig)
    st.caption("✨ Quantum signature reveals stealth target")

# PDP Quantum Radar (RGB)
with col3:
    fig, ax = plt.subplots(figsize=(5, 5), facecolor='#0a0a1a')
    rgb = np.stack([radar_return, dark_mode_leakage, enhanced], axis=-1)
    ax.imshow(np.clip(rgb, 0, 1), extent=[-range_km, range_km, -range_km, range_km])
    ax.set_title(f"PDP Quantum Radar\n{location_preset}", color='white', fontsize=10)
    ax.set_xlabel("Range (km)", color='white')
    ax.set_ylabel("Range (km)", color='white')
    ax.tick_params(colors='white')
    safe_display_plot(fig)
    st.caption("🌈 Blue-halo fusion - target detected")

# Show target coordinates
st.caption(f"📍 **Target Position:** X = {target_x:.1f} km, Y = {target_y:.1f} km")


# ── DETECTION ANALYSIS ─────────────────────────────────────────────
st.markdown("---")
st.markdown("### 🎯 Detection Analysis")

col_m1, col_m2, col_m3, col_m4 = st.columns(4)

with col_m1:
    st.metric("Detection Confidence", f"{detection_confidence:.1f}%",
              delta="STEALTH BREACHED" if detection_confidence > 10 else "No Detection")

with col_m2:
    st.metric("Quantum Signature", f"{quantum_signature:.4f}")

with col_m3:
    st.metric("Conventional RCS", f"{conventional_strength:.4f}")

with col_m4:
    st.metric("PDP Enhancement", f"{enhancement_gain:.1f}x")

# Threat Assessment
if detection_confidence > 50:
    st.error(f"⚠️ **HIGH ALERT:** {target} detected at {range_km} km near {location_preset}!")
elif detection_confidence > 20:
    st.warning(f"⚠️ **MEDIUM ALERT:** Possible {target} signature detected near {location_preset}")
elif detection_confidence > 5:
    st.info(f"ℹ️ **LOW ALERT:** Weak quantum signature - investigate further")
else:
    st.success(f"✅ **CLEAR:** No stealth signatures detected near {location_preset}")


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
    st.download_button("📸 PDP Radar Image", save_array_png(enhanced), f"pdp_radar_{location_preset.replace(' ', '_').replace('(', '').replace(')', '')}.png", width='stretch')

with col_e2:
    metadata = {
        "timestamp": str(timestamp),
        "location": location_preset,
        "target": target,
        "range_km": range_km,
        "detection_confidence": detection_confidence,
        "quantum_signature": float(quantum_signature),
        "target_x": target_x,
        "target_y": target_y
    }
    st.download_button("📋 Export Metadata", json.dumps(metadata, indent=2), "radar_metadata.json", width='stretch')

with col_e3:
    # Export current radar data as CSV
    df_export = pd.DataFrame(radar_return)
    csv_data = df_export.to_csv(index=False).encode()
    st.download_button("📊 Export Radar Data", csv_data, f"radar_data_{location_preset.replace(' ', '_')}.csv", width='stretch')


# ── THEORY ─────────────────────────────────────────────
with st.expander("📖 How It Works – PDP Quantum Radar"):
    st.markdown(r"""
    ### Photon-Dark-Photon Quantum Radar
    
    **Real-World Locations:** Simulates radar coverage at major air bases and test sites worldwide
    
    **Detection Chain:**
    1. Radar pulse transmitted from location
    2. Photon-dark-photon mixing: $P(\gamma \to A') = (\varepsilon B / m')^2 \sin^2(m'^2 L / 4\omega)$
    3. Dark photons interact with stealth target
    4. Unique quantum signature returned
    5. PDP filter extracts signature
    
    **Result:** Detection of stealth platforms at >250 km range
    
    ### Available Locations
    - 🇺🇸 **Nellis AFB** – F-35 testing, Red Flag exercises
    - 🇺🇸 **Edwards AFB** – B-21 Raider development
    - 🇺🇸 **Area 51** – NGAD testing
    - 🇬🇧 **RAF Lakenheath** – US F-35A in Europe
    - 🇷🇺 **Akhtubinsk** – Russian Su-57 testing
    - 🇨🇳 **Dingxin** – Chinese J-20 operations
    - 🇮🇷 **Shahid Satari** – Missile/drone testing
    - 🇰🇵 **Sohae** – North Korean missile facility
    - 🇮🇱 **Palmachim** – Israeli F-35I operations
    - 🇦🇪 **Al Dhafra** – US F-35 deployment
    """)

st.markdown("---")
st.markdown("🛸 **StealthPDPRadar v4.1** | Real-World Location Presets | Tony Ford Model")
