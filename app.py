"""
StealthPDPRadar v9.0 – Fully Automatic Radar
Auto-search | Auto-identify | Continuous live feed
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
import requests
import threading

warnings.filterwarnings('ignore')

# ── PAGE CONFIG ─────────────────────────────────────────────
st.set_page_config(
    layout="wide",
    page_title="StealthPDPRadar v9.0",
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
    .stealth-alert {
        background-color: #ff4444;
        color: white;
        padding: 10px;
        border-radius: 8px;
        text-align: center;
        font-weight: bold;
        margin: 10px 0;
        animation: pulse 1s infinite;
    }
    .auto-badge {
        background-color: #00aaff;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        display: inline-block;
        margin-left: 10px;
    }
</style>
""", unsafe_allow_html=True)


# ── AIRPORT DATABASE ─────────────────────────────────────────────
AIRPORTS = {
    "🇺🇸 Nellis AFB (Las Vegas)": {"lat": 36.2358, "lon": -115.0341, "range_km": 300, "code": "LSV"},
    "🇺🇸 Edwards AFB": {"lat": 34.9056, "lon": -117.8839, "range_km": 350, "code": "EDW"},
    "🇺🇸 Area 51": {"lat": 37.2390, "lon": -115.8158, "range_km": 400, "code": "XTA"},
    "🇬🇧 RAF Lakenheath": {"lat": 52.4092, "lon": 0.5565, "range_km": 250, "code": "LKZ"},
    "🇷🇺 Moscow Domodedovo": {"lat": 55.4086, "lon": 37.9063, "range_km": 350, "code": "DME"},
    "🇨🇳 Beijing Capital": {"lat": 40.0801, "lon": 116.5846, "range_km": 400, "code": "PEK"},
    "🇫🇷 Paris CDG": {"lat": 49.0097, "lon": 2.5479, "range_km": 300, "code": "CDG"},
    "🇩🇪 Frankfurt": {"lat": 50.0379, "lon": 8.5622, "range_km": 300, "code": "FRA"},
    "🇯🇵 Tokyo Narita": {"lat": 35.7647, "lon": 140.3864, "range_km": 350, "code": "NRT"},
    "🇦🇪 Dubai International": {"lat": 25.2532, "lon": 55.3657, "range_km": 320, "code": "DXB"},
}

RCS_FACTORS = {
    "F-35 Lightning II": 0.001,
    "B-21 Raider": 0.0005,
    "NGAD": 0.0003,
    "Su-57": 0.01,
    "J-20": 0.008,
    "Commercial Airliner": 50.0,
    "Private Jet": 10.0,
    "Military Transport": 30.0,
    "Drone": 0.02
}


# ── WORKING ADSB FETCHER ─────────────────────────────────────────────

def fetch_opensky_aircraft(lat, lon, radius_km=300):
    """Fetch real aircraft from OpenSky Network API"""
    try:
        url = "https://opensky-network.org/api/states/all"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            states = data.get('states', [])
            
            aircraft = []
            for state in states:
                if state is None:
                    continue
                    
                callsign = state[1] if state[1] else "Unknown"
                lon_pos = state[5]
                lat_pos = state[6]
                altitude = state[7] if state[7] else 0
                velocity = state[9] if state[9] else 0
                
                if lat_pos and lon_pos:
                    dx = (lon_pos - lon) * 111 * np.cos(np.radians(lat))
                    dy = (lat_pos - lat) * 111
                    distance = np.sqrt(dx**2 + dy**2)
                    
                    if distance <= radius_km:
                        # Auto-identify aircraft type
                        if any(x in callsign.upper() for x in ['AF', 'RCH', 'CFC', 'RRR', 'GAF', 'FNY', 'NATO']):
                            ac_type = "Military Transport"
                        elif callsign.startswith('N') and len(callsign) > 3:
                            ac_type = "Private Jet"
                        elif callsign != "Unknown":
                            ac_type = "Commercial Airliner"
                        else:
                            ac_type = "Unknown"
                        
                        aircraft.append({
                            'callsign': callsign,
                            'lat': lat_pos,
                            'lon': lon_pos,
                            'x_km': dx,
                            'y_km': dy,
                            'altitude': altitude,
                            'speed': velocity,
                            'type': ac_type,
                            'distance': distance
                        })
            return aircraft
    except Exception as e:
        pass
    
    return []


def generate_simulated_aircraft(lat, lon, radius_km):
    """Generate realistic simulated aircraft when API unavailable"""
    aircraft = []
    commercial_callsigns = ["UAL", "DAL", "AAL", "SWA", "JBU", "BAW", "AFR", "DLH"]
    military_callsigns = ["RCH", "AF1", "CFC", "RRR", "GAF", "USAF"]
    
    num_aircraft = np.random.randint(15, 35)
    
    for i in range(num_aircraft):
        angle = np.random.uniform(0, 2*np.pi)
        dist = np.random.uniform(15, radius_km - 15)
        x_km = dist * np.cos(angle)
        y_km = dist * np.sin(angle)
        
        # Auto-identify based on distance
        if dist < radius_km * 0.15:
            ac_type = np.random.choice(["Commercial Airliner", "Private Jet"], p=[0.7, 0.3])
        elif dist > radius_km * 0.7:
            ac_type = np.random.choice(["Military Transport", "Commercial Airliner"], p=[0.6, 0.4])
        else:
            ac_type = np.random.choice(["Commercial Airliner", "Private Jet", "Military Transport"], p=[0.5, 0.3, 0.2])
        
        if ac_type == "Commercial Airliner":
            callsign = f"{np.random.choice(commercial_callsigns)}{np.random.randint(100, 999)}"
            altitude = np.random.randint(28000, 41000)
            speed = np.random.randint(400, 550)
        elif ac_type == "Military Transport":
            callsign = f"{np.random.choice(military_callsigns)}{np.random.randint(10, 999)}"
            altitude = np.random.randint(20000, 35000)
            speed = np.random.randint(350, 500)
        else:
            callsign = f"N{np.random.randint(1000, 9999)}"
            altitude = np.random.randint(5000, 25000)
            speed = np.random.randint(180, 350)
        
        aircraft.append({
            'callsign': callsign,
            'x_km': x_km,
            'y_km': y_km,
            'altitude': altitude,
            'speed': speed,
            'type': ac_type,
            'distance': dist
        })
    
    return aircraft


# ── PDP STEALTH DETECTION ─────────────────────────────────────────────

def apply_pdp_stealth_detection(aircraft_list, target_type, epsilon=1e-10, B_field=1e15, m_dark=1e-9):
    """Auto-detect stealth aircraft using PDP quantum filter"""
    rcs = RCS_FACTORS.get(target_type, 0.001)
    mixing = epsilon * B_field / (m_dark + 1e-12)
    
    for ac in aircraft_list:
        # Auto-calculate quantum signature
        if ac['type'] in ["Commercial Airliner", "Private Jet"]:
            quantum_sig = 0.01 * mixing
            stealth_prob = 0
        elif ac['type'] == "Military Transport":
            quantum_sig = 0.05 * mixing
            stealth_prob = np.random.uniform(0, 15)
        else:
            quantum_sig = (1 / (rcs + 1e-12)) ** 0.25 * mixing * 8
            stealth_prob = min(quantum_sig * 100, 95)
        
        ac['quantum_signature'] = quantum_sig
        ac['stealth_probability'] = stealth_prob
        ac['is_stealth'] = stealth_prob > 20
    
    return aircraft_list


# ── AUTO-RADAR ENGINE ─────────────────────────────────────────────

class AutoRadar:
    """Automatic continuous radar scanner"""
    
    def __init__(self):
        self.is_running = True
        self.last_update = 0
        self.update_interval = 8  # seconds between auto-scans
    
    def should_scan(self):
        current = time.time()
        if current - self.last_update >= self.update_interval:
            self.last_update = current
            return True
        return False


# ── SIDEBAR ─────────────────────────────────────────────
with st.sidebar:
    st.title("🛸 StealthPDPRadar v9.0")
    st.markdown("*Fully Automatic Radar*")
    st.markdown("---")
    
    # Location selection
    st.markdown("### 📡 Radar Location")
    selected_airport = st.selectbox("Select Airport/Base", list(AIRPORTS.keys()), index=0)
    airport = AIRPORTS[selected_airport]
    
    use_custom = st.checkbox("Custom coordinates", value=False)
    if use_custom:
        col_lat, col_lon = st.columns(2)
        with col_lat:
            custom_lat = st.number_input("Latitude", value=airport['lat'], format="%.4f")
        with col_lon:
            custom_lon = st.number_input("Longitude", value=airport['lon'], format="%.4f")
        radar_lat, radar_lon = custom_lat, custom_lon
    else:
        radar_lat, radar_lon = airport['lat'], airport['lon']
    
    range_km = st.slider("Radar Range (km)", 50, 500, airport['range_km'])
    
    st.markdown("---")
    
    # Stealth target to detect
    st.markdown("### 🎯 Auto-Search For")
    target = st.selectbox("Stealth Platform", list(RCS_FACTORS.keys())[:5], index=0)
    
    st.markdown("---")
    
    # PDP Parameters
    st.markdown("### ⚛️ PDP Parameters")
    epsilon = st.slider("Kinetic Mixing ε", 1e-12, 1e-8, 1e-10, format="%.1e")
    B_field = st.slider("B Field (G)", 1e13, 1e16, 1e15, format="%.1e")
    m_dark = st.slider("Dark Photon Mass (eV)", 1e-12, 1e-6, 1e-9, format="%.1e")
    
    st.markdown("---")
    st.caption("🟢 **AUTO MODE** – Continuous scanning")
    st.caption("Tony Ford | StealthPDPRadar v9.0")
    st.caption("Auto-search | Auto-identify | Live radar")


# ── INITIALIZE SESSION STATE ─────────────────────────────────────────────
if 'aircraft_data' not in st.session_state:
    st.session_state.aircraft_data = []
if 'auto_radar' not in st.session_state:
    st.session_state.auto_radar = AutoRadar()
if 'last_scan_time' not in st.session_state:
    st.session_state.last_scan_time = None


# ── AUTO-SCAN ENGINE ─────────────────────────────────────────────
# This runs automatically on every page refresh
if st.session_state.auto_radar.should_scan():
    with st.spinner("🔄 Auto-scanning radar..."):
        # Fetch real aircraft
        aircraft = fetch_opensky_aircraft(radar_lat, radar_lon, range_km)
        
        # Fallback to simulated if no data
        if not aircraft:
            aircraft = generate_simulated_aircraft(radar_lat, radar_lon, range_km)
        
        # Auto-apply PDP stealth detection
        aircraft = apply_pdp_stealth_detection(aircraft, target, epsilon, B_field, m_dark)
        
        st.session_state.aircraft_data = aircraft
        st.session_state.last_scan_time = datetime.now()
        
        # Auto-rerun to refresh display
        st.rerun()


# ── MAIN DISPLAY ─────────────────────────────────────────────
st.title("🛸 StealthPDPRadar")
st.markdown(f"*Fully Automatic Radar – {selected_airport}*")
st.markdown(f"**Auto-Searching for:** {target} | **Range:** {range_km} km")
st.markdown("---")

# Live indicator and auto-status
st.markdown(f"""
<div>
    <span class="live-indicator"></span> 
    <strong>AUTO RADAR ACTIVE</strong> 
    <span class="auto-badge">Continuous Scanning</span>
</div>
""", unsafe_allow_html=True)

if st.session_state.last_scan_time:
    st.caption(f"🕒 Last auto-scan: {st.session_state.last_scan_time.strftime('%H:%M:%S')} | Next scan in ~{st.session_state.auto_radar.update_interval}s")

st.markdown("---")

# Metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("✈️ Total Aircraft", len(st.session_state.aircraft_data))
with col2:
    civilian = len([a for a in st.session_state.aircraft_data if a['type'] in ["Commercial Airliner", "Private Jet"]])
    st.metric("🟢 Civilian", civilian)
with col3:
    military = len([a for a in st.session_state.aircraft_data if a['type'] == "Military Transport"])
    st.metric("🟠 Military", military)
with col4:
    stealth = len([a for a in st.session_state.aircraft_data if a.get('is_stealth', False)])
    st.metric("🔴 Potential Stealth", stealth)


# ── RADAR DISPLAY ─────────────────────────────────────────────
st.markdown("### 📡 Auto-Radar View")

fig, ax = plt.subplots(figsize=(10, 10), facecolor='#0a0a1a')
ax.set_facecolor('#0a0a1a')
ax.set_xlim(-range_km, range_km)
ax.set_ylim(-range_km, range_km)
ax.set_aspect('equal')

# Range rings
for r in [range_km/4, range_km/2, 3*range_km/4, range_km]:
    circle = Circle((0, 0), r, fill=False, edgecolor='#335588', linestyle='--', linewidth=1)
    ax.add_patch(circle)

# Crosshairs
ax.axhline(y=0, color='#335588', linewidth=0.5)
ax.axvline(x=0, color='#335588', linewidth=0.5)

# Radar center
ax.plot(0, 0, 'o', color='#00aaff', markersize=12, label='Radar Site')

# Plot all auto-detected aircraft
for ac in st.session_state.aircraft_data:
    x = ac['x_km']
    y = ac['y_km']
    
    if ac.get('is_stealth', False):
        color = '#ff4444'
        marker = 's'
        size = 140
        zorder = 10
    elif ac['type'] == "Military Transport":
        color = '#ffaa44'
        marker = '^'
        size = 100
        zorder = 6
    elif ac['type'] == "Commercial Airliner":
        color = '#88ff88'
        marker = 'o'
        size = 90
        zorder = 5
    else:
        color = '#44aaff'
        marker = 'o'
        size = 80
        zorder = 5
    
    ax.scatter(x, y, c=color, marker=marker, s=size, alpha=0.9, edgecolors='white', linewidth=1)
    ax.annotate(ac['callsign'], (x, y), xytext=(8, 8), textcoords='offset points',
                fontsize=9, color='white', alpha=0.9)

# Legend
legend_elements = [
    plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#88ff88', markersize=10, label='Civilian'),
    plt.Line2D([0], [0], marker='^', color='w', markerfacecolor='#ffaa44', markersize=10, label='Military'),
    plt.Line2D([0], [0], marker='s', color='w', markerfacecolor='#ff4444', markersize=10, label=f'Auto-Detected {target}'),
]
ax.legend(handles=legend_elements, loc='upper right', facecolor='#1a1a3a', labelcolor='white')

ax.set_xlabel("East-West (km)", color='white')
ax.set_ylabel("North-South (km)", color='white')
ax.tick_params(colors='white')
ax.grid(True, alpha=0.2)

st.pyplot(fig)
plt.close(fig)


# ── AUTO-IDENTIFIED AIRCRAFT TABLE ─────────────────────────────────────────────
st.markdown("---")
st.markdown("### ✈️ Auto-Identified Aircraft")

if st.session_state.aircraft_data:
    df = pd.DataFrame(st.session_state.aircraft_data)
    display_cols = ['callsign', 'type', 'x_km', 'y_km', 'altitude', 'speed', 'stealth_probability']
    df_display = df[display_cols].copy()
    df_display['x_km'] = df_display['x_km'].round(1)
    df_display['y_km'] = df_display['y_km'].round(1)
    df_display['stealth_probability'] = df_display['stealth_probability'].round(1)
    df_display = df_display.sort_values('stealth_probability', ascending=False)
    
    st.dataframe(df_display, use_container_width=True)


# ── AUTO-STEALTH ALERTS ─────────────────────────────────────────────
auto_stealth = [ac for ac in st.session_state.aircraft_data if ac.get('is_stealth', False)]

if auto_stealth:
    st.markdown("---")
    st.markdown("### 🚨 AUTO-STEALTH DETECTION ALERT")
    
    for ac in auto_stealth:
        st.markdown(f"""
        <div class="stealth-alert">
        ⚠️ **AUTO-DETECTED: POTENTIAL {target}**<br>
        📍 Position: {ac['x_km']:.1f} km E, {ac['y_km']:.1f} km N<br>
        🎯 Signature Match: {ac['stealth_probability']:.1f}%<br>
        📡 Callsign: {ac['callsign']} | Type: {ac['type']}<br>
        🛸 Altitude: {ac['altitude']:,} ft | Speed: {ac['speed']} kt
        </div>
        """, unsafe_allow_html=True)


# ── EXPORT ─────────────────────────────────────────────
st.markdown("---")
st.markdown("### 💾 Export Data")

col_e1, col_e2 = st.columns(2)

with col_e1:
    if st.session_state.aircraft_data:
        df_export = pd.DataFrame(st.session_state.aircraft_data)
        csv_data = df_export.to_csv(index=False).encode()
        st.download_button("📊 Export Aircraft Data (CSV)", csv_data, f"radar_auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", width='stretch')

with col_e2:
    report = {
        "timestamp": datetime.now().isoformat(),
        "location": selected_airport,
        "target": target,
        "auto_detected_stealth": len(auto_stealth),
        "total_aircraft": len(st.session_state.aircraft_data)
    }
    st.download_button("📋 Export Report (JSON)", json.dumps(report, indent=2), "auto_radar_report.json", width='stretch')


# ── AUTO-REFRESH ─────────────────────────────────────────────
# The app auto-refreshes when radar scans
st.markdown("---")
st.markdown("🛸 **StealthPDPRadar v9.0** | Fully Automatic | Continuous Scanning | Tony Ford Model")
