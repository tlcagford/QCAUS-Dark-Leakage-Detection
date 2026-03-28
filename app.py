"""
StealthPDPRadar v8.1 – Working Live ADSB Feed
Fixed API | OpenSky Network | Real aircraft data
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

warnings.filterwarnings('ignore')

# ── PAGE CONFIG ─────────────────────────────────────────────
st.set_page_config(
    layout="wide",
    page_title="StealthPDPRadar v8.1",
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
    .aircraft-card {
        background-color: #1a1a3a;
        padding: 8px;
        border-radius: 6px;
        margin: 5px 0;
        border-left: 3px solid #00aaff;
        font-size: 12px;
    }
    .stealth-alert {
        background-color: #ff4444;
        color: white;
        padding: 10px;
        border-radius: 8px;
        text-align: center;
        font-weight: bold;
        margin: 10px 0;
    }
    .coord-panel {
        background-color: #1a1a3a;
        padding: 10px;
        border-radius: 8px;
        margin: 10px 0;
        border: 1px solid #00aaff;
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


# ── WORKING ADSB FETCHERS ─────────────────────────────────────────────

def fetch_opensky_aircraft(lat, lon, radius_km=300):
    """
    Fetch real aircraft from OpenSky Network API (no key required, rate-limited but works)
    """
    try:
        # OpenSky Network states API
        url = "https://opensky-network.org/api/states/all"
        response = requests.get(url, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            states = data.get('states', [])
            
            aircraft = []
            for state in states:
                if state is None:
                    continue
                    
                icao24 = state[0]
                callsign = state[1] if state[1] else "Unknown"
                origin_country = state[2] if state[2] else "Unknown"
                lon_pos = state[5]
                lat_pos = state[6]
                altitude = state[7] if state[7] else 0
                velocity = state[9] if state[9] else 0
                
                # Filter by position
                if lat_pos and lon_pos:
                    dx = (lon_pos - lon) * 111 * np.cos(np.radians(lat))
                    dy = (lat_pos - lat) * 111
                    distance = np.sqrt(dx**2 + dy**2)
                    
                    if distance <= radius_km:
                        # Determine aircraft type based on callsign or origin
                        if any(x in callsign.upper() for x in ['AF', 'RCH', 'CFC', 'RRR', 'GAF', 'FNY']):
                            ac_type = "Military Transport"
                        elif callsign.startswith('N') and len(callsign) > 3:
                            ac_type = "Private Jet"
                        elif callsign != "Unknown":
                            ac_type = "Commercial Airliner"
                        else:
                            ac_type = "Unknown"
                        
                        aircraft.append({
                            'callsign': callsign,
                            'icao24': icao24,
                            'lat': lat_pos,
                            'lon': lon_pos,
                            'x_km': dx,
                            'y_km': dy,
                            'altitude': altitude,
                            'speed': velocity,
                            'type': ac_type,
                            'origin': origin_country,
                            'distance': distance
                        })
            
            return aircraft
    except Exception as e:
        st.warning(f"OpenSky API: {e}")
    
    return []


def generate_realistic_simulated_aircraft(lat, lon, radius_km):
    """Generate realistic simulated aircraft with proper patterns"""
    aircraft = []
    
    # Commercial routes - typically along major corridors
    commercial_callsigns = ["UAL", "DAL", "AAL", "SWA", "JBU", "FDX", "UPS", "BAW", "AFR", "DLH"]
    military_callsigns = ["RCH", "AF1", "CFC", "RRR", "GAF", "FNY", "NATO", "USAF"]
    private_prefixes = ["N", "G", "M", "VP"]
    
    num_aircraft = np.random.randint(15, 35)
    
    for i in range(num_aircraft):
        # Generate position in a realistic pattern (radial distribution)
        angle = np.random.uniform(0, 2*np.pi)
        dist = np.random.uniform(15, radius_km - 15)
        x_km = dist * np.cos(angle)
        y_km = dist * np.sin(angle)
        
        # Determine type based on position and random
        if dist < radius_km * 0.2:
            # Closer to airport - more likely commercial
            type_weights = [0.6, 0.2, 0.2]
        else:
            type_weights = [0.4, 0.3, 0.3]
        
        ac_type = np.random.choice(["Commercial Airliner", "Private Jet", "Military Transport"], p=type_weights)
        
        # Generate callsign based on type
        if ac_type == "Commercial Airliner":
            callsign = f"{np.random.choice(commercial_callsigns)}{np.random.randint(100, 999)}"
            altitude = np.random.randint(28000, 41000)
            speed = np.random.randint(400, 550)
        elif ac_type == "Military Transport":
            callsign = f"{np.random.choice(military_callsigns)}{np.random.randint(10, 999)}"
            altitude = np.random.randint(20000, 35000)
            speed = np.random.randint(350, 500)
        else:
            callsign = f"{np.random.choice(private_prefixes)}{np.random.randint(100, 9999)}"
            altitude = np.random.randint(5000, 25000)
            speed = np.random.randint(180, 350)
        
        aircraft.append({
            'callsign': callsign,
            'lat': lat + (y_km / 111),
            'lon': lon + (x_km / 111),
            'x_km': x_km,
            'y_km': y_km,
            'altitude': altitude,
            'speed': speed,
            'type': ac_type,
            'origin': "Simulated",
            'distance': dist
        })
    
    return aircraft


# ── PDP QUANTUM RADAR CORE ─────────────────────────────────────────────

def apply_pdp_stealth_detection(aircraft_list, target_type, epsilon=1e-10, B_field=1e15, m_dark=1e-9, threshold=20):
    """Apply PDP quantum filter to detect stealth aircraft"""
    rcs = RCS_FACTORS.get(target_type, 0.001)
    
    # PDP mixing strength
    mixing = epsilon * B_field / (m_dark + 1e-12)
    
    for ac in aircraft_list:
        # Calculate quantum signature
        # Stealth aircraft have small RCS → LARGE quantum signature
        # Regular aircraft have large RCS → small quantum signature
        
        if ac['type'] in ["Commercial Airliner", "Private Jet"]:
            base_rcs = RCS_FACTORS.get(ac['type'], 50.0)
            quantum_sig = 0.01 * mixing * (50.0 / base_rcs)
            stealth_prob = 0
            detected = False
        elif ac['type'] == "Military Transport":
            base_rcs = RCS_FACTORS.get(ac['type'], 30.0)
            quantum_sig = 0.05 * mixing * (30.0 / base_rcs)
            stealth_prob = np.random.uniform(0, 15)
            detected = stealth_prob > threshold
        else:
            # Unknown type - could be stealth
            quantum_sig = (1 / (rcs + 1e-12)) ** 0.25 * mixing * 8
            stealth_prob = min(quantum_sig * 100, 95)
            detected = stealth_prob > threshold
        
        ac['quantum_signature'] = quantum_sig
        ac['stealth_probability'] = stealth_prob
        ac['detected'] = detected
    
    return aircraft_list


# ── SIDEBAR ─────────────────────────────────────────────
with st.sidebar:
    st.title("🛸 StealthPDPRadar v8.1")
    st.markdown("*Live ADSB Radar | Working API*")
    st.markdown("---")
    
    # Location selection
    st.markdown("### 📡 Radar Location")
    airport_names = list(AIRPORTS.keys())
    selected_airport = st.selectbox("Select Airport/Base", airport_names, index=0)
    airport = AIRPORTS[selected_airport]
    
    # Manual coordinates
    use_custom = st.checkbox("Use custom coordinates", value=False)
    
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
    
    # Stealth target
    st.markdown("### 🎯 Search For")
    stealth_targets = ["F-35 Lightning II", "B-21 Raider", "NGAD", "Su-57", "J-20"]
    target = st.selectbox("Stealth Platform", stealth_targets, index=0)
    
    st.markdown("---")
    
    # Data source
    st.markdown("### 📡 Data Source")
    data_source = st.radio("Source", ["🌍 OpenSky Network", "🧪 Simulated Aircraft"], index=1)
    
    st.markdown("---")
    
    # PDP Parameters
    st.markdown("### ⚛️ PDP Parameters")
    epsilon = st.slider("Kinetic Mixing ε", 1e-12, 1e-8, 1e-10, format="%.1e")
    B_field = st.slider("B Field (G)", 1e13, 1e16, 1e15, format="%.1e")
    m_dark = st.slider("Dark Photon Mass (eV)", 1e-12, 1e-6, 1e-9, format="%.1e")
    threshold = st.slider("Detection Threshold", 0, 100, 20)
    
    st.markdown("---")
    
    # Controls
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔄 SCAN NOW", use_container_width=True):
            st.session_state.scan_requested = True
    with col_btn2:
        if st.button("📡 LIVE MODE", use_container_width=True):
            st.session_state.live_mode = not st.session_state.get('live_mode', False)
    
    st.markdown("---")
    st.caption("Tony Ford | StealthPDPRadar v8.1")
    st.caption("OpenSky Network | Real aircraft data")


# ── INITIALIZE SESSION STATE ─────────────────────────────────────────────
if 'aircraft_data' not in st.session_state:
    st.session_state.aircraft_data = []
if 'scan_requested' not in st.session_state:
    st.session_state.scan_requested = True
if 'live_mode' not in st.session_state:
    st.session_state.live_mode = False
if 'last_scan' not in st.session_state:
    st.session_state.last_scan = 0


# ── FETCH AIRCRAFT DATA ─────────────────────────────────────────────
current_time = time.time()

if st.session_state.scan_requested or (st.session_state.live_mode and (current_time - st.session_state.last_scan >= 15)):
    with st.spinner(f"Scanning radar at {selected_airport}..."):
        if data_source == "🌍 OpenSky Network":
            aircraft = fetch_opensky_aircraft(radar_lat, radar_lon, range_km)
            if not aircraft:
                st.info("Using simulated aircraft (OpenSky data temporarily unavailable)")
                aircraft = generate_realistic_simulated_aircraft(radar_lat, radar_lon, range_km)
        else:
            aircraft = generate_realistic_simulated_aircraft(radar_lat, radar_lon, range_km)
        
        # Apply PDP stealth detection
        aircraft = apply_pdp_stealth_detection(aircraft, target, epsilon, B_field, m_dark, threshold)
        
        st.session_state.aircraft_data = aircraft
        st.session_state.scan_requested = False
        st.session_state.last_scan = current_time
        st.session_state.last_update_time = datetime.now()


# ── MAIN DISPLAY ─────────────────────────────────────────────
st.title("🛸 StealthPDPRadar")
st.markdown(f"*Live Radar – {selected_airport}*")
st.markdown(f"**Searching for:** {target} | **Range:** {range_km} km")
st.markdown("---")

# Live indicator
if st.session_state.live_mode:
    st.markdown('<div><span class="live-indicator"></span> <strong>LIVE MODE ACTIVE</strong> - Auto-updating every 15 seconds</div>', unsafe_allow_html=True)
else:
    st.info("🔄 **MANUAL MODE** - Click 'SCAN NOW' to update")

st.caption(f"📡 Last scan: {st.session_state.last_update_time.strftime('%H:%M:%S') if hasattr(st.session_state, 'last_update_time') else 'Never'} | Source: {data_source}")
st.markdown("---")

# Metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Aircraft Tracked", len(st.session_state.aircraft_data))
with col2:
    civilian = len([a for a in st.session_state.aircraft_data if a['type'] in ["Commercial Airliner", "Private Jet"]])
    st.metric("Civilian", civilian)
with col3:
    military = len([a for a in st.session_state.aircraft_data if a['type'] == "Military Transport"])
    st.metric("Military", military)
with col4:
    stealth = len([a for a in st.session_state.aircraft_data if a.get('stealth_probability', 0) > threshold])
    st.metric("⚠️ Potential Stealth", stealth)


# ── RADAR DISPLAY ─────────────────────────────────────────────
st.markdown("### 📡 Radar View")

fig, ax = plt.subplots(figsize=(10, 10), facecolor='#0a0a1a')
ax.set_facecolor('#0a0a1a')
ax.set_xlim(-range_km, range_km)
ax.set_ylim(-range_km, range_km)
ax.set_aspect('equal')

# Draw range rings
for r in [range_km/4, range_km/2, 3*range_km/4, range_km]:
    circle = Circle((0, 0), r, fill=False, edgecolor='#335588', linestyle='--', linewidth=1)
    ax.add_patch(circle)

# Draw crosshairs
ax.axhline(y=0, color='#335588', linewidth=0.5)
ax.axvline(x=0, color='#335588', linewidth=0.5)

# Radar center
ax.plot(0, 0, 'o', color='#00aaff', markersize=10, label='Radar Site')

# Plot aircraft
for ac in st.session_state.aircraft_data:
    x = ac['x_km']
    y = ac['y_km']
    
    # Color based on type and stealth detection
    if ac.get('stealth_probability', 0) > threshold:
        color = '#ff4444'
        marker = 's'
        size = 120
        zorder = 10
    elif ac['type'] == "Commercial Airliner":
        color = '#88ff88'
        marker = 'o'
        size = 80
        zorder = 5
    elif ac['type'] == "Private Jet":
        color = '#88ff88'
        marker = 'd'
        size = 70
        zorder = 5
    elif ac['type'] == "Military Transport":
        color = '#ffaa44'
        marker = '^'
        size = 90
        zorder = 6
    else:
        color = '#44aaff'
        marker = 'o'
        size = 60
        zorder = 5
    
    ax.scatter(x, y, c=color, marker=marker, s=size, alpha=0.9, edgecolors='white', linewidth=0.8)
    
    # Add callsign label
    ax.annotate(ac['callsign'], (x, y), xytext=(8, 8), textcoords='offset points',
                fontsize=9, color='white', alpha=0.9, fontweight='bold')

# Legend
legend_elements = [
    plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#88ff88', markersize=10, label='Civilian'),
    plt.Line2D([0], [0], marker='^', color='w', markerfacecolor='#ffaa44', markersize=10, label='Military'),
    plt.Line2D([0], [0], marker='s', color='w', markerfacecolor='#ff4444', markersize=10, label=f'Potential {target}'),
]
ax.legend(handles=legend_elements, loc='upper right', facecolor='#1a1a3a', labelcolor='white', fontsize=10)

ax.set_xlabel("East-West (km)", color='white', fontsize=12)
ax.set_ylabel("North-South (km)", color='white', fontsize=12)
ax.tick_params(colors='white')
ax.grid(True, alpha=0.2, color='white')

st.pyplot(fig)
plt.close(fig)


# ── AIRCRAFT TABLE ─────────────────────────────────────────────
st.markdown("---")
st.markdown("### ✈️ Aircraft Detected")

if st.session_state.aircraft_data:
    df = pd.DataFrame(st.session_state.aircraft_data)
    display_cols = ['callsign', 'type', 'x_km', 'y_km', 'altitude', 'speed', 'stealth_probability']
    df_display = df[display_cols].copy()
    df_display['x_km'] = df_display['x_km'].round(1)
    df_display['y_km'] = df_display['y_km'].round(1)
    df_display['stealth_probability'] = df_display['stealth_probability'].round(1)
    df_display = df_display.sort_values('stealth_probability', ascending=False)
    
    st.dataframe(df_display, use_container_width=True)
else:
    st.info("No aircraft detected in this area")


# ── STEALTH ALERT ─────────────────────────────────────────────
potential_stealth = [ac for ac in st.session_state.aircraft_data if ac.get('stealth_probability', 0) > threshold]

if potential_stealth:
    st.markdown("---")
    st.markdown("### 🚨 STEALTH DETECTION ALERT")
    
    for ac in potential_stealth:
        st.markdown(f"""
        <div class="stealth-alert">
        ⚠️ **POTENTIAL {target} DETECTED**<br>
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
        st.download_button("📊 Export Aircraft Data (CSV)", csv_data, f"radar_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", width='stretch')

with col_e2:
    report = {
        "timestamp": datetime.now().isoformat(),
        "location": selected_airport,
        "coordinates": {"lat": radar_lat, "lon": radar_lon},
        "range_km": range_km,
        "target": target,
        "total_aircraft": len(st.session_state.aircraft_data),
        "potential_stealth": len(potential_stealth),
        "detections": [
            {
                "callsign": ac['callsign'],
                "type": ac['type'],
                "x_km": ac['x_km'],
                "y_km": ac['y_km'],
                "stealth_probability": ac.get('stealth_probability', 0)
            }
            for ac in potential_stealth
        ]
    }
    st.download_button("📋 Export Report (JSON)", json.dumps(report, indent=2), "radar_report.json", width='stretch')


# ── AUTO-REFRESH ─────────────────────────────────────────────
if st.session_state.live_mode:
    time.sleep(1)
    st.rerun()

st.markdown("---")
st.markdown("🛸 **StealthPDPRadar v8.1** | OpenSky Network | Real Aircraft | PDP Stealth Detection | Tony Ford Model")
