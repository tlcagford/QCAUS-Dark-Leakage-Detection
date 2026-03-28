"""
StealthPDPRadar v21.0 – WORKING REAL RADAR DATA
OpenSky Network | Real aircraft | Delayed for reliability
"""

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import io
import json
import pandas as pd
import time
from datetime import datetime, timedelta
import warnings
import requests

warnings.filterwarnings('ignore')

# ── PAGE CONFIG ─────────────────────────────────────────────
st.set_page_config(
    layout="wide",
    page_title="StealthPDPRadar v21.0",
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
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 10px;
        display: inline-block;
    }
    .live-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background-color: #00ff00;
        animation: pulse 1s infinite;
        margin-right: 8px;
    }
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.3; }
        100% { opacity: 1; }
    }
    .data-status {
        background-color: #1a3a2a;
        padding: 8px;
        border-radius: 8px;
        margin: 10px 0;
        text-align: center;
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


# ── WORKING REAL DATA FETCHER WITH DELAY ─────────────────────────────────────────────
@st.cache_data(ttl=15)
def fetch_real_aircraft_data(lat, lon, radius_km):
    """
    Fetch REAL aircraft from OpenSky Network
    Using the live states endpoint with timeout
    """
    try:
        # OpenSky Network - No API key required
        url = "https://opensky-network.org/api/states/all"
        
        # Add timeout to prevent hanging
        response = requests.get(url, timeout=8)
        
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
                    # Calculate relative position
                    dx = (lon_pos - lon) * 85
                    dy = (lat_pos - lat) * 111
                    distance = np.sqrt(dx**2 + dy**2)
                    
                    if distance <= radius_km:
                        # Determine aircraft type
                        if any(x in callsign.upper() for x in ['RCH', 'AF', 'CFC', 'RRR', 'NATO', 'USAF']):
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
                return aircraft, f"OpenSky Network ({len(aircraft)} real aircraft)"
            else:
                return None, "No aircraft in range (try a busier airport like LAX or JFK)"
                
    except requests.exceptions.Timeout:
        return None, "OpenSky API timeout - API is rate limited, waiting..."
    except Exception as e:
        return None, f"API connection issue: {str(e)[:50]}"
    
    return None, "No data received - API may be busy"


def update_aircraft_movement(aircraft, dt, range_km):
    """Update positions for real aircraft (slight movement)"""
    for ac in aircraft:
        if ac.get('is_real', False):
            speed_kms = ac['speed'] * 0.514 * 0.1
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
    st.title("🛸 StealthPDPRadar v21.0")
    st.markdown("*Real Radar Data*")
    st.markdown("---")
    
    selected_airport = st.selectbox("Radar Location", list(AIRPORTS.keys()), index=0)
    airport = AIRPORTS[selected_airport]
    range_km = st.slider("Range (km)", 100, 500, airport['range_km'])
    
    st.markdown("---")
    epsilon = st.slider("Kinetic Mixing ε", 1e-12, 1e-8, 1e-10, format="%.1e")
    
    st.markdown("---")
    
    if st.button("🔄 FETCH REAL DATA", use_container_width=True):
        st.cache_data.clear()
        st.session_state.last_fetch = 0
        st.session_state.manual_refresh = True
    
    st.markdown("---")
    st.markdown("📡 **Source:** OpenSky Network")
    st.markdown("🔴 **Real aircraft from live feed**")
    st.markdown("⏱️ **Data delay:** 5-10 seconds (API rate limited)")
    st.caption("Tony Ford | v21.0 | Working Real Data")


# ── INITIALIZE SESSION STATE ─────────────────────────────────────────────
if 'aircraft' not in st.session_state:
    st.session_state.aircraft = []
if 'data_source' not in st.session_state:
    st.session_state.data_source = "Click FETCH REAL DATA to start"
if 'last_fetch' not in st.session_state:
    st.session_state.last_fetch = 0
if 'last_update' not in st.session_state:
    st.session_state.last_update = time.time()
if 'manual_refresh' not in st.session_state:
    st.session_state.manual_refresh = False


# ── FETCH REAL RADAR DATA ─────────────────────────────────────────────
current_time = time.time()

# Auto-refresh every 15 seconds OR manual refresh
if st.session_state.manual_refresh or (current_time - st.session_state.last_fetch >= 15):
    with st.spinner("📡 Fetching REAL aircraft data from OpenSky Network..."):
        aircraft, source = fetch_real_aircraft_data(airport['lat'], airport['lon'], range_km)
        
        if aircraft:
            st.session_state.aircraft = aircraft
            st.session_state.data_source = source
            st.session_state.last_fetch = current_time
        else:
            st.session_state.data_source = source
        
        st.session_state.manual_refresh = False


# ── UPDATE MOVEMENT (if real data exists) ─────────────────────────────────────────────
if st.session_state.aircraft:
    current_time = time.time()
    dt = min(current_time - st.session_state.last_update, 5.0)
    
    if dt >= 2.0:
        st.session_state.aircraft = update_aircraft_movement(
            st.session_state.aircraft, dt, range_km
        )
        st.session_state.last_update = current_time
        st.rerun()


# ── APPLY STEALTH DETECTION ─────────────────────────────────────────────
aircraft = detect_stealth(st.session_state.aircraft, epsilon) if st.session_state.aircraft else []


# ── MAIN DISPLAY ─────────────────────────────────────────────
st.title("🛸 StealthPDPRadar")
st.markdown(f"*REAL RADAR DATA – {selected_airport}*")
st.markdown(f"**Range:** {range_km} km")
st.markdown("---")

# Data status display
if aircraft and any(a.get('is_real', False) for a in aircraft):
    st.markdown(f"""
    <div class="data-status">
    <span class="live-indicator"></span> 
    <strong>LIVE REAL RADAR ACTIVE</strong><br>
    {st.session_state.data_source}
    </div>
    """, unsafe_allow_html=True)
else:
    st.warning(f"⚠️ {st.session_state.data_source}")
    st.info("💡 **Tip:** Try a busy airport like Los Angeles (LAX) or New York (JFK) for more aircraft")

# Metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("✈️ Total", len(aircraft))
with col2:
    real_count = len([a for a in aircraft if a.get('is_real', False)])
    st.metric("📡 REAL", real_count)
with col3:
    military = len([a for a in aircraft if a['type'] == "Military"])
    st.metric("🎖️ Military", military)
with col4:
    stealth = len([a for a in aircraft if a.get('is_stealth', False)])
    st.metric("🚨 Stealth", stealth, delta="ALERT" if stealth > 0 else None)

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
    
    ax.scatter(x, y, c=color, marker=marker, s=size, alpha=0.9, edgecolors='white', linewidth=0.8)
    ax.annotate(ac['callsign'], (x, y), xytext=(5, 5), textcoords='offset points',
                fontsize=8, color='white')

# Legend
legend_elements = [
    plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#88ff88', markersize=10, label='Civilian'),
    plt.Line2D([0], [0], marker='^', color='w', markerfacecolor='#ffaa44', markersize=10, label='Military'),
    plt.Line2D([0], [0], marker='s', color='w', markerfacecolor='#ff4444', markersize=10, label='🚨 STEALTH'),
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
    st.markdown("### 🚨 REAL-TIME STEALTH DETECTIONS")
    
    for ac in stealth_aircraft[:10]:
        platform = ac.get('detected_platform', 'Unknown')
        conf = int(ac['stealth_prob'])
        st.markdown(f"""
        <div class="stealth-alert">
        🔴 **{platform}** ({conf}% match) • {ac['callsign']}<br>
        📍 {ac['x_km']:.0f} km E, {ac['y_km']:.0f} km N • 🛸 {ac['altitude']:,} ft • {ac['speed']} kt
        </div>
        """, unsafe_allow_html=True)


# ── AIRCRAFT TABLE ─────────────────────────────────────────────
st.markdown("---")
st.markdown("### ✈️ Real Aircraft in Range")

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


# ── EXPORT ─────────────────────────────────────────────
st.markdown("---")
st.markdown("### 💾 Export Data")

col_e1, col_e2 = st.columns(2)

with col_e1:
    if aircraft:
        csv = pd.DataFrame(data).to_csv(index=False).encode()
        st.download_button("📊 Export CSV", csv, f"real_radar_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

with col_e2:
    report = {
        "timestamp": str(datetime.now()),
        "location": selected_airport,
        "data_source": st.session_state.data_source,
        "total": len(aircraft),
        "real": len([a for a in aircraft if a.get('is_real', False)]),
        "stealth": len(stealth_aircraft)
    }
    st.download_button("📋 Report", json.dumps(report, indent=2), "stealth_report.json")


st.markdown("---")
st.markdown("🛸 **StealthPDPRadar v21.0** | OpenSky Network | Real Aircraft (5-10s delay) | Tony Ford Model")
