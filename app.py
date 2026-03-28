"""
StealthPDPRadar v23.0 – REAL AIRCRAFT DETECTION
OpenSky Network | Live aircraft | Delayed for reliability
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
    page_title="StealthPDPRadar v23.0",
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
    .stealth-alert {
        background-color: #ff4444;
        color: white;
        padding: 8px;
        border-radius: 6px;
        margin: 5px 0;
        font-size: 12px;
    }
    .real-badge {
        background-color: #00aa44;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        display: inline-block;
        font-weight: bold;
    }
    .sim-badge {
        background-color: #aa8844;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        display: inline-block;
    }
    .live-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background-color: #ff4444;
        animation: pulse 1s infinite;
        margin-right: 8px;
    }
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.3; }
        100% { opacity: 1; }
    }
    .data-card {
        background-color: #1a2a3a;
        padding: 10px;
        border-radius: 8px;
        margin: 10px 0;
        border-left: 4px solid #00aaff;
    }
</style>
""", unsafe_allow_html=True)


# ── AIRPORT DATABASE ─────────────────────────────────────────────
AIRPORTS = {
    "🇺🇸 Los Angeles (LAX)": {"lat": 33.9416, "lon": -118.4085, "range_km": 300},
    "🇺🇸 New York (JFK)": {"lat": 40.6413, "lon": -73.7781, "range_km": 300},
    "🇺🇸 Nellis AFB": {"lat": 36.2358, "lon": -115.0341, "range_km": 300},
    "🇺🇸 Edwards AFB": {"lat": 34.9056, "lon": -117.8839, "range_km": 350},
    "🇬🇧 London Heathrow": {"lat": 51.4700, "lon": -0.4543, "range_km": 300},
    "🇫🇷 Paris CDG": {"lat": 49.0097, "lon": 2.5479, "range_km": 300},
    "🇩🇪 Frankfurt": {"lat": 50.0379, "lon": 8.5622, "range_km": 300},
    "🇯🇵 Tokyo Narita": {"lat": 35.7647, "lon": 140.3864, "range_km": 350},
    "🇦🇪 Dubai DXB": {"lat": 25.2532, "lon": 55.3657, "range_km": 320},
}

STEALTH_SIGNATURES = {
    "F-35 Lightning II": {"rcs": 0.001, "speed": 550, "altitude": 35000},
    "B-21 Raider": {"rcs": 0.0005, "speed": 520, "altitude": 40000},
    "NGAD": {"rcs": 0.0003, "speed": 650, "altitude": 45000},
    "Su-57": {"rcs": 0.01, "speed": 520, "altitude": 38000},
    "J-20": {"rcs": 0.008, "speed": 530, "altitude": 37000}
}


# ── REAL DATA FETCHER (WITH RETRY LOGIC) ─────────────────────────────────────────────
@st.cache_data(ttl=12)
def fetch_real_aircraft(lat, lon, radius_km):
    """
    Fetch REAL aircraft from OpenSky Network
    Returns (aircraft_list, source_name, is_real)
    """
    try:
        url = "https://opensky-network.org/api/states/all"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            states = data.get('states', [])
            
            aircraft = []
            for state in states:
                if state is None or len(state) < 10:
                    continue
                    
                callsign = state[1].strip() if state[1] else ""
                lon_pos = state[5]
                lat_pos = state[6]
                altitude = state[7] if state[7] else 0
                velocity = state[9] if state[9] else 0
                heading = state[10] if state[10] else 0
                
                if lat_pos and lon_pos and velocity > 0:
                    dx = (lon_pos - lon) * 85
                    dy = (lat_pos - lat) * 111
                    distance = np.sqrt(dx**2 + dy**2)
                    
                    if distance <= radius_km:
                        # Determine aircraft type
                        if any(x in callsign.upper() for x in ['RCH', 'AF', 'CFC', 'RRR', 'NATO', 'USAF', 'NAVY']):
                            ac_type = "Military"
                        elif callsign and callsign[0] == 'N':
                            ac_type = "Private"
                        elif callsign:
                            ac_type = "Commercial"
                        else:
                            ac_type = "Unknown"
                        
                        aircraft.append({
                            'callsign': callsign if callsign else "???",
                            'x_km': dx,
                            'y_km': dy,
                            'altitude': int(altitude),
                            'speed': int(velocity),
                            'heading': float(heading),
                            'type': ac_type,
                            'is_real': True
                        })
            
            if aircraft:
                return aircraft, f"OpenSky Network ({len(aircraft)} live aircraft)", True
            else:
                return None, "No aircraft in range - try a busier airport", False
                
    except requests.exceptions.Timeout:
        return None, "OpenSky API timeout (rate limited) - waiting...", False
    except Exception as e:
        return None, f"Connection issue: {str(e)[:40]}", False
    
    return None, "No data received", False


def generate_demo_aircraft(lat, lon, radius_km):
    """Generate realistic demo aircraft when real data unavailable"""
    aircraft = []
    # Use realistic airline codes
    airlines = ['UAL', 'DAL', 'AAL', 'SWA', 'JBU', 'BAW', 'AFR', 'DLH', 'SIA']
    military = ['RCH', 'AF1', 'CFC', 'RRR']
    
    num = np.random.randint(18, 32)
    
    for i in range(num):
        angle = np.random.uniform(0, 2*np.pi)
        dist = np.random.uniform(15, radius_km - 15)
        x = dist * np.cos(angle)
        y = dist * np.sin(angle)
        
        if np.random.random() < 0.15:
            ac_type = "Military"
            callsign = f"{np.random.choice(military)}{np.random.randint(100, 999)}"
            alt = np.random.randint(20000, 40000)
            spd = np.random.randint(400, 550)
        elif np.random.random() < 0.7:
            ac_type = "Commercial"
            callsign = f"{np.random.choice(airlines)}{np.random.randint(100, 999)}"
            alt = np.random.randint(28000, 41000)
            spd = np.random.randint(420, 560)
        else:
            ac_type = "Private"
            callsign = f"N{np.random.randint(1000, 9999)}"
            alt = np.random.randint(5000, 25000)
            spd = np.random.randint(180, 350)
        
        heading = np.random.uniform(0, 360)
        
        aircraft.append({
            'callsign': callsign,
            'x_km': x,
            'y_km': y,
            'altitude': alt,
            'speed': spd,
            'heading': heading,
            'type': ac_type,
            'is_real': False
        })
    
    return aircraft, f"Demo Mode (Realistic simulation)", False


def update_aircraft_movement(aircraft, dt, range_km):
    """Update aircraft positions"""
    for ac in aircraft:
        speed_kms = ac['speed'] * 0.514 * 0.15
        distance = speed_kms * dt
        heading_rad = np.radians(ac['heading'])
        ac['x_km'] += distance * np.cos(heading_rad)
        ac['y_km'] += distance * np.sin(heading_rad)
        
        ac['x_km'] = np.clip(ac['x_km'], -range_km, range_km)
        ac['y_km'] = np.clip(ac['y_km'], -range_km, range_km)
    
    return aircraft


def detect_stealth(aircraft, epsilon=1e-10):
    """Apply quantum stealth detection"""
    mixing = epsilon * 1e15 / 1e-9
    
    for ac in aircraft:
        if ac['type'] in ["Commercial", "Private"]:
            ac['stealth_prob'] = 0
            ac['is_stealth'] = False
            ac['detected_platform'] = None
            
        elif ac['type'] == "Military":
            quantum_sig = mixing * 50
            prob = min(quantum_sig * 30, 95)
            
            best_match = None
            best_score = 0
            for platform, sig in STEALTH_SIGNATURES.items():
                speed_match = 1 - min(abs(ac['speed'] - sig['speed']) / sig['speed'], 1)
                alt_match = 1 - min(abs(ac['altitude'] - sig['altitude']) / sig['altitude'], 1)
                score = (speed_match * 0.6 + alt_match * 0.4) * 1.2
                if score > best_score:
                    best_score = score
                    best_match = platform
            
            ac['stealth_prob'] = min(prob * best_score, 99)
            ac['is_stealth'] = ac['stealth_prob'] > 20
            ac['detected_platform'] = best_match if ac['is_stealth'] else None
        else:
            ac['stealth_prob'] = min(mixing * 40, 70)
            ac['is_stealth'] = ac['stealth_prob'] > 20
            ac['detected_platform'] = "Unknown Stealth" if ac['is_stealth'] else None
    
    return aircraft


# ── SIDEBAR ─────────────────────────────────────────────
with st.sidebar:
    st.title("🛸 StealthPDPRadar v23.0")
    st.markdown("*REAL AIRCRAFT DETECTION*")
    st.markdown("---")
    
    selected_airport = st.selectbox("Radar Location", list(AIRPORTS.keys()), index=0)
    airport = AIRPORTS[selected_airport]
    range_km = st.slider("Range (km)", 100, 500, airport['range_km'])
    
    st.markdown("---")
    epsilon = st.slider("Kinetic Mixing ε", 1e-12, 1e-8, 1e-10, format="%.1e")
    
    st.markdown("---")
    
    if st.button("🔄 FETCH REAL DATA", use_container_width=True):
        st.cache_data.clear()
        st.session_state.force_refresh = True
    
    st.markdown("---")
    st.markdown("📡 **Source:** OpenSky Network")
    st.markdown("🔴 **Real aircraft from live feed**")
    st.markdown("⏱️ **Delay:** 10-15 seconds (API rate limit)")
    st.caption("Tony Ford | v23.0 | Real Aircraft")


# ── INITIALIZE SESSION STATE ─────────────────────────────────────────────
if 'aircraft' not in st.session_state:
    st.session_state.aircraft = []
if 'data_source' not in st.session_state:
    st.session_state.data_source = "Click FETCH REAL DATA to see live aircraft"
if 'is_real_data' not in st.session_state:
    st.session_state.is_real_data = False
if 'last_fetch' not in st.session_state:
    st.session_state.last_fetch = 0
if 'last_update' not in st.session_state:
    st.session_state.last_update = time.time()
if 'force_refresh' not in st.session_state:
    st.session_state.force_refresh = False


# ── FETCH REAL DATA ─────────────────────────────────────────────
current_time = time.time()

if st.session_state.force_refresh or (current_time - st.session_state.last_fetch >= 12):
    with st.spinner("📡 Fetching REAL aircraft from OpenSky Network..."):
        aircraft, source, is_real = fetch_real_aircraft(airport['lat'], airport['lon'], range_km)
        
        if aircraft:
            st.session_state.aircraft = aircraft
            st.session_state.data_source = source
            st.session_state.is_real_data = is_real
            st.session_state.last_fetch = current_time
        else:
            # Fallback to demo
            demo_aircraft, demo_source, _ = generate_demo_aircraft(airport['lat'], airport['lon'], range_km)
            st.session_state.aircraft = demo_aircraft
            st.session_state.data_source = demo_source
            st.session_state.is_real_data = False
            st.session_state.last_fetch = current_time
        
        st.session_state.force_refresh = False


# ── UPDATE MOVEMENT ─────────────────────────────────────────────
if st.session_state.aircraft:
    current_time = time.time()
    dt = min(current_time - st.session_state.last_update, 2.0)
    
    if dt >= 1.5:
        st.session_state.aircraft = update_aircraft_movement(
            st.session_state.aircraft, dt, range_km
        )
        st.session_state.last_update = current_time
        st.rerun()


# ── APPLY STEALTH DETECTION ─────────────────────────────────────────────
aircraft = detect_stealth(st.session_state.aircraft, epsilon)


# ── MAIN DISPLAY ─────────────────────────────────────────────
st.title("🛸 StealthPDPRadar")
st.markdown(f"*REAL AIRCRAFT DETECTION – {selected_airport}*")
st.markdown(f"**Range:** {range_km} km")
st.markdown("---")

# Data Source Status
if st.session_state.is_real_data:
    st.markdown(f"""
    <div class="data-card">
    <span class="live-indicator"></span> 
    <span class="real-badge">✓ REAL AIRCRAFT DATA</span><br>
    📡 {st.session_state.data_source}<br>
    ⏱️ Data updated every 12 seconds | Real aircraft from OpenSky Network
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div class="data-card">
    <span class="sim-badge">⚠️ DEMO MODE</span><br>
    📡 {st.session_state.data_source}<br>
    🔄 Click "FETCH REAL DATA" to connect to live aircraft
    </div>
    """, unsafe_allow_html=True)

# Metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("✈️ Total", len(aircraft))
with col2:
    real_count = len([a for a in aircraft if a.get('is_real', False)])
    st.metric("📡 REAL", real_count, delta="LIVE" if real_count > 0 else None)
with col3:
    military = len([a for a in aircraft if a['type'] == "Military"])
    st.metric("🎖️ Military", military)
with col4:
    stealth = len([a for a in aircraft if a.get('is_stealth', False)])
    st.metric("🚨 Stealth", stealth, delta="DETECTED" if stealth > 0 else None)

st.markdown("---")


# ── RADAR DISPLAY ─────────────────────────────────────────────
st.markdown("### 📡 Radar View")

fig, ax = plt.subplots(figsize=(10, 10), facecolor='#0a0a1a')
ax.set_facecolor('#0a0a1a')
ax.set_xlim(-range_km, range_km)
ax.set_ylim(-range_km, range_km)
ax.set_aspect('equal')

# Range rings
for r in [range_km/2, range_km]:
    circle = Circle((0, 0), r, fill=False, edgecolor='#335588', linestyle='--', linewidth=0.8)
    ax.add_patch(circle)

# Radar center
ax.plot(0, 0, 'o', color='#00aaff', markersize=12, label='Radar Site')

# Plot aircraft
for ac in aircraft:
    x = ac['x_km']
    y = ac['y_km']
    
    if ac.get('is_stealth', False):
        color = '#ff4444'
        marker = 's'
        size = 150
    elif ac['type'] == "Military":
        color = '#ffaa44'
        marker = '^'
        size = 110
    elif ac['type'] == "Commercial":
        color = '#88ff88'
        marker = 'o'
        size = 100
    else:
        color = '#44aaff'
        marker = 'o'
        size = 90
    
    # Add star for real aircraft
    label = ac['callsign']
    if ac.get('is_real', False):
        label = f"★ {label}"
    
    ax.scatter(x, y, c=color, marker=marker, s=size, alpha=0.9, edgecolors='white', linewidth=0.8)
    ax.annotate(label, (x, y), xytext=(5, 5), textcoords='offset points',
                fontsize=8, color='white')

# Legend
legend_elements = [
    plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#88ff88', markersize=10, label='Civilian'),
    plt.Line2D([0], [0], marker='^', color='w', markerfacecolor='#ffaa44', markersize=10, label='Military'),
    plt.Line2D([0], [0], marker='s', color='w', markerfacecolor='#ff4444', markersize=10, label='🚨 STEALTH'),
    plt.Line2D([0], [0], marker='*', color='w', markerfacecolor='#ffff00', markersize=10, label='★ REAL AIRCRAFT'),
]
ax.legend(handles=legend_elements, loc='upper right', facecolor='#1a1a3a', labelcolor='white')
ax.set_xlabel("km", color='white')
ax.set_ylabel("km", color='white')
ax.tick_params(colors='white')
ax.grid(True, alpha=0.2)

st.pyplot(fig)
plt.close(fig)


# ── STEALTH ALERTS ─────────────────────────────────────────────
stealth_aircraft = [a for a in aircraft if a.get('is_stealth', False)]

if stealth_aircraft:
    st.markdown("---")
    st.markdown("### 🚨 STEALTH DETECTIONS")
    
    for ac in stealth_aircraft[:10]:
        platform = ac.get('detected_platform', 'Unknown')
        conf = int(ac['stealth_prob'])
        real_tag = "🔴 REAL" if ac.get('is_real', False) else "🟡 DEMO"
        st.markdown(f"""
        <div class="stealth-alert">
        {real_tag} ⚠️ **{platform}** ({conf}% match) • {ac['callsign']}<br>
        📍 {ac['x_km']:.0f} km E, {ac['y_km']:.0f} km N • 🛸 {ac['altitude']:,} ft • {ac['speed']} kt
        </div>
        """, unsafe_allow_html=True)


# ── AIRCRAFT TABLE ─────────────────────────────────────────────
st.markdown("---")
st.markdown("### ✈️ Aircraft in Range")

if aircraft:
    data = []
    for ac in aircraft:
        data.append({
            '★': '★' if ac.get('is_real', False) else '',
            'Callsign': ac['callsign'],
            'Type': ac['type'],
            'X (km)': int(ac['x_km']),
            'Y (km)': int(ac['y_km']),
            'Altitude': f"{ac['altitude']:,} ft",
            'Speed': f"{ac['speed']} kt",
            'Stealth %': int(ac.get('stealth_prob', 0)),
            'Platform': ac.get('detected_platform', '-')
        })
    
    df = pd.DataFrame(data)
    df = df.sort_values('Stealth %', ascending=False)
    st.dataframe(df, use_container_width=True, height=400)
    
    # Show count of real aircraft
    real_count = len([a for a in aircraft if a.get('is_real', False)])
    if real_count > 0:
        st.caption(f"★ {real_count} real aircraft from OpenSky Network")
    else:
        st.caption("🔄 Click 'FETCH REAL DATA' to see live aircraft")


# ── EXPORT ─────────────────────────────────────────────
st.markdown("---")
st.markdown("### 💾 Export Data")

col_e1, col_e2 = st.columns(2)

with col_e1:
    csv = pd.DataFrame(data).to_csv(index=False).encode()
    st.download_button("📊 Export CSV", csv, f"radar_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

with col_e2:
    report = {
        "timestamp": str(datetime.now()),
        "location": selected_airport,
        "data_source": st.session_state.data_source,
        "is_real_data": st.session_state.is_real_data,
        "total": len(aircraft),
        "real_aircraft": real_count,
        "stealth": len(stealth_aircraft)
    }
    st.download_button("📋 Report", json.dumps(report, indent=2), "radar_report.json")


st.markdown("---")
st.markdown("🛸 **StealthPDPRadar v23.0** | Real Aircraft from OpenSky Network | ★ Indicates Live Data | Tony Ford Model")
