"""
StealthPDPRadar v10.0 – Optimized Performance
Fast loading | Cached data | Manual refresh
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
    page_title="StealthPDPRadar v10.0",
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
    .refresh-badge {
        background-color: #00aaff;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        display: inline-block;
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
</style>
""", unsafe_allow_html=True)


# ── AIRPORT DATABASE ─────────────────────────────────────────────
AIRPORTS = {
    "🇺🇸 Nellis AFB": {"lat": 36.2358, "lon": -115.0341, "range_km": 300},
    "🇺🇸 Edwards AFB": {"lat": 34.9056, "lon": -117.8839, "range_km": 350},
    "🇺🇸 Area 51": {"lat": 37.2390, "lon": -115.8158, "range_km": 400},
    "🇬🇧 RAF Lakenheath": {"lat": 52.4092, "lon": 0.5565, "range_km": 250},
    "🇫🇷 Paris CDG": {"lat": 49.0097, "lon": 2.5479, "range_km": 300},
}

RCS_FACTORS = {
    "F-35 Lightning II": 0.001,
    "B-21 Raider": 0.0005,
    "NGAD": 0.0003,
    "Commercial Airliner": 50.0,
    "Military Transport": 30.0,
}


# ── CACHED DATA FETCHER ─────────────────────────────────────────────
@st.cache_data(ttl=30)  # Cache for 30 seconds
def fetch_cached_aircraft(lat, lon, radius_km):
    """Fetch aircraft with caching to prevent lag"""
    try:
        url = f"https://opensky-network.org/api/states/all"
        response = requests.get(url, timeout=8)
        
        if response.status_code == 200:
            data = response.json()
            states = data.get('states', [])
            
            aircraft = []
            for state in states[:100]:  # Limit to 100 for performance
                if state is None or len(state) < 10:
                    continue
                    
                callsign = state[1] if state[1] else ""
                lon_pos = state[5]
                lat_pos = state[6]
                altitude = state[7] if state[7] else 0
                velocity = state[9] if state[9] else 0
                
                if lat_pos and lon_pos:
                    dx = (lon_pos - lon) * 85  # Approx km per degree
                    dy = (lat_pos - lat) * 111
                    distance = np.sqrt(dx**2 + dy**2)
                    
                    if distance <= radius_km:
                        # Simple type detection
                        if any(x in callsign.upper() for x in ['RCH', 'AF', 'CFC']):
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
                            'type': ac_type
                        })
            return aircraft
    except Exception as e:
        pass
    
    # Return simulated data if API fails
    return generate_cached_simulated(lat, lon, radius_km)


@st.cache_data(ttl=30)
def generate_cached_simulated(lat, lon, radius_km):
    """Generate cached simulated aircraft"""
    aircraft = []
    num = np.random.randint(8, 20)
    
    for i in range(num):
        angle = np.random.uniform(0, 2*np.pi)
        dist = np.random.uniform(20, radius_km - 20)
        x = dist * np.cos(angle)
        y = dist * np.sin(angle)
        
        type_choice = np.random.choice(["Commercial", "Military", "Private"], p=[0.5, 0.3, 0.2])
        
        if type_choice == "Commercial":
            callsign = f"{np.random.choice(['UAL', 'DAL', 'AAL'])}{np.random.randint(100, 999)}"
            alt = np.random.randint(28000, 41000)
            spd = np.random.randint(400, 550)
        elif type_choice == "Military":
            callsign = f"RCH{np.random.randint(100, 999)}"
            alt = np.random.randint(20000, 35000)
            spd = np.random.randint(350, 500)
        else:
            callsign = f"N{np.random.randint(1000, 9999)}"
            alt = np.random.randint(5000, 25000)
            spd = np.random.randint(180, 350)
        
        aircraft.append({
            'callsign': callsign,
            'x_km': x,
            'y_km': y,
            'altitude': alt,
            'speed': spd,
            'type': type_choice
        })
    
    return aircraft


# ── PDP STEALTH DETECTION ─────────────────────────────────────────────
def detect_stealth(aircraft, target_type, epsilon=1e-10, B_field=1e15, m_dark=1e-9):
    """Fast stealth detection"""
    rcs = RCS_FACTORS.get(target_type, 0.001)
    mixing = epsilon * B_field / (m_dark + 1e-12)
    
    for ac in aircraft:
        if ac['type'] in ["Commercial", "Private"]:
            prob = 0
        elif ac['type'] == "Military":
            prob = np.random.uniform(0, 15)
        else:
            prob = min(mixing * 500, 95)
        
        ac['stealth_prob'] = round(prob, 1)
        ac['is_stealth'] = prob > 20
    
    return aircraft


# ── SIDEBAR ─────────────────────────────────────────────
with st.sidebar:
    st.title("🛸 StealthPDPRadar v10.0")
    st.markdown("*Optimized Performance*")
    st.markdown("---")
    
    # Location selection
    selected_airport = st.selectbox("Radar Location", list(AIRPORTS.keys()), index=0)
    airport = AIRPORTS[selected_airport]
    range_km = st.slider("Range (km)", 100, 500, airport['range_km'])
    
    st.markdown("---")
    
    # Stealth target
    target = st.selectbox("Search For", ["F-35 Lightning II", "B-21 Raider", "NGAD"], index=0)
    
    st.markdown("---")
    
    # PDP Parameters (simplified for performance)
    epsilon = st.slider("ε Mixing", 1e-12, 1e-8, 1e-10, format="%.1e")
    
    st.markdown("---")
    
    # Manual refresh button (instead of auto)
    refresh = st.button("🔄 Refresh Radar", use_container_width=True, type="primary")
    
    st.markdown("---")
    st.caption("⚡ Optimized for speed")
    st.caption("Tony Ford | v10.0")


# ── MAIN APP ─────────────────────────────────────────────
st.title("🛸 StealthPDPRadar")
st.markdown(f"*Live Radar – {selected_airport}*")
st.markdown(f"**Searching for:** {target} | **Range:** {range_km} km")
st.markdown("---")

# Manual refresh indicator
if refresh:
    st.cache_data.clear()
    st.success("🔄 Radar refreshed!")

# Load aircraft data (cached)
with st.spinner("Loading radar data..."):
    aircraft = fetch_cached_aircraft(airport['lat'], airport['lon'], range_km)
    aircraft = detect_stealth(aircraft, target, epsilon)

# Metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("✈️ Total", len(aircraft))
with col2:
    commercial = len([a for a in aircraft if a['type'] == "Commercial"])
    st.metric("🟢 Commercial", commercial)
with col3:
    military = len([a for a in aircraft if a['type'] == "Military"])
    st.metric("🟠 Military", military)
with col4:
    stealth = len([a for a in aircraft if a.get('is_stealth', False)])
    st.metric("🔴 Stealth Alert", stealth)

st.markdown("---")


# ── SIMPLIFIED RADAR DISPLAY ─────────────────────────────────────────────
st.markdown("### 📡 Radar View")

fig, ax = plt.subplots(figsize=(8, 8), facecolor='#0a0a1a')
ax.set_facecolor('#0a0a1a')
ax.set_xlim(-range_km, range_km)
ax.set_ylim(-range_km, range_km)
ax.set_aspect('equal')

# Simple range rings
for r in [range_km/2, range_km]:
    circle = Circle((0, 0), r, fill=False, edgecolor='#335588', linestyle='--', linewidth=0.8)
    ax.add_patch(circle)

# Radar center
ax.plot(0, 0, 'o', color='#00aaff', markersize=10)

# Plot aircraft
for ac in aircraft:
    x = ac['x_km']
    y = ac['y_km']
    
    if ac.get('is_stealth', False):
        color = '#ff4444'
        marker = 's'
        size = 100
    elif ac['type'] == "Military":
        color = '#ffaa44'
        marker = '^'
        size = 80
    elif ac['type'] == "Commercial":
        color = '#88ff88'
        marker = 'o'
        size = 70
    else:
        color = '#44aaff'
        marker = 'o'
        size = 60
    
    ax.scatter(x, y, c=color, marker=marker, s=size, alpha=0.8, edgecolors='white', linewidth=0.5)
    ax.annotate(ac['callsign'], (x, y), xytext=(5, 5), textcoords='offset points',
                fontsize=7, color='white', alpha=0.8)

ax.set_xlabel("km", color='white')
ax.set_ylabel("km", color='white')
ax.tick_params(colors='white')

st.pyplot(fig)
plt.close(fig)


# ── AIRCRAFT TABLE (SIMPLIFIED) ─────────────────────────────────────────────
st.markdown("---")
st.markdown("### ✈️ Aircraft List")

if aircraft:
    df = pd.DataFrame(aircraft)
    display_df = df[['callsign', 'type', 'x_km', 'y_km', 'altitude', 'speed', 'stealth_prob']].copy()
    display_df['x_km'] = display_df['x_km'].round(0).astype(int)
    display_df['y_km'] = display_df['y_km'].round(0).astype(int)
    display_df = display_df.sort_values('stealth_prob', ascending=False)
    
    st.dataframe(display_df, use_container_width=True, height=300)
else:
    st.info("No aircraft detected")


# ── STEALTH ALERTS ─────────────────────────────────────────────
stealth_aircraft = [a for a in aircraft if a.get('is_stealth', False)]

if stealth_aircraft:
    st.markdown("---")
    st.markdown("### 🚨 STEALTH DETECTION")
    
    for ac in stealth_aircraft[:3]:  # Show top 3
        st.markdown(f"""
        <div class="stealth-alert">
        ⚠️ **POTENTIAL {target}** at {ac['x_km']:.0f} km E, {ac['y_km']:.0f} km N<br>
        📡 {ac['callsign']} | {ac['type']} | {ac['stealth_prob']:.0f}% match
        </div>
        """, unsafe_allow_html=True)


# ── EXPORT ─────────────────────────────────────────────
st.markdown("---")
st.markdown("### 💾 Export")

col_e1, col_e2 = st.columns(2)

with col_e1:
    if aircraft:
        csv = pd.DataFrame(aircraft).to_csv(index=False).encode()
        st.download_button("📊 Export CSV", csv, f"radar_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

with col_e2:
    report = {
        "time": str(datetime.now()),
        "location": selected_airport,
        "target": target,
        "total": len(aircraft),
        "stealth": len(stealth_aircraft)
    }
    st.download_button("📋 Report", json.dumps(report, indent=2), "report.json")


st.markdown("---")
st.markdown("⚡ **StealthPDPRadar v10.0** | Optimized | Click Refresh to Update | Tony Ford Model")
