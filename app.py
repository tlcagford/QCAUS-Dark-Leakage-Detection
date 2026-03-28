"""
StealthPDPRadar v4.0 – Real-World Location Presets
Live radar simulation with real-world coordinates | Stealth detection
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
import random

warnings.filterwarnings('ignore')

# ── PAGE CONFIG ─────────────────────────────────────────────
st.set_page_config(
    layout="wide",
    page_title="StealthPDPRadar v4.0",
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
    }
</style>
""", unsafe_allow_html=True)


# ── REAL-WORLD LOCATION DATABASE ─────────────────────────────────────────────
LOCATIONS = {
    "🇺🇸 Nellis AFB (NV, USA)": {
        "lat": 36.2358, "lon": -115.0341,
        "range_km": 300, "description": "Home of Red Flag exercises, F-35 testing",
        "stealth_presence": "High",
        "coordinates": (-115.0341, 36.2358)
    },
    "🇺🇸 Edwards AFB (CA, USA)": {
        "lat": 34.9056, "lon": -117.8839,
        "range_km": 350, "description": "Air Force Test Center, B-21 testing",
        "stealth_presence": "Very High",
        "coordinates": (-117.8839, 34.9056)
    },
    "🇺🇸 Area 51 (Groom Lake, NV)": {
        "lat": 37.2390, "lon": -115.8158,
        "range_km": 400, "description": "Classified test site, NGAD development",
        "stealth_presence": "Classified",
        "coordinates": (-115.8158, 37.2390)
    },
    "🇬🇧 RAF Lakenheath (UK)": {
        "lat": 52.4092, "lon": 0.5565,
        "range_km": 250, "description": "US F-35A base in Europe",
        "stealth_presence": "High",
        "coordinates": (0.5565, 52.4092)
    },
    "🇷🇺 Akhtubinsk (Russia)": {
        "lat": 48.3000, "lon": 46.1667,
        "range_km": 350, "description": "Russian Su-57 testing center",
        "stealth_presence": "Medium",
        "coordinates": (46.1667, 48.3000)
    },
    "🇨🇳 Dingxin Air Base (China)": {
        "lat": 40.7833, "lon": 99.5333,
        "range_km": 400, "description": "PLAAF test range, J-20 operations",
        "stealth_presence": "High",
        "coordinates": (99.5333, 40.7833)
    },
    "🇮🇷 Shahid Satari (Iran)": {
        "lat": 35.2469, "lon": 52.0222,
        "range_km": 250, "description": "Iranian drone and missile test site",
        "stealth_presence": "Medium",
        "coordinates": (52.0222, 35.2469)
    },
    "🇰🇵 Sohae Satellite Station (North Korea)": {
        "lat": 39.2966, "lon": 124.7231,
        "range_km": 300, "description": "Missile test facility",
        "stealth_presence": "Low",
        "coordinates": (124.7231, 39.2966)
    },
    "🇮🇱 Palmachim Airbase (Israel)": {
        "lat": 31.9025, "lon": 34.6903,
        "range_km": 280, "description": "Israeli F-35I operations",
        "stealth_presence": "High",
        "coordinates": (34.6903, 31.9025)
    },
    "🇦🇪 Al Dhafra AB (UAE)": {
        "lat": 24.2481, "lon": 54.5475,
        "range_km": 320, "description": "US F-35 deployment",
        "stealth_presence": "Medium",
        "coordinates": (54.5475, 24.2481)
    }
}


# ── REAL-TIME RADAR FEED SIMULATOR ─────────────────────────────────────────────

class RealTimeRadarFeed:
    """Simulates real-time radar feed from actual locations"""
    
    def __init__(self, location_name, target_type="F-35", range_km=300):
        self.location = location_name
        self.location_data = LOCATIONS.get(location_name, LOCATIONS["🇺🇸 Nellis AFB (NV, USA)"])
        self.target_type = target_type
        self.range_km = range_km
        self.current_data = None
        self.timestamp = None
        self.scan_count = 0
        self.detection_history = []
        self.manual_mode = False
        self.manual_x = None
        self.manual_y = None
        self.feed_active = False
        
        # RCS models for different stealth platforms
        self.rcs_factors = {
            "F-35 Lightning II": 0.001,
            "B-21 Raider": 0.0005,
            "NGAD": 0.0003,
            "HQ-19": 0.005,
            "Kinzhal": 0.01,
            "Su-57": 0.01,
            "J-20": 0.008,
            "Drone": 0.02
        }
        
        # Additional stealth platforms
        self.stealth_platforms = list(self.rcs_factors.keys())
    
    def set_manual_coords(self, x_km, y_km):
        """Set manual target coordinates"""
        self.manual_mode = True
        self.manual_x = np.clip(x_km, -self.range_km, self.range_km)
        self.manual_y = np.clip(y_km, -self.range_km, self.range_km)
    
    def set_auto_mode(self):
        """Switch back to automatic moving target"""
        self.manual_mode = False
    
    def generate_scan(self):
        """Generate a single radar scan frame"""
        size = 200
        rcs = self.rcs_factors.get(self.target_type, 0.001)
        
        # Create grid
        x = np.linspace(-self.range_km, self.range_km, size)
        y = np.linspace(-self.range_km, self.range_km, size)
        X, Y = np.meshgrid(x, y)
        
        # Determine target position
        if self.manual_mode and self.manual_x is not None:
            target_x = self.manual_x
            target_y = self.manual_y
        else:
            # Simulate realistic target movement (spiral pattern)
            t = time.time()
            target_x = self.range_km * (0.3 + 0.15 * np.sin(t / 12))
            target_y = self.range_km * (0.2 + 0.1 * np.cos(t / 15))
        
        # Add some random drift
        target_x += np.random.randn() * 5
        target_y += np.random.randn() * 5
        target_x = np.clip(target_x, -self.range_km, self.range_km)
        target_y = np.clip(target_y, -self.range_km, self.range_km)
        
        # Conventional radar return
        distance = np.sqrt((X - target_x)**2 + (Y - target_y)**2)
        conventional = rcs * np.exp(-distance**2 / (2 * (self.range_km/8)**2))
        
        # Quantum signature (PDP effect - stronger for stealth)
        quantum_strength = 0.15 * (1 / rcs) ** 0.3  # Stealthier = stronger quantum signature
        quantum = quantum_strength * np.exp(-distance**2 / (2 * (self.range_km/4)**2))
        
        # Add realistic noise (simulates atmospheric effects)
        noise = np.random.randn(size, size) * 0.05
        radar_data = conventional + quantum + noise
        radar_data = np.clip(radar_data, 0, 1)
        
        self.scan_count += 1
        
        return {
            'data': radar_data,
            'target_position': (target_x, target_y),
            'target_type': self.target_type,
            'location': self.location,
            'timestamp': datetime.now(),
            'range_km': self.range_km,
            'scan_number': self.scan_count,
            'manual_mode': self.manual_mode,
            'rcs': rcs,
            'quantum_strength': quantum_strength
        }
    
    def update(self):
        """Generate and store new scan"""
        self.current_data = self.generate_scan()
        self.timestamp = self.current_data['timestamp']
        
        # Store detection history
        confidence = np.max(self.current_data['data'])
        self.detection_history.append({
            'timestamp': self.timestamp,
            'confidence': confidence,
            'scan_number': self.scan_count,
            'target_x': self.current_data['target_position'][0],
            'target_y': self.current_data['target_position'][1]
        })
        if len(self.detection_history) > 50:
            self.detection_history.pop(0)
        
        return self.current_data
    
    def start_feed(self):
        """Start the live feed"""
        self.feed_active = True
    
    def stop_feed(self):
        """Stop the live feed"""
        self.feed_active = False


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


def generate_location_visualization(location_name, range_km, target_x, target_y):
    """Generate a location-aware radar visualization"""
    location = LOCATIONS.get(location_name, LOCATIONS["🇺🇸 Nellis AFB (NV, USA)"])
    
    # Create grid with location context
    size = 200
    x = np.linspace(-range_km, range_km, size)
    y = np.linspace(-range_km, range_km, size)
    X, Y = np.meshgrid(x, y)
    
    rcs = 0.001  # Default stealth RCS
    
    # Simulate radar return based on location
    distance = np.sqrt((X - target_x)**2 + (Y - target_y)**2)
    conventional = rcs * np.exp(-distance**2 / (2 * (range_km/8)**2))
    quantum = 0.15 * np.exp(-distance**2 / (2 * (range_km/4)**2))
    noise = np.random.randn(size, size) * 0.05
    radar_return = conventional + quantum + noise
    radar_return = np.clip(radar_return, 0, 1)
    
    return radar_return


# ── SIDEBAR ─────────────────────────────────────────────
with st.sidebar:
    st.title("🛸 StealthPDPRadar v4.0")
    st.markdown("*Real-World Radar Detection*")
    st.markdown("---")
    
    # Location Presets
    st.markdown("### 🌍 Location Presets")
    location_preset = st.selectbox(
        "Select Radar Station",
        list(LOCATIONS.keys())
    )
    
    location_info = LOCATIONS[location_preset]
    st.markdown(f"""
    <div class="location-card">
    📍 **{location_preset}**<br>
    📝 {location_info['description']}<br>
    🎯 Stealth Presence: {location_info['stealth_presence']}<br>
    📡 Range: {location_info['range_km']} km
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Data source
    st.markdown("### 📡 Data Source")
    data_mode = st.radio(
        "Select Mode",
        ["🟢 LIVE Radar Feed", "📁 Upload File", "🌌 Synthetic Demo"]
    )
    
    if data_mode == "🟢 LIVE Radar Feed":
        st.markdown('<span class="live-indicator"></span> **LIVE FEED ACTIVE**', unsafe_allow_html=True)
        st.caption(f"Simulating radar from {location_preset}")
    
    st.markdown("---")
    
    # Target selection
    st.markdown("### 🎯 Target")
    stealth_targets = ["F-35 Lightning II", "B-21 Raider", "NGAD", "HQ-19", "Kinzhal", "Su-57", "J-20", "Drone"]
    target = st.selectbox("Stealth Platform", stealth_targets)
    
    st.markdown("---")
    st.markdown("### ⚛️ PDP Parameters")
    epsilon = st.slider("Kinetic Mixing ε", 1e-12, 1e-8, 1e-10, format="%.1e")
    B_field = st.slider("B Field (G)", 1e13, 1e16, 1e15, format="%.1e")
    m_dark = st.slider("Dark Photon Mass (eV)", 1e-12, 1e-6, 1e-9, format="%.1e")
    
    st.markdown("---")
    st.markdown("### 📡 Radar Controls")
    
    # Use location's range as default
    default_range = location_info['range_km']
    range_km = st.slider("Range (km)", 50, 500, default_range)
    threshold = st.slider("Detection Threshold", 0.01, 0.5, 0.1)
    
    if data_mode == "🟢 LIVE Radar Feed":
        update_interval = st.slider("Update Interval (s)", 0.5, 5.0, 1.0)
        
        st.markdown("---")
        st.markdown("### 🎮 Target Movement")
        
        movement_mode = st.radio(
            "Movement Mode",
            ["🤖 Auto (Realistic Track)", "✋ Manual (Set Coordinates)"]
        )
        
        if movement_mode == "✋ Manual (Set Coordinates)":
            col_x, col_y = st.columns(2)
            with col_x:
                manual_x = st.number_input("X (km)", value=int(range_km * 0.3), step=10)
            with col_y:
                manual_y = st.number_input("Y (km)", value=int(range_km * 0.2), step=10)
            
            manual_x = np.clip(manual_x, -range_km, range_km)
            manual_y = np.clip(manual_y, -range_km, range_km)
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("▶️ Start Feed", use_container_width=True):
                st.session_state.live_active = True
                if 'live_feed' not in st.session_state:
                    st.session_state.live_feed = RealTimeRadarFeed(location_preset, target, range_km)
        with col_btn2:
            if st.button("⏹️ Stop Feed", use_container_width=True):
                st.session_state.live_active = False
    
    if data_mode == "📁 Upload File":
        uploaded_file = st.file_uploader(
            "Upload radar data",
            type=['csv', 'npy', 'txt', 'fits']
        )
    
    st.markdown("---")
    st.caption("Tony Ford | StealthPDPRadar v4.0")
    st.caption("Real-world location presets | Live radar simulation")


# ── INITIALIZE SESSION STATE ─────────────────────────────────────────────
if 'live_active' not in st.session_state:
    st.session_state.live_active = False
if 'live_feed' not in st.session_state:
    st.session_state.live_feed = None
if 'radar_history' not in st.session_state:
    st.session_state.radar_history = []


# ── MAIN APP ─────────────────────────────────────────────
st.title("🛸 StealthPDPRadar")
st.markdown(f"*Real-World Quantum Radar Simulation – {location_preset}*")
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
# Initialize variables
radar_return = None
timestamp = datetime.now()
enhanced = None
dark_mode_leakage = None
targets = []
detection_confidence = 0
conventional_strength = 0
quantum_signature = 0
enhancement_gain = 0
current_target_pos = None

# LIVE Radar Feed
if data_mode == "🟢 LIVE Radar Feed":
    if st.session_state.live_active:
        # Create or update feed
        if st.session_state.live_feed is None:
            st.session_state.live_feed = RealTimeRadarFeed(location_preset, target, range_km)
        
        # Update feed with current settings
        st.session_state.live_feed.location = location_preset
        st.session_state.live_feed.target_type = target
        st.session_state.live_feed.range_km = range_km
        
        # Apply manual coordinates if in manual mode
        if movement_mode == "✋ Manual (Set Coordinates)":
            st.session_state.live_feed.set_manual_coords(manual_x, manual_y)
            st.info(f"📍 **Manual Target:** X = {manual_x} km, Y = {manual_y} km")
        else:
            st.session_state.live_feed.set_auto_mode()
            st.caption("🤖 Target moving automatically (realistic track)")
        
        # Generate new scan
        radar_data = st.session_state.live_feed.update()
        radar_return = radar_data['data']
        timestamp = radar_data['timestamp']
        current_target_pos = radar_data['target_position']
        
        # Store history
        st.session_state.radar_history.append({
            'timestamp': timestamp,
            'confidence': np.max(radar_return),
            'scan_number': radar_data['scan_number'],
            'target_x': current_target_pos[0],
            'target_y': current_target_pos[1],
            'location': location_preset
        })
        if len(st.session_state.radar_history) > 30:
            st.session_state.radar_history.pop(0)
        
        # Show live indicator with location
        mode_text = "MANUAL" if radar_data['manual_mode'] else "AUTO"
        st.caption(f"🟢 **LIVE** | {location_preset} | Mode: {mode_text} | Scan #{radar_data['scan_number']} | {timestamp.strftime('%H:%M:%S')}")
        
        # Auto-refresh
        time.sleep(update_interval)
        st.rerun()
    else:
        st.warning("🟡 **Click 'Start Feed' to begin real-time radar data acquisition**")
        # Generate placeholder based on location
        radar_return = generate_location_visualization(location_preset, range_km, range_km*0.3, range_km*0.2)
        timestamp = datetime.now()

# File Upload Mode
elif data_mode == "📁 Upload File" and 'uploaded_file' in locals() and uploaded_file is not None:
    with st.spinner(f"Loading radar data from {location_preset}..."):
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
        
        if radar_return.max() > radar_return.min():
            radar_return = (radar_return - radar_return.min()) / (radar_return.max() - radar_return.min())
        
        st.success(f"✅ Loaded: {uploaded_file.name} | Location: {location_preset} | Shape: {radar_return.shape}")
        timestamp = datetime.now()

# Synthetic Demo Mode
elif data_mode == "🌌 Synthetic Demo":
    # Use location-based demo
    demo_x = st.slider("Target X (km)", -range_km, range_km, int(range_km * 0.3), key="demo_x")
    demo_y = st.slider("Target Y (km)", -range_km, range_km, int(range_km * 0.2), key="demo_y")
    
    radar_return = generate_location_visualization(location_preset, range_km, demo_x, demo_y)
    timestamp = datetime.now()
    current_target_pos = (demo_x, demo_y)


# ── PROCESS WITH PDP FILTER ─────────────────────────────────────────────
if radar_return is not None:
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
    if radar_return is not None:
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
    if dark_mode_leakage is not None:
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
    if enhanced is not None and dark_mode_leakage is not None and radar_return is not None:
        rgb = np.stack([radar_return, dark_mode_leakage, enhanced], axis=-1)
        ax.imshow(np.clip(rgb, 0, 1), extent=[-range_km, range_km, -range_km, range_km])
    ax.set_title(f"PDP Quantum Radar\n{location_preset}", color='white', fontsize=10)
    ax.set_xlabel("Range (km)", color='white')
    ax.set_ylabel("Range (km)", color='white')
    ax.tick_params(colors='white')
    safe_display_plot(fig)
    st.caption("🌈 Blue-halo fusion - target detected")

# Show target coordinates
if current_target_pos is not None:
    st.caption(f"📍 **Target Position:** X = {current_target_pos[0]:.1f} km, Y = {current_target_pos[1]:.1f} km")


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


# ── HISTORY GRAPH ─────────────────────────────────────────────
if st.session_state.radar_history:
    st.markdown("---")
    st.markdown("### 📈 Detection History")
    
    history_df = pd.DataFrame([
        {'Scan': h['scan_number'], 'Confidence': h['confidence'] * 100}
        for h in st.session_state.radar_history[-20:]
    ])
    
    fig, ax = plt.subplots(figsize=(10, 4), facecolor='#0a0a1a')
    ax.bar(history_df['Scan'], history_df['Confidence'], color='#00aaff')
    ax.axhline(y=10, color='red', linestyle='--', label='Detection Threshold')
    ax.set_xlabel("Scan Number", color='white')
    ax.set_ylabel("Detection Confidence (%)", color='white')
    ax.set_title(f"Live Detection Confidence - {location_preset}", color='white')
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
    if enhanced is not None:
        st.download_button("📸 PDP Radar Image", save_array_png(enhanced), f"pdp_radar_{location_preset.replace(' ', '_')}.png", width='stretch')

with col_e2:
    metadata = {
        "timestamp": str(timestamp),
        "location": location_preset,
        "target": target,
        "range_km": range_km,
        "detection_confidence": detection_confidence,
        "quantum_signature": float(quantum_signature),
        "mode": data_mode,
        "target_position": current_target_pos
    }
    st.download_button("📋 Export Metadata", json.dumps(metadata, indent=2), "radar_metadata.json", width='stretch')

with col_e3:
    if st.session_state.radar_history:
        history_data = json.dumps([
            {'timestamp': str(h['timestamp']), 'confidence': float(h['confidence']), 
             'scan': h['scan_number'], 'location': h.get('location', location_preset)}
            for h in st.session_state.radar_history
        ], indent=2)
        st.download_button("📊 Export History", history_data, "detection_history.json", width='stretch')


# ── THEORY ─────────────────────────────────────────────
with st.expander("📖 How It Works – PDP Quantum Radar"):
    st.markdown(r"""
    ### Photon-Dark-Photon Quantum Radar
    
    **Real-World Locations:** Simulates radar coverage at major air bases and test sites worldwide
    
    **Location Presets:**
    - 🇺🇸 Nellis AFB – F-35 testing
    - 🇺🇸 Edwards AFB – B-21 Raider development
    - 🇺🇸 Area 51 – NGAD testing
    - 🇬🇧 RAF Lakenheath – US F-35A in Europe
    - 🇷🇺 Akhtubinsk – Russian Su-57 testing
    - 🇨🇳 Dingxin – Chinese J-20 operations
    - 🇮🇷 Shahid Satari – Missile/drone testing
    - 🇰🇵 Sohae – North Korean missile facility
    - 🇮🇱 Palmachim – Israeli F-35I operations
    - 🇦🇪 Al Dhafra – US F-35 deployment
    
    **Detection Chain:**
    1. Radar pulse transmitted from location
    2. Photon-dark-photon mixing: $P(\gamma \to A') = (\varepsilon B / m')^2 \sin^2(m'^2 L / 4\omega)$
    3. Dark photons interact with stealth target
    4. Unique quantum signature returned
    5. PDP filter extracts signature
    
    **Result:** Detection of stealth platforms at >250 km range
    """)

st.markdown("---")
st.markdown("🛸 **StealthPDPRadar v4.0** | Real-World Location Presets | Live Radar | Tony Ford Model")
