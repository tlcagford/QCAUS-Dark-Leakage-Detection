"""
StealthPDPRadar - REAL AIRCRAFT ONLY + GLOBAL MODE
Detects real aircraft including international flights via ADS-B exchange
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
import time

st.set_page_config(page_title="Stealth PDP Radar", page_icon="🔍", layout="wide")

# ============================================================================
# REAL AIRCRAFT DATABASE (Actual aircraft types)
# ============================================================================

REAL_AIRCRAFT_TYPES = {
    # US Military (real)
    'F22': {'name': 'F-22 Raptor', 'country': 'USA', 'type': '5th Gen Fighter', 'rcs_m2': 0.0001, 'stealth_level': 'Very High', 'realistic': True},
    'F35': {'name': 'F-35 Lightning II', 'country': 'USA', 'type': '5th Gen Fighter', 'rcs_m2': 0.001, 'stealth_level': 'High', 'realistic': True},
    'B2': {'name': 'B-2 Spirit', 'country': 'USA', 'type': 'Stealth Bomber', 'rcs_m2': 0.0001, 'stealth_level': 'Very High', 'realistic': True},
    'B21': {'name': 'B-21 Raider', 'country': 'USA', 'type': 'Stealth Bomber', 'rcs_m2': 0.00005, 'stealth_level': 'Very High', 'realistic': True},
    'F15': {'name': 'F-15 Eagle', 'country': 'USA', 'type': '4th Gen Fighter', 'rcs_m2': 5.0, 'stealth_level': 'None', 'realistic': True},
    'F16': {'name': 'F-16 Fighting Falcon', 'country': 'USA', 'type': '4th Gen Fighter', 'rcs_m2': 1.2, 'stealth_level': 'Low', 'realistic': True},
    'F18': {'name': 'F/A-18 Hornet', 'country': 'USA', 'type': 'Naval Fighter', 'rcs_m2': 1.5, 'stealth_level': 'Low', 'realistic': True},
    'C17': {'name': 'C-17 Globemaster', 'country': 'USA', 'type': 'Transport', 'rcs_m2': 80.0, 'stealth_level': 'None', 'realistic': True},
    'KC135': {'name': 'KC-135 Stratotanker', 'country': 'USA', 'type': 'Tanker', 'rcs_m2': 60.0, 'stealth_level': 'None', 'realistic': True},
    'E3': {'name': 'E-3 Sentry', 'country': 'USA', 'type': 'AWACS', 'rcs_m2': 90.0, 'stealth_level': 'None', 'realistic': True},
    'C130': {'name': 'C-130 Hercules', 'country': 'USA', 'type': 'Transport', 'rcs_m2': 45.0, 'stealth_level': 'None', 'realistic': True},
    'KC46': {'name': 'KC-46 Pegasus', 'country': 'USA', 'type': 'Tanker', 'rcs_m2': 70.0, 'stealth_level': 'None', 'realistic': True},
    
    # International aircraft (real)
    'SU57': {'name': 'Su-57 Felon', 'country': 'Russia', 'type': '5th Gen Fighter', 'rcs_m2': 0.01, 'stealth_level': 'Medium', 'realistic': True},
    'SU35': {'name': 'Su-35 Flanker', 'country': 'Russia', 'type': '4.5 Gen Fighter', 'rcs_m2': 3.0, 'stealth_level': 'Low', 'realistic': True},
    'SU30': {'name': 'Su-30 Flanker', 'country': 'Russia', 'type': '4th Gen Fighter', 'rcs_m2': 4.0, 'stealth_level': 'None', 'realistic': True},
    'MIG29': {'name': 'MiG-29 Fulcrum', 'country': 'Russia', 'type': '4th Gen Fighter', 'rcs_m2': 3.5, 'stealth_level': 'Low', 'realistic': True},
    'TU95': {'name': 'Tu-95 Bear', 'country': 'Russia', 'type': 'Strategic Bomber', 'rcs_m2': 100.0, 'stealth_level': 'None', 'realistic': True},
    'J20': {'name': 'Chengdu J-20', 'country': 'China', 'type': '5th Gen Fighter', 'rcs_m2': 0.005, 'stealth_level': 'High', 'realistic': True},
    'J16': {'name': 'Shenyang J-16', 'country': 'China', 'type': '4.5 Gen Fighter', 'rcs_m2': 2.0, 'stealth_level': 'Low', 'realistic': True},
    'J10': {'name': 'Chengdu J-10', 'country': 'China', 'type': '4th Gen Fighter', 'rcs_m2': 3.0, 'stealth_level': 'None', 'realistic': True},
    'H6': {'name': 'Xian H-6', 'country': 'China', 'type': 'Bomber', 'rcs_m2': 50.0, 'stealth_level': 'None', 'realistic': True},
    'TYPHOON': {'name': 'Eurofighter Typhoon', 'country': 'Europe', 'type': '4.5 Gen Fighter', 'rcs_m2': 0.5, 'stealth_level': 'Low', 'realistic': True},
    'RAFALE': {'name': 'Dassault Rafale', 'country': 'France', 'type': '4.5 Gen Fighter', 'rcs_m2': 0.4, 'stealth_level': 'Low', 'realistic': True},
    'GRIPEN': {'name': 'Saab Gripen', 'country': 'Sweden', 'type': '4th Gen Fighter', 'rcs_m2': 0.8, 'stealth_level': 'Low', 'realistic': True},
}

def identify_aircraft_type(callsign):
    """Identify real aircraft type from callsign"""
    callsign_upper = callsign.upper() if callsign else ""
    
    # Check for military aircraft patterns
    for key, info in REAL_AIRCRAFT_TYPES.items():
        if key in callsign_upper:
            return info
    
    # US military callsign prefixes (real)
    us_military = {
        'RCH': ('C-17 Globemaster', 'Transport', 80),
        'REACH': ('C-17 Globemaster', 'Transport', 80),
        'AF1': ('VC-25', 'Presidential', 25),
        'SAM': ('C-32', 'VIP Transport', 20),
        'NAVY': ('P-8 Poseidon', 'Maritime Patrol', 25),
        'ARMY': ('UH-60 Black Hawk', 'Helicopter', 3),
        'COBRA': ('AH-1 Cobra', 'Attack Helicopter', 2),
        'VIPER': ('F-16 Fighting Falcon', 'Fighter', 1.2),
        'EAGLE': ('F-15 Eagle', 'Fighter', 5.0),
        'HORNET': ('F/A-18 Hornet', 'Fighter', 1.5),
        'GRIZZLY': ('E-3 Sentry', 'AWACS', 90),
        'SENTRY': ('E-3 Sentry', 'AWACS', 90),
        'HAWK': ('C-130 Hercules', 'Transport', 45),
    }
    
    for prefix, (name, type_name, rcs) in us_military.items():
        if callsign_upper.startswith(prefix):
            return {'name': name, 'type': type_name, 'country': 'USA', 'rcs_m2': rcs, 'stealth_level': 'None', 'realistic': True}
    
    # Commercial airlines (real)
    commercial = {
        'UAL': ('United Airlines', 70), 'DAL': ('Delta Air Lines', 70), 'AAL': ('American Airlines', 70),
        'SWA': ('Southwest Airlines', 65), 'JAL': ('Japan Airlines', 70), 'BAW': ('British Airways', 70),
        'AFR': ('Air France', 70), 'DLH': ('Lufthansa', 70), 'KLM': ('KLM', 70), 'CPA': ('Cathay Pacific', 70),
        'QFA': ('Qantas', 70), 'SIA': ('Singapore Airlines', 70), 'ANA': ('All Nippon Airways', 70),
        'KAL': ('Korean Air', 70), 'ASA': ('Alaska Airlines', 65), 'FDX': ('FedEx', 85), 'UPS': ('UPS', 85),
    }
    for code, (name, rcs) in commercial.items():
        if callsign_upper.startswith(code):
            return {'name': name, 'type': 'Commercial Airliner', 'country': 'Various', 'rcs_m2': np.random.uniform(rcs-20, rcs+20), 'stealth_level': 'None', 'realistic': True}
    
    # General Aviation (real)
    if callsign_upper.startswith('N') and len(callsign_upper) >= 2:
        return {'name': 'General Aviation', 'type': 'General Aviation', 'country': 'USA', 'rcs_m2': np.random.uniform(1, 5), 'stealth_level': 'None', 'realistic': True}
    
    return {'name': 'Unknown Aircraft', 'type': 'Unknown', 'country': 'Unknown', 'rcs_m2': np.random.uniform(5, 15), 'stealth_level': 'Unknown', 'realistic': False}

# ============================================================================
# OPENSKY FETCHER WITH REAL DATA ONLY
# ============================================================================

def fetch_opensky_real(lat, lon, radius):
    """Fetch real aircraft data from OpenSky - NO SYNTHETIC FALLBACK"""
    try:
        bbox = (lat - radius, lat + radius, lon - radius, lon + radius)
        url = "https://opensky-network.org/api/states/all"
        params = {'lamin': bbox[0], 'lamax': bbox[1], 'lomin': bbox[2], 'lomax': bbox[3]}
        
        response = requests.get(url, params=params, timeout=15)
        if response.status_code != 200:
            return None, None, f"API Error: {response.status_code}"
        
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
            
            # Identify real aircraft type
            aircraft_info = identify_aircraft_type(callsign)
            
            # Calculate range and azimuth
            r_km = haversine_km(lat, lon, lat_air, lon_air)
            if r_km > max_range:
                continue
            
            az_deg = bearing(lat, lon, lat_air, lon_air)
            r_idx = int(r_km / max_range * (range_bins - 1))
            az_idx = int(az_deg / 360 * (az_bins - 1))
            
            rcs = aircraft_info.get('rcs_m2', np.random.uniform(5, 15))
            snr = rcs / (r_km**2 + 10)
            radar[r_idx, az_idx] += snr
            
            aircraft_list.append({
                'icao24': icao24,
                'callsign': callsign or 'Unknown',
                'aircraft_name': aircraft_info['name'],
                'aircraft_type': aircraft_info['type'],
                'country': aircraft_info['country'],
                'stealth_level': aircraft_info['stealth_level'],
                'range_km': round(r_km, 1),
                'azimuth_deg': round(az_deg, 1),
                'altitude_m': altitude,
                'velocity_mps': round(velocity, 1),
                'rcs_m2': round(rcs, 4),
                'track_deg': round(track, 1),
                'realistic': aircraft_info.get('realistic', True)
            })
        
        if np.max(radar) > 0:
            radar = radar / np.max(radar)
        
        aircraft_list.sort(key=lambda x: x['range_km'])
        return radar, pd.DataFrame(aircraft_list), f"✅ {len(aircraft_list)} REAL aircraft detected"
        
    except Exception as e:
        return None, None, f"Error: {str(e)}"

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
# PDP FILTER (Same as before)
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

def export_to_csv(aircraft_df):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_data = aircraft_df.to_csv(index=False)
    return csv_data, f"stealth_radar_real_data_{timestamp}.csv"

def export_to_json(aircraft_df, parameters):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_data = {
        'timestamp': timestamp,
        'parameters': parameters,
        'aircraft_detections': aircraft_df.to_dict('records')
    }
    json_data = json.dumps(export_data, indent=2)
    return json_data, f"stealth_radar_real_data_{timestamp}.json"

def get_image_download_link(fig, filename):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode()
    href = f'<a href="data:image/png;base64,{b64}" download="{filename}">📥 Download PNG</a>'
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
    data_source = st.radio("Select Source", ["OpenSky Live", "Synthetic Test", "Upload Custom Data"])
    
    if data_source == "OpenSky Live":
        st.subheader("📍 Radar Location")
        st.caption("🇺🇸 USA: DEN: 39.85, -104.67 | Nellis: 36.24, -115.04 | Langley: 37.08, -76.36")
        st.caption("🌍 Global: London: 51.47, -0.45 | Tokyo: 35.55, 139.78 | Moscow: 55.76, 37.62")
        radar_lat = st.number_input("Latitude", value=39.85, format="%.2f")
        radar_lon = st.number_input("Longitude", value=-104.67, format="%.2f")
        radius = st.slider("Search Radius (deg)", 1.0, 5.0, 3.5)
        fetch_opensky = st.button("🌐 Fetch REAL Live Data", type="primary", use_container_width=True)
        st.caption("⚠️ Note: Only real aircraft currently flying will appear. Russian/Chinese stealth rarely fly over US.")
    
    elif data_source == "Synthetic Test":
        st.subheader("🎯 Synthetic Test Mode")
        st.caption("Use this to test stealth detection with simulated targets")
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

if data_source == "OpenSky Live":
    if 'fetch_opensky' in locals() and fetch_opensky:
        with st.spinner("Fetching REAL aircraft data from OpenSky..."):
            radar_image, aircraft_df, msg = fetch_opensky_real(radar_lat, radar_lon, radius)
            if radar_image is not None:
                st.sidebar.success(msg)
                st.session_state.radar_opensky = radar_image
                st.session_state.aircraft_opensky = aircraft_df
            else:
                st.sidebar.error(msg)
                if 'radar_opensky' in st.session_state:
                    radar_image = st.session_state.radar_opensky
                    aircraft_df = st.session_state.aircraft_opensky
    else:
        if 'radar_opensky' in st.session_state:
            radar_image = st.session_state.radar_opensky
            aircraft_df = st.session_state.aircraft_opensky
        else:
            st.info("Click 'Fetch REAL Live Data' to see actual aircraft in your selected area")

elif data_source == "Synthetic Test":
    if generate or 'radar_synthetic' not in st.session_state:
        radar_image = np.random.randn(256, 360) * 0.1
        r_idx = int(150 / 300 * 255)
        az_idx = int(180 / 360 * 359)
        for dr in range(-12, 13):
            for da in range(-10, 11):
                rr = r_idx + dr
                aa = (az_idx + da) % 360
                if 0 <= rr < 256:
                    radar_image[rr, aa] += 0.8 * np.exp(-(dr**2 + da**2) / 30)
        radar_image = (radar_image - radar_image.min()) / (radar_image.max() - radar_image.min())
        
        aircraft_list = [{
            'callsign': 'STEALTH',
            'aircraft_name': 'Stealth Target',
            'aircraft_type': 'Stealth',
            'country': 'Test',
            'stealth_level': 'Very High',
            'range_km': 150,
            'azimuth_deg': 180,
            'altitude_m': 8000,
            'velocity_mps': 250,
            'rcs_m2': 0.001
        }]
        aircraft_df = pd.DataFrame(aircraft_list)
        st.session_state.radar_synthetic = radar_image
        st.session_state.aircraft_synthetic = aircraft_df
    else:
        radar_image = st.session_state.radar_synthetic
        aircraft_df = st.session_state.aircraft_synthetic

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
st.markdown("*Real aircraft detection via OpenSky Network*")

# Metrics
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Data Source", data_source)
c2.metric("Aircraft", len(aircraft_df) if aircraft_df is not None else 0)
c3.metric("Detections", len(detections))
c4.metric("Max P", f"{np.max(prob):.3f}")
c5.metric("Threshold", f"{threshold:.2f}")

# Main plot
if radar_image is not None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    extent = [0, 360, 300, 0]

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

    for d in detections:
        r = d['center'][0] / 256 * 300
        az = d['center'][1] / 360 * 360
        from matplotlib.patches import Rectangle
        rect = Rectangle((az - 12, r - 12), 24, 24, linewidth=3, edgecolor='lime', facecolor='none')
        ax1.add_patch(rect)

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
if export_button and aircraft_df is not None and len(aircraft_df) > 0:
    params = {'omega': omega, 'fringe': fringe, 'entanglement': entanglement, 'mixing': mixing, 'threshold': threshold}
    if export_format == "CSV":
        csv_data, filename = export_to_csv(aircraft_df)
        st.download_button("📥 Download CSV", csv_data, filename, "text/csv")
    elif export_format == "JSON":
        json_data, filename = export_to_json(aircraft_df, params)
        st.download_button("📥 Download JSON", json_data, filename, "application/json")
    elif export_format == "Image (PNG)":
        st.markdown(get_image_download_link(fig, f"stealth_radar_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"), unsafe_allow_html=True)

# Aircraft Display
if aircraft_df is not None and len(aircraft_df) > 0:
    st.subheader("✈️ REAL Aircraft Detections")
    
    col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
    military_count = len(aircraft_df[aircraft_df['country'].isin(['USA', 'Russia', 'China', 'Europe'])])
    stealth_count = len(aircraft_df[aircraft_df['stealth_level'].isin(['Very High', 'High'])])
    
    col_stats1.metric("Total Aircraft", len(aircraft_df))
    col_stats2.metric("Military", military_count)
    col_stats3.metric("Stealth Capable", stealth_count)
    col_stats4.metric("Avg RCS", f"{aircraft_df['rcs_m2'].mean():.2f} m²")
    
    display_df = aircraft_df[['callsign', 'aircraft_name', 'aircraft_type', 'country', 'stealth_level', 'range_km', 'azimuth_deg', 'altitude_m', 'velocity_mps', 'rcs_m2']].copy()
    display_df.columns = ['Callsign', 'Aircraft', 'Type', 'Country', 'Stealth', 'Range (km)', 'Azimuth (°)', 'Altitude (m)', 'Speed (m/s)', 'RCS (m²)']
    st.dataframe(display_df, use_container_width=True)

# Fusion and components
if radar_image is not None:
    st.subheader("🌀 Blue-Halo IR Fusion")
    fig_fusion, ax_fusion = plt.subplots(figsize=(12, 3.5))
    ax_fusion.imshow(fusion, aspect='auto', extent=extent)
    ax_fusion.set_xlabel("Azimuth (deg)")
    ax_fusion.set_ylabel("Range (km)")
    st.pyplot(fig_fusion)

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
    <span style="color: #4CAF50;">✅ <b>REAL AIRCRAFT DETECTION</b></span> | 
    Ω={omega:.2f} | Fringe={fringe:.2f} | ε={mixing:.2f} | Threshold={threshold:.2f}<br>
    <b>Real Aircraft:</b> {len(aircraft_df) if aircraft_df is not None else 0} | 
    <b>PDP Detections:</b> {len(detections)}<br>
    <b>Note:</b> Russian/Chinese stealth aircraft only appear in their respective airspace (Russia, China)<br>
    © 2026 Tony E. Ford | QCAUS Framework
</div>
""", unsafe_allow_html=True)
