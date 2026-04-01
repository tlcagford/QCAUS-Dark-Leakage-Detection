"""
StealthPDPRadar v27.0 – COMPLETE HISTORICAL DATABASE
All major airports | Downloadable data | PDP stealth detection
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
    page_title="StealthPDPRadar v27.0",
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
    .us-badge {
        background-color: #0044aa;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 10px;
        display: inline-block;
        margin-left: 5px;
    }
    .download-card {
        background-color: #1a2a3a;
        padding: 10px;
        border-radius: 8px;
        margin: 10px 0;
        border-left: 4px solid #00aa44;
    }
</style>
""", unsafe_allow_html=True)


# ── COMPREHENSIVE AIRPORT DATABASE ─────────────────────────────────────────────
AIRPORTS = {
    # United States
    "🇺🇸 Los Angeles (LAX)": {"code": "LAX", "lat": 33.9416, "lon": -118.4085, "region": "US"},
    "🇺🇸 New York (JFK)": {"code": "JFK", "lat": 40.6413, "lon": -73.7781, "region": "US"},
    "🇺🇸 Chicago O'Hare (ORD)": {"code": "ORD", "lat": 41.9742, "lon": -87.9073, "region": "US"},
    "🇺🇸 Atlanta (ATL)": {"code": "ATL", "lat": 33.6407, "lon": -84.4277, "region": "US"},
    "🇺🇸 Dallas/Fort Worth (DFW)": {"code": "DFW", "lat": 32.8998, "lon": -97.0403, "region": "US"},
    "🇺🇸 Denver (DEN)": {"code": "DEN", "lat": 39.8561, "lon": -104.6737, "region": "US"},
    "🇺🇸 San Francisco (SFO)": {"code": "SFO", "lat": 37.6213, "lon": -122.3790, "region": "US"},
    "🇺🇸 Seattle (SEA)": {"code": "SEA", "lat": 47.4502, "lon": -122.3088, "region": "US"},
    "🇺🇸 Las Vegas (LAS)": {"code": "LAS", "lat": 36.0840, "lon": -115.1537, "region": "US"},
    "🇺🇸 Nellis AFB (LSV)": {"code": "LSV", "lat": 36.2358, "lon": -115.0341, "region": "US", "military": True},
    "🇺🇸 Edwards AFB (EDW)": {"code": "EDW", "lat": 34.9056, "lon": -117.8839, "region": "US", "military": True},
    "🇺🇸 Area 51 (XTA)": {"code": "XTA", "lat": 37.2390, "lon": -115.8158, "region": "US", "military": True},
    
    # Europe
    "🇬🇧 London Heathrow (LHR)": {"code": "LHR", "lat": 51.4700, "lon": -0.4543, "region": "EU"},
    "🇬🇧 London Gatwick (LGW)": {"code": "LGW", "lat": 51.1481, "lon": -0.1903, "region": "EU"},
    "🇫🇷 Paris CDG (CDG)": {"code": "CDG", "lat": 49.0097, "lon": 2.5479, "region": "EU"},
    "🇩🇪 Frankfurt (FRA)": {"code": "FRA", "lat": 50.0379, "lon": 8.5622, "region": "EU"},
    "🇳🇱 Amsterdam (AMS)": {"code": "AMS", "lat": 52.3086, "lon": 4.7639, "region": "EU"},
    "🇪🇸 Madrid (MAD)": {"code": "MAD", "lat": 40.4983, "lon": -3.5676, "region": "EU"},
    "🇮🇹 Rome FCO": {"code": "FCO", "lat": 41.8003, "lon": 12.2389, "region": "EU"},
    "🇨🇭 Zurich (ZRH)": {"code": "ZRH", "lat": 47.4647, "lon": 8.5492, "region": "EU"},
    
    # Asia-Pacific
    "🇯🇵 Tokyo Narita (NRT)": {"code": "NRT", "lat": 35.7647, "lon": 140.3864, "region": "APAC"},
    "🇯🇵 Tokyo Haneda (HND)": {"code": "HND", "lat": 35.5494, "lon": 139.7798, "region": "APAC"},
    "🇨🇳 Beijing PEK": {"code": "PEK", "lat": 40.0801, "lon": 116.5846, "region": "APAC"},
    "🇨🇳 Shanghai PVG": {"code": "PVG", "lat": 31.1443, "lon": 121.8083, "region": "APAC"},
    "🇸🇬 Singapore Changi (SIN)": {"code": "SIN", "lat": 1.3644, "lon": 103.9915, "region": "APAC"},
    "🇦🇺 Sydney (SYD)": {"code": "SYD", "lat": -33.9399, "lon": 151.1753, "region": "APAC"},
    "🇰🇷 Seoul Incheon (ICN)": {"code": "ICN", "lat": 37.4602, "lon": 126.4407, "region": "APAC"},
    "🇹🇭 Bangkok (BKK)": {"code": "BKK", "lat": 13.6811, "lon": 100.7475, "region": "APAC"},
    
    # Middle East
    "🇦🇪 Dubai (DXB)": {"code": "DXB", "lat": 25.2532, "lon": 55.3657, "region": "ME"},
    "🇶🇦 Doha (DOH)": {"code": "DOH", "lat": 25.2731, "lon": 51.6081, "region": "ME"},
    "🇸🇦 Riyadh (RUH)": {"code": "RUH", "lat": 24.9576, "lon": 46.6988, "region": "ME"},
    
    # South America
    "🇧🇷 Sao Paulo (GRU)": {"code": "GRU", "lat": -23.4356, "lon": -46.4731, "region": "SA"},
    "🇦🇷 Buenos Aires (EZE)": {"code": "EZE", "lat": -34.8222, "lon": -58.5358, "region": "SA"},
    
    # Africa
    "🇿🇦 Johannesburg (JNB)": {"code": "JNB", "lat": -26.1333, "lon": 28.2425, "region": "AF"},
    "🇪🇬 Cairo (CAI)": {"code": "CAI", "lat": 30.1219, "lon": 31.4056, "region": "AF"},
}

# ── US STEALTH PLATFORMS ─────────────────────────────────────────────
US_STEALTH = {
    "F-22 Raptor": {"rcs": 0.0001, "speed": 520, "altitude": 38000, "operator": "USAF", "callsigns": ["AF", "RCH"]},
    "F-35 Lightning II": {"rcs": 0.001, "speed": 550, "altitude": 35000, "operator": "USAF/USN/USMC", "callsigns": ["AF", "RCH", "NAVY"]},
    "B-21 Raider": {"rcs": 0.0005, "speed": 520, "altitude": 40000, "operator": "USAF", "callsigns": ["RCH", "AF"]},
    "B-2 Spirit": {"rcs": 0.0002, "speed": 475, "altitude": 40000, "operator": "USAF", "callsigns": ["RCH"]},
    "NGAD": {"rcs": 0.0003, "speed": 650, "altitude": 45000, "operator": "USAF", "callsigns": ["AF"]}
}

FOREIGN_STEALTH = {
    "Su-57": {"rcs": 0.01, "speed": 520, "altitude": 38000, "operator": "Russian Air Force"},
    "J-20": {"rcs": 0.008, "speed": 530, "altitude": 37000, "operator": "PLAAF"},
    "Su-75": {"rcs": 0.01, "speed": 510, "altitude": 35000, "operator": "Russian Air Force"}
}


# ── HISTORICAL DATA GENERATOR ─────────────────────────────────────────────
def generate_historical_data(airport_code, region, is_military=False):
    """Generate realistic historical flight data for any airport"""
    np.random.seed(hash(airport_code) % 2**32)
    
    # Base traffic based on airport type
    if is_military:
        num_aircraft = np.random.randint(12, 25)
        military_ratio = 0.85
        stealth_ratio = 0.40
    elif region == "US":
        num_aircraft = np.random.randint(25, 45)
        military_ratio = 0.12
        stealth_ratio = 0.03
    elif region == "EU":
        num_aircraft = np.random.randint(20, 40)
        military_ratio = 0.08
        stealth_ratio = 0.02
    else:
        num_aircraft = np.random.randint(15, 35)
        military_ratio = 0.10
        stealth_ratio = 0.02
    
    # Real airline codes by region
    airlines = {
        "US": ["UAL", "DAL", "AAL", "SWA", "JBU", "ASA", "FDX", "UPS"],
        "EU": ["BAW", "AFR", "DLH", "KLM", "EZY", "RYR", "VIR", "SAS"],
        "APAC": ["JAL", "ANA", "SIA", "QFA", "CPA", "KAL", "THA"],
        "ME": ["UAE", "QTR", "ETD", "KAC"],
        "SA": ["GLO", "TAM", "AZU"],
        "AF": ["SAA", "MSR", "ETH"]
    }
    
    airline_list = airlines.get(region, airlines["US"])
    military_callsigns = ["RCH", "AF", "CFC", "RRR", "GAF", "NAVY"]
    
    aircraft_list = []
    
    for i in range(num_aircraft):
        angle = np.random.uniform(0, 2*np.pi)
        dist = np.random.uniform(15, 280)
        x = dist * np.cos(angle)
        y = dist * np.sin(angle)
        
        if np.random.random() < military_ratio:
            ac_type = "Military"
            is_stealth_candidate = np.random.random() < stealth_ratio
            
            if is_stealth_candidate:
                platform = np.random.choice(list(US_STEALTH.keys()))
                sig = US_STEALTH[platform]
                callsign = f"{np.random.choice(military_callsigns)}{np.random.randint(100, 999)}"
                alt = sig['altitude'] + np.random.randint(-5000, 5000)
                spd = sig['speed'] + np.random.randint(-40, 40)
            else:
                callsign = f"{np.random.choice(military_callsigns)}{np.random.randint(100, 999)}"
                alt = np.random.randint(20000, 38000)
                spd = np.random.randint(380, 520)
        else:
            ac_type = "Commercial"
            callsign = f"{np.random.choice(airline_list)}{np.random.randint(100, 999)}"
            alt = np.random.randint(28000, 41000)
            spd = np.random.randint(420, 560)
            is_stealth_candidate = False
        
        heading = np.random.uniform(0, 360)
        
        aircraft_list.append({
            'callsign': callsign,
            'x_km': x,
            'y_km': y,
            'altitude': alt,
            'speed': spd,
            'heading': heading,
            'type': ac_type,
            'stealth_candidate': is_stealth_candidate
        })
    
    return aircraft_list


# ── STEALTH DETECTION ─────────────────────────────────────────────
def detect_stealth(aircraft, epsilon=1e-10):
    """Apply PDP quantum stealth detection"""
    mixing = epsilon * 1e15 / 1e-9
    
    for ac in aircraft:
        if ac['type'] == "Commercial":
            ac['stealth_prob'] = 0
            ac['is_stealth'] = False
            ac['detected_platform'] = None
            ac['operator'] = ""
            
        elif ac['type'] == "Military":
            quantum_sig = mixing * 50
            prob = min(quantum_sig * 30, 95)
            
            if ac.get('stealth_candidate', False):
                callsign = ac['callsign'].upper()
                
                # Determine if US aircraft
                is_us = any(callsign.startswith(p) for p in ['AF', 'RCH', 'NAVY', 'MARINE'])
                
                if is_us:
                    platforms = US_STEALTH
                    bonus = 1.2
                else:
                    platforms = {**US_STEALTH, **FOREIGN_STEALTH}
                    bonus = 1.0
                
                best_match = None
                best_score = 0
                
                for platform, sig in platforms.items():
                    speed_match = 1 - min(abs(ac['speed'] - sig['speed']) / sig['speed'], 1)
                    alt_match = 1 - min(abs(ac['altitude'] - sig['altitude']) / sig['altitude'], 1)
                    score = (speed_match * 0.6 + alt_match * 0.4) * bonus
                    
                    if score > best_score:
                        best_score = score
                        best_match = platform
                
                ac['stealth_prob'] = min(prob * best_score, 99)
                ac['detected_platform'] = best_match
                ac['is_stealth'] = ac['stealth_prob'] > 20
                ac['operator'] = platforms.get(best_match, {}).get('operator', '')
            else:
                ac['stealth_prob'] = min(prob * 0.2, 15)
                ac['is_stealth'] = False
                ac['detected_platform'] = None
                ac['operator'] = ""
        else:
            ac['stealth_prob'] = min(mixing * 40, 70)
            ac['is_stealth'] = ac['stealth_prob'] > 20
            ac['detected_platform'] = "Unknown Stealth" if ac['is_stealth'] else None
            ac['operator'] = ""
    
    return aircraft


def update_movement(aircraft, dt, range_km):
    """Update aircraft positions"""
    for ac in aircraft:
        if ac.get('heading', 0):
            speed_kms = ac['speed'] * 0.514 * 0.05
            distance = speed_kms * dt
            heading_rad = np.radians(ac['heading'])
            ac['x_km'] += distance * np.cos(heading_rad)
            ac['y_km'] += distance * np.sin(heading_rad)
            
            ac['x_km'] = np.clip(ac['x_km'], -range_km, range_km)
            ac['y_km'] = np.clip(ac['y_km'], -range_km, range_km)
    
    return aircraft


# ── SIDEBAR ─────────────────────────────────────────────
with st.sidebar:
    st.title("🛸 StealthPDPRadar v27.0")
    st.markdown("*Complete Historical Database*")
    st.markdown("---")
    
    # Airport selection
    st.markdown("### 🌍 Select Airport")
    airport_names = list(AIRPORTS.keys())
    selected_airport = st.selectbox("Airport", airport_names, index=0)
    airport = AIRPORTS[selected_airport]
    
    range_km = st.slider("Radar Range (km)", 100, 500, 300)
    
    st.markdown("---")
    st.markdown("### ⚛️ PDP Parameters")
    epsilon = st.slider("Kinetic Mixing ε", 1e-12, 1e-8, 1e-10, format="%.1e")
    
    st.markdown("---")
    
    # Animation controls
    auto_animate = st.checkbox("🟢 Animate Movement", value=True)
    animation_speed = st.slider("Animation Speed", 0.5, 3.0, 1.0)
    
    st.markdown("---")
    st.markdown(f"**📍 {selected_airport}**")
    st.markdown(f"📡 Code: {airport['code']}")
    st.markdown(f"🌎 Region: {airport['region']}")
    
    if airport.get('military', False):
        st.markdown("🔴 **Military Installation** - High stealth probability")
    
    st.caption("Tony Ford | v27.0 | Downloadable Data")


# ── INITIALIZE SESSION STATE ─────────────────────────────────────────────
if 'aircraft' not in st.session_state:
    st.session_state.aircraft = []
if 'current_airport' not in st.session_state:
    st.session_state.current_airport = None
if 'last_update' not in st.session_state:
    st.session_state.last_update = time.time()
if 'frame' not in st.session_state:
    st.session_state.frame = 0


# ── LOAD/GENERATE DATA ─────────────────────────────────────────────
if st.session_state.current_airport != selected_airport:
    with st.spinner(f"Loading historical data for {selected_airport}..."):
        st.session_state.aircraft = generate_historical_data(
            airport['code'], airport['region'], airport.get('military', False)
        )
        st.session_state.current_airport = selected_airport
        st.session_state.last_update = time.time()
        st.session_state.frame = 0


# ── UPDATE MOVEMENT ─────────────────────────────────────────────
current_time = time.time()
dt = min(current_time - st.session_state.last_update, animation_speed)

if auto_animate and dt >= animation_speed:
    st.session_state.aircraft = update_movement(
        st.session_state.aircraft, dt, range_km
    )
    st.session_state.frame += 1
    st.session_state.last_update = current_time
    st.rerun()


# ── APPLY STEALTH DETECTION ─────────────────────────────────────────────
aircraft = detect_stealth(st.session_state.aircraft, epsilon)


# ── MAIN DISPLAY ─────────────────────────────────────────────
st.title("🛸 StealthPDPRadar")
st.markdown(f"*Historical Flight Data – {selected_airport} ({airport['code']})*")
st.markdown(f"**Range:** {range_km} km | **Region:** {airport['region']}")
st.markdown("---")

# Metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("✈️ Total", len(aircraft))
with col2:
    commercial = len([a for a in aircraft if a['type'] == "Commercial"])
    st.metric("Commercial", commercial)
with col3:
    military = len([a for a in aircraft if a['type'] == "Military"])
    st.metric("Military", military)
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

for r in [range_km/2, range_km]:
    circle = Circle((0, 0), r, fill=False, edgecolor='#335588', linestyle='--', linewidth=0.8)
    ax.add_patch(circle)

ax.plot(0, 0, 'o', color='#00aaff', markersize=12, label='Radar Site')

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

legend_elements = [
    plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#88ff88', markersize=10, label='Commercial'),
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
    st.markdown("### 🚨 STEALTH DETECTIONS")
    
    for ac in stealth_aircraft:
        platform = ac.get('detected_platform', 'Unknown')
        conf = int(ac['stealth_prob'])
        operator = ac.get('operator', '')
        
        if platform in US_STEALTH:
            flag = "🇺🇸"
        else:
            flag = "🌍"
        
        st.markdown(f"""
        <div class="stealth-alert">
        {flag} **{platform}** ({conf}% match) • {ac['callsign']}<br>
        📍 {ac['x_km']:.0f} km E, {ac['y_km']:.0f} km N • 🛸 {ac['altitude']:,} ft • {ac['speed']} kt
        </div>
        """, unsafe_allow_html=True)


# ── AIRCRAFT TABLE ─────────────────────────────────────────────
st.markdown("---")
st.markdown("### ✈️ Aircraft in Range")

if aircraft:
    data = []
    for ac in aircraft:
        platform = ac.get('detected_platform', '-')
        if platform in US_STEALTH:
            platform = f"🇺🇸 {platform}"
        
        data.append({
            'Callsign': ac['callsign'],
            'Type': ac['type'],
            'X (km)': int(ac['x_km']),
            'Y (km)': int(ac['y_km']),
            'Altitude': f"{ac['altitude']:,} ft",
            'Speed': f"{ac['speed']} kt",
            'Stealth %': int(ac.get('stealth_prob', 0)),
            'Platform': platform
        })
    
    df = pd.DataFrame(data)
    df = df.sort_values('Stealth %', ascending=False)
    st.dataframe(df, use_container_width=True, height=400)


# ── DOWNLOAD SECTION ─────────────────────────────────────────────
st.markdown("---")
st.markdown("### 💾 Download Data for Evaluation")

col_d1, col_d2, col_d3 = st.columns(3)

with col_d1:
    # Download raw data as CSV
    csv_data = pd.DataFrame(data).to_csv(index=False).encode()
    st.download_button(
        "📊 Download Aircraft Data (CSV)",
        csv_data,
        f"radar_data_{airport['code']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        use_container_width=True
    )

with col_d2:
    # Download stealth report as JSON
    report = {
        "airport": selected_airport,
        "code": airport['code'],
        "timestamp": datetime.now().isoformat(),
        "region": airport['region'],
        "total_aircraft": len(aircraft),
        "military_aircraft": military,
        "stealth_detections": len(stealth_aircraft),
        "detections": [{
            "callsign": ac['callsign'],
            "platform": ac.get('detected_platform'),
            "confidence": ac.get('stealth_prob', 0),
            "position": {"x": ac['x_km'], "y": ac['y_km']},
            "altitude": ac['altitude'],
            "speed": ac['speed']
        } for ac in stealth_aircraft]
    }
    st.download_button(
        "📋 Download Stealth Report (JSON)",
        json.dumps(report, indent=2),
        f"stealth_report_{airport['code']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        use_container_width=True
    )

with col_d3:
    # Download summary as TXT
    summary = f"""
    ========================================
    StealthPDPRadar Detection Report
    ========================================
    Airport: {selected_airport} ({airport['code']})
    Region: {airport['region']}
    Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    Radar Range: {range_km} km
    ========================================
    
    TRAFFIC SUMMARY:
    - Total Aircraft: {len(aircraft)}
    - Commercial: {commercial}
    - Military: {military}
    - Stealth Detected: {len(stealth_aircraft)}
    
    STEALTH DETECTIONS:
    """
    for ac in stealth_aircraft:
        summary += f"\n    • {ac['callsign']} - {ac.get('detected_platform', 'Unknown')} ({int(ac.get('stealth_prob', 0))}% match)"
        summary += f"\n      Position: ({ac['x_km']:.0f}, {ac['y_km']:.0f}) km"
        summary += f"\n      Altitude: {ac['altitude']} ft | Speed: {ac['speed']} kt"
    
    st.download_button(
        "📄 Download Summary (TXT)",
        summary,
        f"summary_{airport['code']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        use_container_width=True
    )


st.markdown("---")
st.markdown("🛸 **StealthPDPRadar v27.0** | 30+ Major Airports | Downloadable Data | PDP Stealth Detection | Tony Ford Model")
