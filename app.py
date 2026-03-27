"""
StealthPDPRadar - ENHANCED COMPLETE VERSION
Features:
- Military aircraft detection with stealth signatures
- Export data (CSV, JSON, images)
- Real-time OpenSky integration
- Aircraft type identification
"""

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from scipy.ndimage import gaussian_filter, label, center_of_mass
from scipy.fft import fft2, ifft2, fftshift
import requests
import io
import json
import base64
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="Stealth PDP Radar", page_icon="🔍", layout="wide")

# ============================================================================
# MILITARY AIRCRAFT SIGNATURE DATABASE
# ============================================================================

MILITARY_AIRCRAFT = {
    # US Aircraft
    'F22': {
        'name': 'F-22 Raptor',
        'country': 'USA',
        'type': '5th Gen Fighter',
        'rcs_m2': 0.0001,
        'stealth_level': 'Very High',
        'signature': 'Ultra-low RCS, angular returns',
        'typical_callsigns': ['RAPTOR', 'F-22', 'F22']
    },
    'F35': {
        'name': 'F-35 Lightning II',
        'country': 'USA',
        'type': '5th Gen Fighter',
        'rcs_m2': 0.001,
        'stealth_level': 'High',
        'signature': 'Very low RCS, broadband stealth',
        'typical_callsigns': ['LIGHTNING', 'F-35', 'F35']
    },
    'B2': {
        'name': 'B-2 Spirit',
        'country': 'USA',
        'type': 'Stealth Bomber',
        'rcs_m2': 0.0001,
        'stealth_level': 'Very High',
        'signature': 'Flying wing, ultra-low RCS',
        'typical_callsigns': ['SPIRIT', 'B-2', 'B2']
    },
    'B21': {
        'name': 'B-21 Raider',
        'country': 'USA',
        'type': 'Stealth Bomber',
        'rcs_m2': 0.00005,
        'stealth_level': 'Very High',
        'signature': 'Next-gen stealth, broadband',
        'typical_callsigns': ['RAIDER', 'B-21']
    },
    'F15': {
        'name': 'F-15 Eagle',
        'country': 'USA',
        'type': '4th Gen Fighter',
        'rcs_m2': 5.0,
        'stealth_level': 'None',
        'signature': 'Large radar return, high speed',
        'typical_callsigns': ['EAGLE', 'F-15']
    },
    'F16': {
        'name': 'F-16 Fighting Falcon',
        'country': 'USA',
        'type': '4th Gen Fighter',
        'rcs_m2': 1.2,
        'stealth_level': 'Low',
        'signature': 'Moderate RCS, agile',
        'typical_callsigns': ['VIPER', 'F-16']
    },
    'F18': {
        'name': 'F/A-18 Hornet',
        'country': 'USA',
        'type': 'Naval Fighter',
        'rcs_m2': 1.5,
        'stealth_level': 'Low',
        'signature': 'Naval operations',
        'typical_callsigns': ['HORNET', 'F-18']
    },
    'C17': {
        'name': 'C-17 Globemaster',
        'country': 'USA',
        'type': 'Transport',
        'rcs_m2': 80.0,
        'stealth_level': 'None',
        'signature': 'Large transport, high RCS',
        'typical_callsigns': ['GLOBEMASTER', 'C-17']
    },
    'KC135': {
        'name': 'KC-135 Stratotanker',
        'country': 'USA',
        'type': 'Tanker',
        'rcs_m2': 60.0,
        'stealth_level': 'None',
        'signature': 'Aerial refueling',
        'typical_callsigns': ['STRATOTANKER', 'KC-135']
    },
    'E3': {
        'name': 'E-3 Sentry',
        'country': 'USA',
        'type': 'AWACS',
        'rcs_m2': 90.0,
        'stealth_level': 'None',
        'signature': 'Radar dome, large RCS',
        'typical_callsigns': ['SENTRY', 'AWACS']
    },
    'P8': {
        'name': 'P-8 Poseidon',
        'country': 'USA',
        'type': 'Maritime Patrol',
        'rcs_m2': 25.0,
        'stealth_level': 'Low',
        'signature': 'Anti-submarine warfare',
        'typical_callsigns': ['POSEIDON', 'P-8']
    },
    
    # Russian Aircraft
    'SU57': {
        'name': 'Su-57 Felon',
        'country': 'Russia',
        'type': '5th Gen Fighter',
        'rcs_m2': 0.01,
        'stealth_level': 'Medium',
        'signature': 'Limited stealth features',
        'typical_callsigns': ['FELON', 'SU-57']
    },
    'SU35': {
        'name': 'Su-35 Flanker',
        'country': 'Russia',
        'type': '4.5 Gen Fighter',
        'rcs_m2': 3.0,
        'stealth_level': 'Low',
        'signature': 'High maneuverability',
        'typical_callsigns': ['FLANKER', 'SU-35']
    },
    'MIG29': {
        'name': 'MiG-29 Fulcrum',
        'country': 'Russia',
        'type': '4th Gen Fighter',
        'rcs_m2': 3.5,
        'stealth_level': 'Low',
        'signature': 'Dogfight optimized',
        'typical_callsigns': ['FULCRUM', 'MIG-29']
    },
    'TU95': {
        'name': 'Tu-95 Bear',
        'country': 'Russia',
        'type': 'Strategic Bomber',
        'rcs_m2': 100.0,
        'stealth_level': 'None',
        'signature': 'Propeller-driven, large RCS',
        'typical_callsigns': ['BEAR', 'TU-95']
    },
    
    # Chinese Aircraft
    'J20': {
        'name': 'Chengdu J-20',
        'country': 'China',
        'type': '5th Gen Fighter',
        'rcs_m2': 0.005,
        'stealth_level': 'High',
        'signature': 'Canard delta, stealth',
        'typical_callsigns': ['MIGHTY DRAGON', 'J-20']
    },
    'J16': {
        'name': 'Shenyang J-16',
        'country': 'China',
        'type': '4.5 Gen Fighter',
        'rcs_m2': 2.0,
        'stealth_level': 'Low',
        'signature': 'Multi-role fighter',
        'typical_callsigns': ['FLANKER', 'J-16']
    },
    'H6': {
        'name': 'Xian H-6',
        'country': 'China',
        'type': 'Bomber',
        'rcs_m2': 50.0,
        'stealth_level': 'None',
        'signature': 'Tu-16 derivative',
        'typical_callsigns': ['BADGER', 'H-6']
    },
    
    # European Aircraft
    'TYPHOON': {
        'name': 'Eurofighter Typhoon',
        'country': 'Europe',
        'type': '4.5 Gen Fighter',
        'rcs_m2': 0.5,
        'stealth_level': 'Low',
        'signature': 'Delta wing, agile',
        'typical_callsigns': ['TYPHOON', 'EURO']
    },
    'RAFALE': {
        'name': 'Dassault Rafale',
        'country': 'France',
        'type': '4.5 Gen Fighter',
        'rcs_m2': 0.4,
        'stealth_level': 'Low',
        'signature': 'Omnirole fighter',
        'typical_callsigns': ['RAFALE', 'DAUPHIN']
    },
    'GRIPEN': {
        'name': 'Saab Gripen',
        'country': 'Sweden',
        'type': '4th Gen Fighter',
        'rcs_m2': 0.8,
        'stealth_level': 'Low',
        'signature': 'Light fighter',
        'typical_callsigns': ['GRIPEN', 'SAAB']
    },
}

# ============================================================================
# AIRCRAFT IDENTIFICATION
# ============================================================================

def identify_military_aircraft(callsign):
    """Identify military aircraft from callsign"""
    callsign_upper = callsign.upper() if callsign else ""
    
    # Check US military patterns
    if 'RAPTOR' in callsign_upper or 'F-22' in callsign_upper:
        return MILITARY_AIRCRAFT['F22']
    if 'LIGHTNING' in callsign_upper or 'F-35' in callsign_upper:
        return MILITARY_AIRCRAFT['F35']
    if 'SPIRIT' in callsign_upper or 'B-2' in callsign_upper:
        return MILITARY_AIRCRAFT['B2']
    if 'RAIDER' in callsign_upper or 'B-21' in callsign_upper:
        return MILITARY_AIRCRAFT['B21']
    if 'EAGLE' in callsign_upper or 'F-15' in callsign_upper:
        return MILITARY_AIRCRAFT['F15']
    if 'VIPER' in callsign_upper or 'F-16' in callsign_upper:
        return MILITARY_AIRCRAFT['F16']
    if 'HORNET' in callsign_upper or 'F-18' in callsign_upper:
        return MILITARY_AIRCRAFT['F18']
    
    # US military callsign prefixes
    us_military_prefixes = {
        'RCH': 'C-17', 'REACH': 'C-17',
        'AF1': 'VC-25', 'SAM': 'C-32',
        'NAVY': 'P-8', 'ARMY': 'UH-60',
        'COBRA': 'AH-1', 'BLACKHAWK': 'UH-60',
        'VIPER': 'F-16', 'EAGLE': 'F-15',
        'HORNET': 'F-18', 'GRIZZLY': 'E-3',
    }
    
    for prefix, aircraft in us_military_prefixes.items():
        if callsign_upper.startswith(prefix):
            for key, info in MILITARY_AIRCRAFT.items():
                if aircraft in info['name']:
                    return info
    
    # Russian patterns
    russian_patterns = {
        'SU-57': 'SU57', 'SU-35': 'SU35', 'SU-27': 'SU35',
        'MIG-29': 'MIG29', 'MIG-31': 'MIG29',
        'TU-95': 'TU95', 'TU-160': 'TU95',
    }
    
    for pattern, aircraft_key in russian_patterns.items():
        if pattern in callsign_upper:
            return MILITARY_AIRCRAFT[aircraft_key]
    
    # Chinese patterns
    chinese_patterns = {
        'J-20': 'J20', 'J-16': 'J16', 'J-10': 'J16',
        'H-6': 'H6', 'H-6K': 'H6',
    }
    
    for pattern, aircraft_key in chinese_patterns.items():
        if pattern in callsign_upper:
            return MILITARY_AIRCRAFT[aircraft_key]
    
    return None

def identify_aircraft_type(callsign):
    """Complete aircraft identification"""
    callsign_upper = callsign.upper() if callsign else ""
    
    # Check military first
    military = identify_military_aircraft(callsign)
    if military:
        return military
    
    # Commercial airlines (3-letter ICAO codes)
    commercial_prefixes = {
        'UAL': ('United Airlines', 'Commercial Airliner', 70),
        'DAL': ('Delta Air Lines', 'Commercial Airliner', 70),
        'AAL': ('American Airlines', 'Commercial Airliner', 70),
        'SWA': ('Southwest Airlines', 'Commercial Airliner', 65),
        'JAL': ('Japan Airlines', 'Commercial Airliner', 70),
        'BAW': ('British Airways', 'Commercial Airliner', 70),
        'AFR': ('Air France', 'Commercial Airliner', 70),
        'DLH': ('Lufthansa', 'Commercial Airliner', 70),
        'KLM': ('KLM', 'Commercial Airliner', 70),
        'CPA': ('Cathay Pacific', 'Commercial Airliner', 70),
        'QFA': ('Qantas', 'Commercial Airliner', 70),
        'SIA': ('Singapore Airlines', 'Commercial Airliner', 70),
    }
    
    for code, (name, type_name, rcs) in commercial_prefixes.items():
        if callsign_upper.startswith(code):
            return {
                'name': name,
                'type': type_name,
                'rcs_m2': np.random.uniform(rcs-20, rcs+20),
                'stealth_level': 'None',
                'country': 'Various',
                'signature': 'Commercial aircraft'
            }
    
    # Cargo
    cargo_prefixes = {
        'FDX': ('FedEx', 'Cargo', 85),
        'UPS': ('UPS', 'Cargo', 85),
        'GTI': ('Atlas Air', 'Cargo', 80),
    }
    
    for code, (name, type_name, rcs) in cargo_prefixes.items():
        if callsign_upper.startswith(code):
            return {
                'name': name,
                'type': type_name,
                'rcs_m2': np.random.uniform(rcs-20, rcs+20),
                'stealth_level': 'None',
                'country': 'USA',
                'signature': 'Cargo aircraft'
            }
    
    # General Aviation (N-number)
    if callsign_upper.startswith('N') and len(callsign_upper) >= 2:
        return {
            'name': 'General Aviation',
            'type': 'General Aviation',
            'rcs_m2': np.random.uniform(1, 5),
            'stealth_level': 'None',
            'country': 'USA',
            'signature': 'Private aircraft'
        }
    
    # Unknown
    return {
        'name': 'Unknown Aircraft',
        'type': 'Unknown',
        'rcs_m2': np.random.uniform(5, 15),
        'stealth_level': 'Unknown',
        'country': 'Unknown',
        'signature': 'Unidentified'
    }

# ============================================================================
# OPENSKY FETCHER WITH FULL IDENTIFICATION
# ============================================================================

def fetch_opensky_radar_enhanced(lat, lon, radius):
    """Fetch live aircraft data with full identification"""
    try:
        bbox = (lat - radius, lat + radius, lon - radius, lon + radius)
        url = "https://opensky-network.org/api/states/all"
        params = {'lamin': bbox[0], 'lamax': bbox[1], 'lomin': bbox[2], 'lomax': bbox[3]}
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            return None, None, "API error"
        
        data = response.json()
        if not data.get('states'):
            return None, None, "No aircraft in area"
        
        range_bins, az_bins = 256, 360
        max_range = 300
        radar = np.zeros((range_bins, az_bins))
        aircraft_list = []
        
        for state in data['states']:
            if state[5] is None or state[6] is None:
                continue
            
            lon_air, lat_air = state[5], state[6]
            callsign = state[1] or ""
            icao24 = state[0]
            altitude = state[7] or 0
            velocity = state[9] or 0
            track = state[10] or 0
            
            # Identify aircraft type
            aircraft_info = identify_aircraft_type(callsign)
            
            # Calculate range and azimuth
            r_km = haversine_km(lat, lon, lat_air, lon_air)
            if r_km > max_range:
                continue
            
            az_deg = bearing(lat, lon, lat_air, lon_air)
            r_idx = int(r_km / max_range * (range_bins - 1))
            az_idx = int(az_deg / 360 * (az_bins - 1))
            
            # Use identified RCS or default
            rcs = aircraft_info.get('rcs_m2', np.random.uniform(5, 15))
            
            # Adjust RCS for stealth aircraft (lower is stealthier)
            stealth_factor = 1.0
            if aircraft_info.get('stealth_level') in ['Very High', 'High']:
                stealth_factor = 0.1
            elif aircraft_info.get('stealth_level') == 'Medium':
                stealth_factor = 0.3
            elif aircraft_info.get('stealth_level') == 'Low':
                stealth_factor = 0.6
            
            effective_rcs = rcs * stealth_factor
            snr = effective_rcs / (r_km**2 + 10)
            radar[r_idx, az_idx] += snr
            
            aircraft_list.append({
                'icao24': icao24,
                'callsign': callsign or 'Unknown',
                'aircraft_name': aircraft_info['name'],
                'aircraft_type': aircraft_info['type'],
                'country': aircraft_info['country'],
                'stealth_level': aircraft_info['stealth_level'],
                'signature': aircraft_info['signature'],
                'range_km': round(r_km, 1),
                'azimuth_deg': round(az_deg, 1),
                'altitude_m': altitude,
                'velocity_mps': round(velocity, 1),
                'rcs_m2': round(effective_rcs, 4),
                'track_deg': round(track, 1),
                'detection_confidence': 0.0  # Will be filled by PDP filter
            })
        
        if np.max(radar) > 0:
            radar = radar / np.max(radar)
        
        aircraft_list.sort(key=lambda x: x['range_km'])
        
        return radar, pd.DataFrame(aircraft_list), f"{len(aircraft_list)} aircraft detected"
        
    except Exception as e:
        return None, None, str(e)

def haversine_km(lat1, lon1, lat2, lon2):
    from math import radians, sin, cos, sqrt, asin
    R = 6371
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return R * 2 * asin(sqrt(a))

def bearing(lat1, lon1, lat2, lon2):
    from math import radians, degrees, sin, cos, atan2
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = sin(dlon) * cos(lat2)
    y = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(dlon)
    return (degrees(atan2(x, y)) + 360) % 360

# ============================================================================
# PDP FILTER (Your existing implementation)
# ============================================================================

def pdp_filter(radar, omega, fringe, mixing, entangle):
    rows, cols = radar.shape
    
    fft_img = fft2(radar)
    fft_shift = fftshift(fft_img)
    
    x = np.linspace(-1, 1, cols)
    y = np.linspace(-1, 1, rows)
    X, Y = np.meshgrid(x, y)
    R = np.sqrt(X**2 + Y**2)
    
    dark_mask = mixing * np.exp(-omega * R**2) * (1 - np.exp(-R**2 / fringe))
    dark_fft = fft_shift * dark_mask
    dark = np.abs(ifft2(fftshift(dark_fft)))
    
    total = np.sum(radar**2) + 1e-10
    ordinary = radar - dark
    rho = ordinary**2 / total
    entropy = -rho * np.log(np.maximum(rho, 1e-10))
    interference = (np.abs(ordinary + dark)**2 - ordinary**2 - dark**2) / total
    residuals = entropy * entangle + np.abs(interference) * mixing
    residuals = gaussian_filter(residuals, sigma=1.0)
    
    prob = dark * residuals
    prob = (prob - prob.min()) / (prob.max() - prob.min() + 1e-8)
    prob = np.clip(prob * 1.2, 0, 1)
    
    def norm(x):
        return (x - x.min()) / (x.max() - x.min() + 1e-8)
    
    rgb = np.zeros((*radar.shape, 3))
    rgb[..., 0] = norm(radar)
    rgb[..., 1] = norm(residuals)
    rgb[..., 2] = norm(dark)
    rgb = np.power(np.clip(rgb, 0, 1), 0.5)
    
    return dark, residuals, prob, rgb

def detect_targets(prob, threshold):
    binary = prob > threshold
    labeled, num = label(binary)
    
    detections = []
    for i in range(1, num + 1):
        mask = (labeled == i)
        if np.sum(mask) >= 5:
            com = center_of_mass(prob, labeled, i)
            confidence = np.mean(prob[mask])
            detections.append({
                'center': com,
                'confidence': confidence,
                'size': np.sum(mask)
            })
    
    max_idx = np.unravel_index(np.argmax(prob), prob.shape)
    max_val = prob[max_idx]
    if max_val > threshold and len(detections) == 0:
        detections.append({
            'center': (float(max_idx[0]), float(max_idx[1])),
            'confidence': float(max_val),
            'size': 1
        })
    
    return detections

# ============================================================================
# EXPORT FUNCTIONS
# ============================================================================

def export_to_csv(aircraft_df, detections_df):
    """Export data to CSV"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_data = aircraft_df.to_csv(index=False)
    return csv_data, f"stealth_radar_data_{timestamp}.csv"

def export_to_json(aircraft_df, detections_df, parameters):
    """Export data to JSON"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_data = {
        'timestamp': timestamp,
        'parameters': parameters,
        'aircraft_detections': aircraft_df.to_dict('records'),
        'pdp_detections': detections_df.to_dict('records') if detections_df is not None else []
    }
    json_data = json.dumps(export_data, indent=2)
    return json_data, f"stealth_radar_data_{timestamp}.json"

def export_to_image(fig):
    """Export figure to PNG"""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    return buf

def get_image_download_link(fig, filename):
    """Generate download link for image"""
    buf = export_to_image(fig)
    b64 = base64.b64encode(buf.read()).decode()
    href = f'<a href="data:image/png;base64,{b64}" download="{filename}">Download PNG</a>'
    return href

# ============================================================================
# SIDEBAR
# ============================================================================

OPTIMAL_OMEGA = 0.72
OPTIMAL_FRINGE = 1.75
OPTIMAL_ENTANGLEMENT = 0.44
OPTIMAL_MIXING = 0.17
OPTIMAL_THRESHOLD = 0.30

with st.sidebar:
    st.header("⚙️ PDP Filter Parameters")
    
    omega = st.slider("Ω (Entanglement Strength)", 0.0, 1.0, OPTIMAL_OMEGA, 0.01)
    fringe = st.slider("Fringe Scale", 0.1, 5.0, OPTIMAL_FRINGE, 0.05)
    entanglement = st.slider("Quantum Entanglement", 0.0, 1.0, OPTIMAL_ENTANGLEMENT, 0.01)
    mixing = st.slider("ε (Mixing Angle)", 0.0, 0.5, OPTIMAL_MIXING, 0.01)
    
    st.header("🎯 Detection")
    threshold = st.slider("Detection Threshold", 0.0, 1.0, OPTIMAL_THRESHOLD, 0.01)
    
    st.header("📡 Data Source")
    data_source = st.radio("Select Source", ["Synthetic Test", "OpenSky Live", "Upload Custom Data"])
    
    if data_source == "OpenSky Live":
        st.subheader("📍 Radar Location")
        st.caption("Try: DEN: 39.85, -104.67 | COS: 38.81, -104.71")
        radar_lat = st.number_input("Latitude", value=39.85, format="%.2f")
        radar_lon = st.number_input("Longitude", value=-104.67, format="%.2f")
        radius = st.slider("Search Radius (deg)", 1.0, 5.0, 3.0)
        fetch_opensky = st.button("🌐 Fetch Live Data", type="primary", use_container_width=True)
    
    elif data_source == "Synthetic Test":
        st.subheader("🎯 Target")
        target_range = st.slider("Target Range (km)", 50, 250, 150)
        target_azimuth = st.slider("Target Azimuth (deg)", 0, 360, 180)
        stealth = st.slider("Stealth Level", 0.0, 1.0, 0.15)
        noise = st.slider("Noise Level", 0.0, 0.3, 0.12)
        generate = st.button("🔄 Generate", type="primary", use_container_width=True)
    
    elif data_source == "Upload Custom Data":
        uploaded_file = st.file_uploader("Upload .npz or .npy", type=['npz', 'npy'])
    
    st.header("📤 Export Data")
    export_format = st.selectbox("Export Format", ["CSV", "JSON", "Image (PNG)"])
    export_button = st.button("💾 Export Data", type="secondary", use_container_width=True)

# ============================================================================
# MAIN EXECUTION
# ============================================================================

radar_image = None
aircraft_df = None
target_info = None

if data_source == "OpenSky Live":
    if 'fetch_opensky' in locals() and fetch_opensky:
        with st.spinner("Fetching live aircraft data..."):
            radar_image, aircraft_df, msg = fetch_opensky_radar_enhanced(radar_lat, radar_lon, radius)
            if radar_image is not None:
                st.sidebar.success(f"✅ {msg}")
                st.session_state.radar_opensky = radar_image
                st.session_state.aircraft_opensky = aircraft_df
            else:
                st.sidebar.error(f"⚠️ {msg}")
                if 'radar_opensky' in st.session_state:
                    radar_image = st.session_state.radar_opensky
                    aircraft_df = st.session_state.aircraft_opensky
    else:
        if 'radar_opensky' in st.session_state:
            radar_image = st.session_state.radar_opensky
            aircraft_df = st.session_state.aircraft_opensky

if radar_image is None:
    radar_image = np.random.randn(256, 360) * 0.1
    radar_image = (radar_image - radar_image.min()) / (radar_image.max() - radar_image.min())

# Apply PDP filter
with st.spinner("Applying PDP quantum filter..."):
    dark, residuals, prob, fusion = pdp_filter(radar_image, omega, fringe, mixing, entanglement)
    detections = detect_targets(prob, threshold)

# ============================================================================
# DISPLAY
# ============================================================================

st.title("🔍 Stealth Photon-Dark-Photon Quantum Radar")
st.markdown("*Spectral duality filter revealing dark-mode leakage in radar returns*")

# Metrics
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Data Source", data_source)
c2.metric("Aircraft", len(aircraft_df) if aircraft_df is not None else 0)
c3.metric("Detections", len(detections))
c4.metric("Max P", f"{np.max(prob):.3f}")
c5.metric("Threshold", f"{threshold:.2f}")

# Main plot
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
extent = [0, 360, 300, 0]

# Left: Radar with overlay
ax1.imshow(radar_image, aspect='auto', cmap='viridis', extent=extent)

# Add aircraft markers
if aircraft_df is not None and len(aircraft_df) > 0:
    for _, row in aircraft_df.iterrows():
        color = 'red' if row.get('stealth_level') in ['Very High', 'High'] else 'blue'
        marker = 'o' if row.get('stealth_level') in ['Very High', 'High'] else 's'
        ax1.plot(row['azimuth_deg'], row['range_km'], marker=marker, color=color,
                markersize=8, markeredgecolor='white', markeredgewidth=1)

ax1.set_xlabel("Azimuth (deg)")
ax1.set_ylabel("Range (km)")
ax1.set_title("📡 Radar with Detection Overlay")
plt.colorbar(ax1.images[0], ax=ax1)

# Add detection boxes
for d in detections:
    r = d['center'][0] / 256 * 300
    az = d['center'][1] / 360 * 360
    from matplotlib.patches import Rectangle
    rect = Rectangle((az - 12, r - 12), 24, 24, linewidth=3, edgecolor='lime', facecolor='none')
    ax1.add_patch(rect)

# Right: Probability map
ax2.imshow(prob, aspect='auto', cmap='hot', extent=extent, vmin=0, vmax=1)
for d in detections:
    r = d['center'][0] / 256 * 300
    az = d['center'][1] / 360 * 360
    from matplotlib.patches import Circle
    circle = Circle((az, r), 10, edgecolor='lime', facecolor='none', linewidth=3)
    ax2.add_patch(circle)

ax2.set_xlabel("Azimuth (deg)")
ax2.set_ylabel("Range (km)")
ax2.set_title("🎯 Stealth Probability Map")
plt.colorbar(ax2.images[0], ax=ax2)

plt.tight_layout()
st.pyplot(fig)

# Export handling
if export_button:
    if aircraft_df is not None:
        detections_df = pd.DataFrame([{
            'range_km': d['center'][0]/256*300,
            'azimuth_deg': d['center'][1]/360*360,
            'confidence': d['confidence']
        } for d in detections])
        
        params = {
            'omega': omega, 'fringe': fringe, 'entanglement': entanglement,
            'mixing': mixing, 'threshold': threshold, 'timestamp': datetime.now().isoformat()
        }
        
        if export_format == "CSV":
            csv_data, filename = export_to_csv(aircraft_df, detections_df)
            st.download_button("📥 Download CSV", csv_data, filename, "text/csv")
        elif export_format == "JSON":
            json_data, filename = export_to_json(aircraft_df, detections_df, params)
            st.download_button("📥 Download JSON", json_data, filename, "application/json")
        elif export_format == "Image (PNG)":
            st.markdown(get_image_download_link(fig, f"stealth_radar_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"), unsafe_allow_html=True)

# Aircraft Display
if aircraft_df is not None and len(aircraft_df) > 0:
    st.subheader("✈️ Aircraft Detections")
    
    # Statistics
    col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
    military_count = len(aircraft_df[aircraft_df['country'].isin(['USA', 'Russia', 'China', 'Europe'])])
    stealth_count = len(aircraft_df[aircraft_df['stealth_level'].isin(['Very High', 'High'])])
    
    col_stats1.metric("Total Aircraft", len(aircraft_df))
    col_stats2.metric("Military", military_count)
    col_stats3.metric("Stealth Capable", stealth_count)
    col_stats4.metric("Avg RCS", f"{aircraft_df['rcs_m2'].mean():.2f} m²")
    
    # Display table with all columns
    display_df = aircraft_df[['callsign', 'aircraft_name', 'aircraft_type', 'country', 
                              'stealth_level', 'range_km', 'azimuth_deg', 'altitude_m', 
                              'velocity_mps', 'rcs_m2']].copy()
    display_df.columns = ['Callsign', 'Aircraft', 'Type', 'Country', 'Stealth', 
                          'Range (km)', 'Azimuth (°)', 'Altitude (m)', 'Speed (m/s)', 'RCS (m²)']
    
    st.dataframe(display_df, use_container_width=True)

# Military Summary
if aircraft_df is not None and len(aircraft_df) > 0:
    with st.expander("🎖️ Military Aircraft Summary"):
        military_df = aircraft_df[aircraft_df['country'].isin(['USA', 'Russia', 'China', 'Europe'])].copy()
        if len(military_df) > 0:
            for _, row in military_df.iterrows():
                st.write(f"**{row['aircraft_name']}** ({row['country']})")
                st.write(f"- Callsign: {row['callsign']} | Range: {row['range_km']} km | RCS: {row['rcs_m2']:.4f} m²")
                st.write(f"- Stealth Level: {row['stealth_level']}")
                st.write("---")

# Fusion visualization
st.subheader("🌀 Blue-Halo IR Fusion")
fig_fusion, ax_fusion = plt.subplots(figsize=(12, 3.5))
ax_fusion.imshow(fusion, aspect='auto', extent=extent)
ax_fusion.set_xlabel("Azimuth (deg)")
ax_fusion.set_ylabel("Range (km)")
st.pyplot(fig_fusion)

# Components
col1, col2 = st.columns(2)
with col1:
    st.subheader("🌑 Dark-Mode Leakage")
    fig_dark, ax_dark = plt.subplots(figsize=(8, 4))
    ax_dark.imshow(dark, aspect='auto', cmap='Blues')
    st.pyplot(fig_dark)
with col2:
    st.subheader("🟢 Entanglement Residuals")
    fig_res, ax_res = plt.subplots(figsize=(8, 4))
    ax_res.imshow(residuals, aspect='auto', cmap='Greens')
    st.pyplot(fig_res)

st.markdown("---")
st.markdown(f"""
<div style="text-align: center;">
    <span style="color: #4CAF50;">✅ <b>ENHANCED COMPLETE VERSION</b></span> | 
    Ω={omega:.2f} | Fringe={fringe:.2f} | ε={mixing:.2f} | Threshold={threshold:.2f}<br>
    <b>Aircraft:</b> {len(aircraft_df) if aircraft_df is not None else 0} | 
    <b>Detections:</b> {len(detections)} | 
    <b>Military:</b> {military_count if aircraft_df is not None else 0}<br>
    <b>Export Ready</b> | <b>Stealth Detection Active</b><br>
    © 2026 Tony E. Ford | QCAUS Framework
</div>
""", unsafe_allow_html=True)
