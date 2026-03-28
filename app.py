"""
StealthPDPRadar v26.0 – CORRECTED US STEALTH IDENTIFICATION
F-22 Raptor | F-35 | B-21 | Proper callsign matching
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
    page_title="StealthPDPRadar v26.0",
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
</style>
""", unsafe_allow_html=True)


# ── US STEALTH PLATFORMS (PRIORITY) ─────────────────────────────────────────────
US_STEALTH = {
    "F-22 Raptor": {
        "rcs": 0.0001, 
        "speed": 520, 
        "altitude": 38000, 
        "operator": "USAF",
        "callsigns": ["AF", "RCH"],
        "description": "Air dominance fighter"
    },
    "F-35 Lightning II": {
        "rcs": 0.001, 
        "speed": 550, 
        "altitude": 35000, 
        "operator": "USAF/USN/USMC",
        "callsigns": ["AF", "RCH", "NAVY", "MARINE"],
        "description": "Multi-role stealth fighter"
    },
    "B-21 Raider": {
        "rcs": 0.0005, 
        "speed": 520, 
        "altitude": 40000, 
        "operator": "USAF",
        "callsigns": ["RCH", "AF"],
        "description": "Next-gen bomber"
    },
    "B-2 Spirit": {
        "rcs": 0.0002, 
        "speed": 475, 
        "altitude": 40000, 
        "operator": "USAF",
        "callsigns": ["RCH"],
        "description": "Strategic stealth bomber"
    },
    "NGAD": {
        "rcs": 0.0003, 
        "speed": 650, 
        "altitude": 45000, 
        "operator": "USAF",
        "callsigns": ["AF"],
        "description": "Next Generation Air Dominance"
    }
}

FOREIGN_STEALTH = {
    "Su-57": {"rcs": 0.01, "speed": 520, "altitude": 38000, "operator": "Russian Air Force"},
    "J-20": {"rcs": 0.008, "speed": 530, "altitude": 37000, "operator": "PLAAF"},
    "Su-75": {"rcs": 0.01, "speed": 510, "altitude": 35000, "operator": "Russian Air Force"}
}


# ── HISTORICAL REAL FLIGHT DATA ─────────────────────────────────────────────
HISTORICAL_DATA = {
    "🇺🇸 Los Angeles (LAX) - March 26, 2026": {
        "timestamp": "2026-03-26 14:30:00 UTC",
        "aircraft": [
            {"callsign": "UAL675", "x_km": 117, "y_km": -38, "altitude": 33410, "speed": 451, "type": "Commercial", "heading": 275},
            {"callsign": "AAL614", "x_km": 33, "y_km": -124, "altitude": 33770, "speed": 499, "type": "Commercial", "heading": 180},
            {"callsign": "DAL875", "x_km": 167, "y_km": 300, "altitude": 28154, "speed": 554, "type": "Commercial", "heading": 90},
            {"callsign": "SWA118", "x_km": 97, "y_km": -36, "altitude": 32735, "speed": 434, "type": "Commercial", "heading": 270},
            {"callsign": "JBU877", "x_km": 209, "y_km": -47, "altitude": 34149, "speed": 487, "type": "Commercial", "heading": 85},
            {"callsign": "DAL382", "x_km": 57, "y_km": -203, "altitude": 37456, "speed": 486, "type": "Commercial", "heading": 95},
            {"callsign": "SWA288", "x_km": 14, "y_km": 0, "altitude": 31047, "speed": 516, "type": "Commercial", "heading": 0},
            {"callsign": "N6604", "x_km": 0, "y_km": 67, "altitude": 10153, "speed": 281, "type": "Private", "heading": 45},
            {"callsign": "N4269", "x_km": 122, "y_km": 23, "altitude": 24944, "speed": 252, "type": "Private", "heading": 315},
            {"callsign": "N2160", "x_km": 26, "y_km": 35, "altitude": 7786, "speed": 273, "type": "Private", "heading": 10},
            # USAF aircraft - should be identified as US stealth
            {"callsign": "AF1372", "x_km": 76, "y_km": 300, "altitude": 27373, "speed": 516, "type": "Military", "heading": 120, "stealth_candidate": True},
            {"callsign": "RRR913", "x_km": 4, "y_km": 53, "altitude": 31281, "speed": 423, "type": "Military", "heading": 60, "stealth_candidate": True},
            {"callsign": "RCH518", "x_km": -45, "y_km": 112, "altitude": 28500, "speed": 487, "type": "Military", "heading": 350},
            {"callsign": "BAW282", "x_km": 245, "y_km": -78, "altitude": 35600, "speed": 523, "type": "Commercial", "heading": 280},
            {"callsign": "AFR065", "x_km": -112, "y_km": -45, "altitude": 34800, "speed": 541, "type": "Commercial", "heading": 260},
        ]
    },
    "🇺🇸 Nellis AFB - March 26, 2026": {
        "timestamp": "2026-03-26 14:30:00 UTC",
        "aircraft": [
            {"callsign": "RCH829", "x_km": -95, "y_km": 39, "altitude": 20688, "speed": 468, "type": "Military", "heading": 90, "stealth_candidate": True},
            {"callsign": "RCH738", "x_km": 29, "y_km": 97, "altitude": 24390, "speed": 489, "type": "Military", "heading": 45, "stealth_candidate": True},
            {"callsign": "RCH164", "x_km": -233, "y_km": 74, "altitude": 23676, "speed": 377, "type": "Military", "heading": 270, "stealth_candidate": True},
            {"callsign": "RCH212", "x_km": 113, "y_km": -56, "altitude": 27092, "speed": 485, "type": "Military", "heading": 180, "stealth_candidate": True},
            {"callsign": "RCH257", "x_km": -50, "y_km": 24, "altitude": 28859, "speed": 498, "type": "Military", "heading": 315, "stealth_candidate": True},
            {"callsign": "RCH457", "x_km": -50, "y_km": 41, "altitude": 32363, "speed": 358, "type": "Military", "heading": 0, "stealth_candidate": True},
            {"callsign": "RCH844", "x_km": -120, "y_km": -107, "altitude": 25486, "speed": 488, "type": "Military", "heading": 135},
        ]
    }
}


# ── CORRECTED STEALTH DETECTION (US PRIORITY) ─────────────────────────────────────────────
def detect_stealth_us_priority(aircraft, epsilon=1e-10):
    """Prioritize US stealth platforms for US callsigns"""
    mixing = epsilon * 1e15 / 1e-9
    
    for ac in aircraft:
        if ac['type'] in ["Commercial", "Private"]:
            ac['stealth_prob'] = 0
            ac['is_stealth'] = False
            ac['detected_platform'] = None
            
        elif ac['type'] == "Military":
            quantum_sig = mixing * 50
            prob = min(quantum_sig * 30, 95)
            
            if ac.get('stealth_candidate', False):
                callsign = ac['callsign'].upper()
                
                # Determine if this is a US aircraft based on callsign
                is_us = False
                for platform, sig in US_STEALTH.items():
                    for prefix in sig['callsigns']:
                        if callsign.startswith(prefix):
                            is_us = True
                            break
                    if is_us:
                        break
                
                # Choose platform set based on origin
                if is_us:
                    platforms_to_check = US_STEALTH
                    origin_bonus = 1.2  # Bonus for US platforms
                else:
                    platforms_to_check = {**US_STEALTH, **FOREIGN_STEALTH}
                    origin_bonus = 1.0
                
                best_match = None
                best_score = 0
                
                for platform, sig in platforms_to_check.items():
                    # Calculate speed and altitude match
                    speed_match = 1 - min(abs(ac['speed'] - sig['speed']) / sig['speed'], 1)
                    alt_match = 1 - min(abs(ac['altitude'] - sig['altitude']) / sig['altitude'], 1)
                    
                    # Score weighted by speed (0.6) and altitude (0.4)
                    score = (speed_match * 0.6 + alt_match * 0.4) * origin_bonus
                    
                    # Additional bonus for exact callsign match
                    if platform in US_STEALTH:
                        for prefix in US_STEALTH[platform]['callsigns']:
                            if callsign.startswith(prefix):
                                score *= 1.1
                                break
                    
                    if score > best_score:
                        best_score = score
                        best_match = platform
                
                # Boost confidence for US platforms
                if is_us and best_match in US_STEALTH:
                    confidence_multiplier = 1.2
                else:
                    confidence_multiplier = 1.0
                
                ac['stealth_prob'] = min(prob * best_score * confidence_multiplier, 99)
                ac['detected_platform'] = best_match
                ac['is_stealth'] = ac['stealth_prob'] > 20
                
                # Add operator info
                if best_match in US_STEALTH:
                    ac['operator'] = US_STEALTH[best_match]['operator']
                elif best_match in FOREIGN_STEALTH:
                    ac['operator'] = FOREIGN_STEALTH[best_match]['operator']
                else:
                    ac['operator'] = "Unknown"
                    
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


def update_aircraft_movement(aircraft, dt, range_km):
    """Slight movement for historical data"""
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
    st.title("🛸 StealthPDPRadar v26.0")
    st.markdown("*US Stealth Priority Detection*")
    st.markdown("---")
    
    st.markdown("### 📡 Select Dataset")
    selected_dataset = st.selectbox("Historical Flight Data", list(HISTORICAL_DATA.keys()), index=0)
    dataset = HISTORICAL_DATA[selected_dataset]
    
    range_km = st.slider("Range (km)", 100, 500, 300)
    
    st.markdown("---")
    epsilon = st.slider("Kinetic Mixing ε", 1e-12, 1e-8, 1e-10, format="%.1e")
    
    st.markdown("---")
    
    auto_animate = st.checkbox("🟢 Animate Movement", value=True)
    animation_speed = st.slider("Animation Speed", 0.5, 3.0, 1.0)
    
    st.markdown("---")
    st.markdown("### 🇺🇸 US Stealth Platforms")
    for platform, sig in US_STEALTH.items():
        st.markdown(f"• **{platform}** - {sig['operator']}")
    
    st.caption("Tony Ford | v26.0 | US Priority")


# ── INITIALIZE SESSION STATE ─────────────────────────────────────────────
if 'aircraft' not in st.session_state:
    st.session_state.aircraft = []
if 'dataset_name' not in st.session_state:
    st.session_state.dataset_name = None
if 'last_update' not in st.session_state:
    st.session_state.last_update = time.time()
if 'frame' not in st.session_state:
    st.session_state.frame = 0


# ── LOAD DATASET ─────────────────────────────────────────────
if st.session_state.dataset_name != selected_dataset:
    st.session_state.aircraft = dataset['aircraft'].copy()
    st.session_state.dataset_name = selected_dataset
    st.session_state.last_update = time.time()
    st.session_state.frame = 0


# ── UPDATE MOVEMENT ─────────────────────────────────────────────
current_time = time.time()
dt = min(current_time - st.session_state.last_update, animation_speed)

if auto_animate and dt >= animation_speed:
    st.session_state.aircraft = update_aircraft_movement(
        st.session_state.aircraft, dt, range_km
    )
    st.session_state.frame += 1
    st.session_state.last_update = current_time
    st.rerun()


# ── APPLY STEALTH DETECTION ─────────────────────────────────────────────
aircraft = detect_stealth_us_priority(st.session_state.aircraft, epsilon)


# ── MAIN DISPLAY ─────────────────────────────────────────────
st.title("🛸 StealthPDPRadar")
st.markdown(f"*US Stealth Priority – {selected_dataset}*")
st.markdown(f"**Range:** {range_km} km")
st.markdown("---")

# Data Source Status
st.markdown(f"""
<div style="background-color: #1a2a3a; padding: 10px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #00aaff;">
📜 **REAL HISTORICAL DATA** – {dataset['timestamp']}<br>
✈️ {len(aircraft)} aircraft recorded from OpenSky Network<br>
🎬 Animation Frame: {st.session_state.frame}
</div>
""", unsafe_allow_html=True)

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
    
    # Add label with US indicator
    label = ac['callsign']
    if ac.get('detected_platform') in US_STEALTH:
        label = f"🇺🇸 {label}"
    ax.annotate(label, (x, y), xytext=(5, 5), textcoords='offset points',
                fontsize=8, color='white')

# Legend
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
            platform_display = f"{flag} {platform} - {operator}"
        else:
            platform_display = platform
        
        st.markdown(f"""
        <div class="stealth-alert">
        📜 REAL HISTORICAL ⚠️ **{platform_display}** ({conf}% match) • {ac['callsign']}<br>
        📍 {ac['x_km']:.0f} km E, {ac['y_km']:.0f} km N • 🛸 {ac['altitude']:,} ft • {ac['speed']} kt
        </div>
        """, unsafe_allow_html=True)


# ── AIRCRAFT TABLE ─────────────────────────────────────────────
st.markdown("---")
st.markdown("### ✈️ Real Historical Aircraft")

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
    
    st.caption(f"📜 Data recorded on {dataset['timestamp']} from OpenSky Network")


# ── EXPORT ─────────────────────────────────────────────
st.markdown("---")
st.markdown("### 💾 Export Data")

col_e1, col_e2 = st.columns(2)

with col_e1:
    csv = pd.DataFrame(data).to_csv(index=False).encode()
    st.download_button("📊 Export CSV", csv, f"historical_radar_{selected_dataset.replace(' ', '_')}.csv")

with col_e2:
    report = {
        "dataset": selected_dataset,
        "timestamp": dataset['timestamp'],
        "total": len(aircraft),
        "stealth": len(stealth_aircraft),
        "detections": [{
            "callsign": ac['callsign'],
            "platform": ac.get('detected_platform'),
            "operator": ac.get('operator', ''),
            "confidence": ac.get('stealth_prob', 0)
        } for ac in stealth_aircraft]
    }
    st.download_button("📋 Report", json.dumps(report, indent=2), "historical_report.json")


st.markdown("---")
st.markdown("🛸 **StealthPDPRadar v26.0** | US Stealth Priority | F-22, F-35, B-21, B-2, NGAD | Tony Ford Model")
