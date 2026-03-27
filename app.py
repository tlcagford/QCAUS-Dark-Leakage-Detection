"""
StealthPDPRadar - ENHANCED WITH RETRY AND BETTER FALLBACK
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
# MILITARY AIRCRAFT SIGNATURE DATABASE
# ============================================================================

MILITARY_AIRCRAFT = {
    'F22': {'name': 'F-22 Raptor', 'country': 'USA', 'type': '5th Gen Fighter', 'rcs_m2': 0.0001, 'stealth_level': 'Very High'},
    'F35': {'name': 'F-35 Lightning II', 'country': 'USA', 'type': '5th Gen Fighter', 'rcs_m2': 0.001, 'stealth_level': 'High'},
    'B2': {'name': 'B-2 Spirit', 'country': 'USA', 'type': 'Stealth Bomber', 'rcs_m2': 0.0001, 'stealth_level': 'Very High'},
    'B21': {'name': 'B-21 Raider', 'country': 'USA', 'type': 'Stealth Bomber', 'rcs_m2': 0.00005, 'stealth_level': 'Very High'},
    'F15': {'name': 'F-15 Eagle', 'country': 'USA', 'type': '4th Gen Fighter', 'rcs_m2': 5.0, 'stealth_level': 'None'},
    'F16': {'name': 'F-16 Fighting Falcon', 'country': 'USA', 'type': '4th Gen Fighter', 'rcs_m2': 1.2, 'stealth_level': 'Low'},
    'F18': {'name': 'F/A-18 Hornet', 'country': 'USA', 'type': 'Naval Fighter', 'rcs_m2': 1.5, 'stealth_level': 'Low'},
    'C17': {'name': 'C-17 Globemaster', 'country': 'USA', 'type': 'Transport', 'rcs_m2': 80.0, 'stealth_level': 'None'},
    'SU57': {'name': 'Su-57 Felon', 'country': 'Russia', 'type': '5th Gen Fighter', 'rcs_m2': 0.01, 'stealth_level': 'Medium'},
    'SU35': {'name': 'Su-35 Flanker', 'country': 'Russia', 'type': '4.5 Gen Fighter', 'rcs_m2': 3.0, 'stealth_level': 'Low'},
    'J20': {'name': 'Chengdu J-20', 'country': 'China', 'type': '5th Gen Fighter', 'rcs_m2': 0.005, 'stealth_level': 'High'},
    'TYPHOON': {'name': 'Eurofighter Typhoon', 'country': 'Europe', 'type': '4.5 Gen Fighter', 'rcs_m2': 0.5, 'stealth_level': 'Low'},
}

def identify_aircraft_type(callsign):
    callsign_upper = callsign.upper() if callsign else ""
    
    # Check military patterns
    for key, info in MILITARY_AIRCRAFT.items():
        if key in callsign_upper:
            return info
    
    # Commercial airlines
    commercial = {
        'UAL': ('United Airlines', 70), 'DAL': ('Delta Air Lines', 70), 'AAL': ('American Airlines', 70),
        'SWA': ('Southwest Airlines', 65), 'JAL': ('Japan Airlines', 70), 'BAW': ('British Airways', 70),
        'AFR': ('Air France', 70), 'DLH': ('Lufthansa', 70), 'KLM': ('KLM', 70), 'CPA': ('Cathay Pacific', 70),
    }
    for code, (name, rcs) in commercial.items():
        if callsign_upper.startswith(code):
            return {'name': name, 'type': 'Commercial Airliner', 'country': 'Various', 'rcs_m2': np.random.uniform(rcs-20, rcs+20), 'stealth_level': 'None'}
    
    # Cargo
    cargo = {'FDX': ('FedEx', 85), 'UPS': ('UPS', 85), 'GTI': ('Atlas Air', 80)}
    for code, (name, rcs) in cargo.items():
        if callsign_upper.startswith(code):
            return {'name': name, 'type': 'Cargo', 'country': 'USA', 'rcs_m2': np.random.uniform(rcs-20, rcs+20), 'stealth_level': 'None'}
    
    # General Aviation
    if callsign_upper.startswith('N') and len(callsign_upper) >= 2:
        return {'name': 'General Aviation', 'type': 'General Aviation', 'country': 'USA', 'rcs_m2': np.random.uniform(1, 5), 'stealth_level': 'None'}
    
    return {'name': 'Unknown', 'type': 'Unknown', 'country': 'Unknown', 'rcs_m2': np.random.uniform(5, 15), 'stealth_level': 'Unknown'}

# ============================================================================
# OPENSKY FETCHER WITH RETRY
# ============================================================================

def fetch_opensky_with_retry(lat, lon, radius, max_retries=2):
    """Fetch OpenSky data with retry logic"""
    for attempt in range(max_retries):
        try:
            bbox = (lat - radius, lat + radius, lon - radius, lon + radius)
            url = "https://opensky-network.org/api/states/all"
            params = {'lamin': bbox[0], 'lamax': bbox[1], 'lomin': bbox[2], 'lomax': bbox[3]}
            
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                return response.json()
            else:
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return None
    return None

def fetch_opensky_radar_enhanced(lat, lon, radius):
    """Fetch live aircraft data with enhanced fallback"""
    data = fetch_opensky_with_retry(lat, lon, radius)
    
    if data is None or 'states' not in data or not data['states']:
        # Create synthetic aircraft data for demonstration
        return create_synthetic_aircraft_data(lat, lon, radius)
    
    range_bins, az_bins = 256, 360
    max_range = 300
    radar = np.zeros((range_bins, az_bins))
    aircraft_list = []
    
    for state in data['states']:
        if state[5] is None or state[6] is None:
            continue
        
        lon_air, lat_air = state[5], state[6]
        callsign = state[1] or ""
        altitude = state[7] or 0
        velocity = state[9] or 0
        
        r_km = haversine_km(lat, lon, lat_air, lon_air)
        if r_km > max_range:
            continue
        
        az_deg = bearing(lat, lon, lat_air, lon_air)
        r_idx = int(r_km / max_range * (range_bins - 1))
        az_idx = int(az_deg / 360 * (az_bins - 1))
        
        aircraft_info = identify_aircraft_type(callsign)
        rcs = aircraft_info['rcs_m2']
        
        # Stealth factor adjustment
        stealth_factor = 0.1 if aircraft_info['stealth_level'] in ['Very High', 'High'] else 1.0
        effective_rcs = rcs * stealth_factor
        snr = effective_rcs / (r_km**2 + 10)
        radar[r_idx, az_idx] += snr
        
        aircraft_list.append({
            'callsign': callsign or 'Unknown',
            'aircraft_name': aircraft_info['name'],
            'aircraft_type': aircraft_info['type'],
            'country': aircraft_info['country'],
            'stealth_level': aircraft_info['stealth_level'],
            'range_km': round(r_km, 1),
            'azimuth_deg': round(az_deg, 1),
            'altitude_m': altitude,
            'velocity_mps': round(velocity, 1),
            'rcs_m2': round(effective_rcs, 4)
        })
    
    if np.max(radar) > 0:
        radar = radar / np.max(radar)
    
    aircraft_list.sort(key=lambda x: x['range_km'])
    return radar, pd.DataFrame(aircraft_list), f"{len(aircraft_list)} aircraft detected"

def create_synthetic_aircraft_data(lat, lon, radius):
    """Create synthetic aircraft data for demonstration when OpenSky is unavailable"""
    range_bins, az_bins = 256, 360
    max_range = 300
    radar = np.zeros((range_bins, az_bins))
    aircraft_list = []
    
    # Create realistic synthetic aircraft positions around the radar location
    num_aircraft = np.random.randint(15, 40)
    
    # Sample aircraft types for synthetic data
    sample_aircraft = [
        ('UAL123', 'Boeing 737', 'Commercial Airliner', 'USA', 'None', 50),
        ('DAL456', 'Airbus A320', 'Commercial Airliner', 'USA', 'None', 55),
        ('AAL789', 'Boeing 787', 'Commercial Airliner', 'USA', 'None', 65),
        ('SWA321', 'Boeing 737', 'Commercial Airliner', 'USA', 'None', 48),
        ('N123AB', 'Cessna 172', 'General Aviation', 'USA', 'None', 2),
        ('N456CD', 'Piper Archer', 'General Aviation', 'USA', 'None', 1.5),
        ('RCH123', 'C-17 Globemaster', 'Military Transport', 'USA', 'None', 80),
        ('AF1', 'VC-25', 'Military VIP', 'USA', 'Low', 25),
        ('RAPTOR11', 'F-22 Raptor', '5th Gen Fighter', 'USA', 'Very High', 0.0001),
        ('LIGHTNING', 'F-35 Lightning', '5th Gen Fighter', 'USA', 'High', 0.001),
        ('EAGLE21', 'F-15 Eagle', '4th Gen Fighter', 'USA', 'None', 5.0),
        ('VIPER31', 'F-16 Falcon', '4th Gen Fighter', 'USA', 'Low', 1.2),
        ('HORNET41', 'F/A-18 Hornet', 'Naval Fighter', 'USA', 'Low', 1.5),
        ('SU57', 'Su-57 Felon', '5th Gen Fighter', 'Russia', 'Medium', 0.01),
        ('J20', 'J-20 Mighty Dragon', '5th Gen Fighter', 'China', 'High', 0.005),
        ('TYPHOON', 'Eurofighter Typhoon', '4.5 Gen Fighter', 'Europe', 'Low', 0.5),
        ('FDX123', 'FedEx MD-11', 'Cargo', 'USA', 'None', 85),
        ('UPS456', 'UPS 747', 'Cargo', 'USA', 'None', 85),
    ]
    
    for i in range(num_aircraft):
        # Random position within radius
        r_km = np.random.uniform(20, max_range - 20)
        az_deg = np.random.uniform(0, 360)
        
        r_idx = int(r_km / max_range * (range_bins - 1))
        az_idx = int(az_deg / 360 * (az_bins - 1))
        
        # Select random aircraft type
        aircraft = sample_aircraft[np.random.randint(0, len(sample_aircraft))]
        callsign, name, a_type, country, stealth_level, base_rcs = aircraft
        
        # Add to radar with realistic SNR
        snr = base_rcs / (r_km**2 + 10)
        radar[r_idx, az_idx] += snr * np.random.uniform(0.5, 1.5)
        
        aircraft_list.append({
            'callsign': callsign,
            'aircraft_name': name,
            'aircraft_type': a_type,
            'country': country,
            'stealth_level': stealth_level,
            'range_km': round(r_km, 1),
            'azimuth_deg': round(az_deg, 1),
            'altitude_m': np.random.randint(3000, 12000),
            'velocity_mps': round(np.random.uniform(70, 250), 1),
            'rcs_m2': round(base_rcs, 4)
        })
    
    # Normalize radar
    if np.max(radar) > 0:
        radar = radar / np.max(radar)
    
    aircraft_list.sort(key=lambda x: x['range_km'])
    return radar, pd.DataFrame(aircraft_list), f"Synthetic: {len(aircraft_list)} simulated aircraft (OpenSky unavailable)"

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
# PDP FILTER
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
    return csv_data, f"stealth_radar_data_{timestamp}.csv"

def export_to_json(aircraft_df, parameters):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_data = {
        'timestamp': timestamp,
        'parameters': parameters,
        'aircraft_detections': aircraft_df.to_dict('records')
    }
    json_data = json.dumps(export_data, indent=2)
    return json_data, f"stealth_radar_data_{timestamp}.json"

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
        st.caption("Try: DEN: 39.85, -104.67 | COS: 38.81, -104.71 | Nellis: 36.24, -115.04")
        radar_lat = st.number_input("Latitude", value=39.85, format="%.2f")
        radar_lon = st.number_input("Longitude", value=-104.67, format="%.2f")
        radius = st.slider("Search Radius (deg)", 1.0, 5.0, 3.5)
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

if data_source == "OpenSky Live":
    if 'fetch_opensky' in locals() and fetch_opensky:
        with st.spinner("Fetching live aircraft data..."):
            radar_image, aircraft_df, msg = fetch_opensky_radar_enhanced(radar_lat, radar_lon, radius)
            st.sidebar.info(f"{msg}")
            st.session_state.radar_opensky = radar_image
            st.session_state.aircraft_opensky = aircraft_df
    else:
        if 'radar_opensky' in st.session_state:
            radar_image = st.session_state.radar_opensky
            aircraft_df = st.session_state.aircraft_opensky
        else:
            radar_image, aircraft_df, _ = create_synthetic_aircraft_data(radar_lat, radar_lon, radius)

elif data_source == "Synthetic Test":
    if generate or 'radar_synthetic' not in st.session_state:
        from scipy.ndimage import gaussian_filter
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
        
        # Create synthetic aircraft list for synthetic mode
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
    st.subheader("✈️ Aircraft Detections")
    
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

# Military Summary
if aircraft_df is not None and len(aircraft_df) > 0:
    military_df = aircraft_df[aircraft_df['country'].isin(['USA', 'Russia', 'China', 'Europe'])].copy()
    if len(military_df) > 0:
        with st.expander("🎖️ Military Aircraft Summary"):
            for _, row in military_df.iterrows():
                st.write(f"**{row['aircraft_name']}** ({row['country']})")
                st.write(f"- Callsign: {row['callsign']} | Range: {row['range_km']} km | RCS: {row['rcs_m2']:.4f} m²")
                st.write(f"- Stealth Level: {row['stealth_level']}")
                st.write("---")

# Fusion and components
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
    <span style="color: #4CAF50;">✅ <b>ENHANCED COMPLETE VERSION</b></span> | 
    Ω={omega:.2f} | Fringe={fringe:.2f} | ε={mixing:.2f} | Threshold={threshold:.2f}<br>
    <b>Aircraft:</b> {len(aircraft_df) if aircraft_df is not None else 0} | 
    <b>Detections:</b> {len(detections)} | 
    <b>Military:</b> {military_count if aircraft_df is not None else 0}<br>
    © 2026 Tony E. Ford | QCAUS Framework
</div>
""", unsafe_allow_html=True)
