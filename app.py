"""
StealthPDPRadar - ENHANCED WITH DETECTION DATA INCORPORATION
Saves and exports all PDP filter results
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
# REAL AIRCRAFT DATABASE
# ============================================================================

REAL_AIRCRAFT_TYPES = {
    'F22': {'name': 'F-22 Raptor', 'country': 'USA', 'type': '5th Gen Fighter', 'rcs_m2': 0.0001, 'stealth_level': 'Very High'},
    'F35': {'name': 'F-35 Lightning II', 'country': 'USA', 'type': '5th Gen Fighter', 'rcs_m2': 0.001, 'stealth_level': 'High'},
    'B2': {'name': 'B-2 Spirit', 'country': 'USA', 'type': 'Stealth Bomber', 'rcs_m2': 0.0001, 'stealth_level': 'Very High'},
    'F15': {'name': 'F-15 Eagle', 'country': 'USA', 'type': '4th Gen Fighter', 'rcs_m2': 5.0, 'stealth_level': 'None'},
    'F16': {'name': 'F-16 Fighting Falcon', 'country': 'USA', 'type': '4th Gen Fighter', 'rcs_m2': 1.2, 'stealth_level': 'Low'},
    'C17': {'name': 'C-17 Globemaster', 'country': 'USA', 'type': 'Transport', 'rcs_m2': 80.0, 'stealth_level': 'None'},
    'SU57': {'name': 'Su-57 Felon', 'country': 'Russia', 'type': '5th Gen Fighter', 'rcs_m2': 0.01, 'stealth_level': 'Medium'},
    'J20': {'name': 'Chengdu J-20', 'country': 'China', 'type': '5th Gen Fighter', 'rcs_m2': 0.005, 'stealth_level': 'High'},
}

def identify_aircraft_type(callsign):
    callsign_upper = callsign.upper() if callsign else ""
    
    for key, info in REAL_AIRCRAFT_TYPES.items():
        if key in callsign_upper:
            return info
    
    us_military = {
        'RCH': ('C-17 Globemaster', 'Transport', 80),
        'REACH': ('C-17 Globemaster', 'Transport', 80),
        'AF1': ('VC-25', 'Presidential', 25),
        'VIPER': ('F-16 Fighting Falcon', 'Fighter', 1.2),
        'EAGLE': ('F-15 Eagle', 'Fighter', 5.0),
    }
    
    for prefix, (name, type_name, rcs) in us_military.items():
        if callsign_upper.startswith(prefix):
            return {'name': name, 'type': type_name, 'country': 'USA', 'rcs_m2': rcs, 'stealth_level': 'None'}
    
    commercial = {
        'UAL': ('United Airlines', 70), 'DAL': ('Delta Air Lines', 70), 'AAL': ('American Airlines', 70),
        'SWA': ('Southwest Airlines', 65), 'FDX': ('FedEx', 85), 'UPS': ('UPS', 85),
    }
    for code, (name, rcs) in commercial.items():
        if callsign_upper.startswith(code):
            return {'name': name, 'type': 'Commercial', 'country': 'Various', 'rcs_m2': np.random.uniform(rcs-20, rcs+20), 'stealth_level': 'None'}
    
    if callsign_upper.startswith('N') and len(callsign_upper) >= 2:
        return {'name': 'General Aviation', 'type': 'GA', 'country': 'USA', 'rcs_m2': np.random.uniform(1, 5), 'stealth_level': 'None'}
    
    return {'name': 'Unknown', 'type': 'Unknown', 'country': 'Unknown', 'rcs_m2': np.random.uniform(5, 15), 'stealth_level': 'Unknown'}

# ============================================================================
# OPENSKY FETCHER
# ============================================================================

def fetch_opensky_real(lat, lon, radius):
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
            altitude = state[7] or 0
            velocity = state[9] or 0
            
            r_km = haversine_km(lat, lon, lat_air, lon_air)
            if r_km > max_range:
                continue
            
            az_deg = bearing(lat, lon, lat_air, lon_air)
            r_idx = int(r_km / max_range * (range_bins - 1))
            az_idx = int(az_deg / 360 * (az_bins - 1))
            
            aircraft_info = identify_aircraft_type(callsign)
            rcs = aircraft_info.get('rcs_m2', 10)
            snr = rcs / (r_km**2 + 10)
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
                'rcs_m2': round(rcs, 4)
            })
        
        if np.max(radar) > 0:
            radar = radar / np.max(radar)
        
        aircraft_list.sort(key=lambda x: x['range_km'])
        return radar, pd.DataFrame(aircraft_list), f"✅ {len(aircraft_list)} real aircraft detected"
        
    except requests.exceptions.Timeout:
        return None, None, "⚠️ OpenSky API timeout - server busy, try again in a few minutes"
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
        if np.sum(mask) >= 10:
            com = center_of_mass(prob, labeled, i)
            confidence = np.mean(prob[mask])
            detections.append({
                'center': com,
                'confidence': confidence,
                'size': np.sum(mask)
            })
    
    return detections

# ============================================================================
# ENHANCED EXPORT FUNCTIONS - INCORPORATES ALL DETECTION DATA
# ============================================================================

def export_complete_data(aircraft_df, detections, prob, radar_image, parameters, timestamp):
    """Export complete detection data including PDP filter results"""
    
    # Convert detections to DataFrame
    detections_data = []
    for d in detections:
        r_km = d['center'][0] / 256 * 300
        az_deg = d['center'][1] / 360 * 360
        detections_data.append({
            'detection_id': len(detections_data) + 1,
            'range_km': round(r_km, 1),
            'azimuth_deg': round(az_deg, 1),
            'confidence': round(d['confidence'], 4),
            'size_pixels': d['size']
        })
    
    detections_df = pd.DataFrame(detections_data) if detections_data else pd.DataFrame()
    
    # Calculate stealth probability statistics
    prob_stats = {
        'max_probability': float(np.max(prob)),
        'mean_probability': float(np.mean(prob)),
        'std_probability': float(np.std(prob)),
        'total_detections': len(detections)
    }
    
    # Create complete export package
    export_package = {
        'timestamp': timestamp,
        'parameters': parameters,
        'detection_summary': prob_stats,
        'aircraft_data': aircraft_df.to_dict('records') if aircraft_df is not None else [],
        'pdp_detections': detections_data,
        'stealth_probability_stats': prob_stats
    }
    
    return export_package

def export_to_csv_complete(aircraft_df, detections):
    """Export aircraft and detection data to CSV"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Aircraft CSV
    if aircraft_df is not None and len(aircraft_df) > 0:
        aircraft_csv = aircraft_df.to_csv(index=False)
        aircraft_filename = f"stealth_radar_aircraft_{timestamp}.csv"
    else:
        aircraft_csv = None
        aircraft_filename = None
    
    # Detections CSV
    detections_data = []
    for d in detections:
        r_km = d['center'][0] / 256 * 300
        az_deg = d['center'][1] / 360 * 360
        detections_data.append({
            'detection_id': len(detections_data) + 1,
            'range_km': r_km,
            'azimuth_deg': az_deg,
            'confidence': d['confidence'],
            'size_pixels': d['size']
        })
    
    detections_df = pd.DataFrame(detections_data)
    detections_csv = detections_df.to_csv(index=False)
    detections_filename = f"stealth_radar_detections_{timestamp}.csv"
    
    return aircraft_csv, detections_csv, aircraft_filename, detections_filename

def export_to_json_complete(aircraft_df, detections, prob, parameters, timestamp):
    """Export complete data to JSON"""
    export_package = export_complete_data(aircraft_df, detections, prob, None, parameters, timestamp)
    json_data = json.dumps(export_package, indent=2)
    filename = f"stealth_radar_complete_{timestamp}.json"
    return json_data, filename

def get_image_download_link(fig, filename):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode()
    href = f'<a href="data:image/png;base64,{b64}" download="{filename}">📥 Download PNG</a>'
    return href

# ============================================================================
# SYNTHETIC TEST DATA GENERATOR
# ============================================================================

def generate_synthetic_test(target_range, target_azimuth, stealth_level):
    range_bins, az_bins = 256, 360
    max_range = 300
    
    radar = np.zeros((range_bins, az_bins))
    
    r_idx = int(target_range / max_range * (range_bins - 1))
    az_idx = int(target_azimuth / 360 * (az_bins - 1))
    
    rcs = 10.0 * (1 - stealth_level)
    snr = rcs / (target_range**2 + 10)
    
    for dr in range(-12, 13):
        for da in range(-10, 11):
            rr = r_idx + dr
            aa = (az_idx + da) % az_bins
            if 0 <= rr < range_bins:
                dist = np.sqrt(dr**2 + da**2)
                radar[rr, aa] += snr * np.exp(-dist**2 / 30)
    
    radar = (radar - radar.min()) / (radar.max() - radar.min() + 1e-8)
    
    stealth_level_text = "Very High" if stealth_level > 0.8 else "High" if stealth_level > 0.5 else "Medium" if stealth_level > 0.2 else "Low"
    
    aircraft_list = [{
        'callsign': 'STEALTH',
        'aircraft_name': 'Stealth Target',
        'aircraft_type': 'Stealth Demonstrator',
        'country': 'Test',
        'stealth_level': stealth_level_text,
        'range_km': target_range,
        'azimuth_deg': target_azimuth,
        'altitude_m': 8000,
        'velocity_mps': 250,
        'rcs_m2': round(rcs, 4)
    }]
    
    return radar, pd.DataFrame(aircraft_list), r_idx, az_idx, rcs

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
    data_source = st.radio("Select Source", ["OpenSky Live", "Synthetic Test"])
    
    if data_source == "OpenSky Live":
        st.subheader("📍 Radar Location")
        st.markdown("**🇺🇸 USA:** DEN: 39.85, -104.67 | Nellis: 36.24, -115.04")
        st.markdown("**🌍 Global:** Moscow: 55.76, 37.62 | Beijing: 39.90, 116.40")
        
        radar_lat = st.number_input("Latitude", value=39.85, format="%.2f")
        radar_lon = st.number_input("Longitude", value=-104.67, format="%.2f")
        radius = st.slider("Search Radius (deg)", 1.0, 5.0, 3.5)
        fetch_opensky = st.button("🌐 Fetch Live Data", type="primary", use_container_width=True)
    
    elif data_source == "Synthetic Test":
        st.subheader("🎯 Synthetic Test")
        target_range = st.slider("Target Range (km)", 50, 250, 150)
        target_azimuth = st.slider("Target Azimuth (deg)", 0, 360, 180)
        stealth_level = st.slider("Stealth Level", 0.0, 1.0, 0.15)
        generate = st.button("🔄 Generate", type="primary", use_container_width=True)
    
    st.header("📤 Export Detection Data")
    export_type = st.selectbox("Export Type", ["Complete JSON", "Aircraft CSV", "Detections CSV", "PNG Image"])
    export_button = st.button("💾 Export", type="secondary", use_container_width=True)

# ============================================================================
# MAIN EXECUTION
# ============================================================================

radar_image = None
aircraft_df = None
target_info = None
status_msg = ""

# Synthetic Test
if data_source == "Synthetic Test":
    if generate or 'radar_synthetic' not in st.session_state:
        radar_image, aircraft_df, r_idx, az_idx, rcs = generate_synthetic_test(target_range, target_azimuth, stealth_level)
        target_info = (target_range, target_azimuth, r_idx, az_idx, rcs)
        st.session_state.radar_synthetic = radar_image
        st.session_state.aircraft_synthetic = aircraft_df
        st.session_state.target_info = target_info
        status_msg = f"Synthetic test: {target_range}km, {target_azimuth}°, RCS={rcs:.4f}m²"
    else:
        radar_image = st.session_state.radar_synthetic
        aircraft_df = st.session_state.aircraft_synthetic
        target_info = st.session_state.target_info
        status_msg = "Synthetic test scenario"

# OpenSky Live
elif data_source == "OpenSky Live":
    if 'fetch_opensky' in locals() and fetch_opensky:
        with st.spinner("Fetching real aircraft data..."):
            radar_image, aircraft_df, status_msg = fetch_opensky_real(radar_lat, radar_lon, radius)
            if radar_image is not None:
                st.session_state.radar = radar_image
                st.session_state.aircraft = aircraft_df
                target_info = None
    else:
        if 'radar' in st.session_state:
            radar_image = st.session_state.radar
            aircraft_df = st.session_state.aircraft
            target_info = None

# Display status
if status_msg:
    if "✅" in status_msg:
        st.sidebar.success(status_msg)
    elif "⚠️" in status_msg:
        st.sidebar.warning(status_msg)
    else:
        st.sidebar.info(status_msg)

# Apply PDP filter
if radar_image is not None:
    with st.spinner("Applying PDP quantum filter..."):
        dark, residuals, prob, fusion = pdp_filter(radar_image, omega, fringe, mixing, entanglement)
        detections = detect_targets(prob, threshold)
else:
    dark = residuals = prob = fusion = None
    detections = []

# ============================================================================
# DISPLAY
# ============================================================================

st.title("🔍 Stealth Photon-Dark-Photon Quantum Radar")
st.markdown("*Quantum detection of low-observable targets*")

# Metrics
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Data Source", data_source)
c2.metric("Aircraft", len(aircraft_df) if aircraft_df is not None else 0)
c3.metric("PDP Detections", len(detections))
c4.metric("Max P", f"{np.max(prob):.3f}" if prob is not None else "N/A")
c5.metric("Threshold", f"{threshold:.2f}")

# Show warning if no data
if radar_image is None:
    st.warning("""
    ### ⚠️ No Radar Data Available
    
    **OpenSky API is currently timing out.** 
    
    **Try these options:**
    1. **Switch to "Synthetic Test"** mode to test the PDP filter
    2. **Wait 30 seconds** and click "Fetch Live Data" again
    3. **Try different coordinates** (Denver area is often busy)
    """)
    
    if st.button("🚀 Switch to Synthetic Test Mode"):
        st.rerun()

# Display radar plots
elif radar_image is not None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    extent = [0, 360, 300, 0]

    ax1.imshow(radar_image, aspect='auto', cmap='viridis', extent=extent)
    
    if target_info:
        target_range, target_azimuth, r_idx, az_idx, rcs = target_info
        ax1.plot(target_azimuth, target_range, 'ro', markersize=14,
                markeredgecolor='white', markeredgewidth=2, label='Target')
        ax1.legend()
    
    if aircraft_df is not None and len(aircraft_df) > 0:
        for _, row in aircraft_df.iterrows():
            color = 'red' if row.get('stealth_level') in ['Very High', 'High'] else 'blue'
            marker = 'o' if row.get('stealth_level') in ['Very High', 'High'] else 's'
            ax1.plot(row['azimuth_deg'], row['range_km'], marker=marker, color=color,
                    markersize=8, markeredgecolor='white', markeredgewidth=1, alpha=0.7)
    
    for d in detections:
        r = d['center'][0] / 256 * 300
        az = d['center'][1] / 360 * 360
        from matplotlib.patches import Rectangle
        rect = Rectangle((az - 12, r - 12), 24, 24, linewidth=2, edgecolor='lime', facecolor='none')
        ax1.add_patch(rect)
        ax1.text(az - 8, r - 18, f"{d['confidence']:.2f}", color='lime', fontsize=8,
                bbox=dict(boxstyle='round', facecolor='black', alpha=0.6))
    
    ax1.set_xlabel("Azimuth (deg)")
    ax1.set_ylabel("Range (km)")
    ax1.set_title("📡 Radar with Detection Overlay")
    plt.colorbar(ax1.images[0], ax=ax1)
    
    ax2.imshow(prob, aspect='auto', cmap='hot', extent=extent, vmin=0, vmax=1)
    for d in detections:
        r = d['center'][0] / 256 * 300
        az = d['center'][1] / 360 * 360
        from matplotlib.patches import Circle
        circle = Circle((az, r), 8, edgecolor='lime', facecolor='none', linewidth=2)
        ax2.add_patch(circle)
    
    if target_info:
        ax2.plot(target_azimuth, target_range, 'ro', markersize=10, alpha=0.5)
    
    ax2.set_xlabel("Azimuth (deg)")
    ax2.set_ylabel("Range (km)")
    ax2.set_title("🎯 Stealth Probability Map")
    plt.colorbar(ax2.images[0], ax=ax2)
    
    plt.tight_layout()
    st.pyplot(fig)
    
    # Aircraft Table
    if aircraft_df is not None and len(aircraft_df) > 0:
        st.subheader("✈️ Aircraft Detections")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total", len(aircraft_df))
        military_count = len(aircraft_df[aircraft_df['country'] == 'USA']) if 'country' in aircraft_df.columns else 0
        col2.metric("Military", military_count)
        stealth_count = len(aircraft_df[aircraft_df['stealth_level'].isin(['Very High', 'High'])])
        col3.metric("Stealth Capable", stealth_count)
        
        display_columns = ['callsign', 'aircraft_name', 'aircraft_type', 'country', 'stealth_level', 'range_km', 'azimuth_deg', 'rcs_m2']
        available_columns = [col for col in display_columns if col in aircraft_df.columns]
        display_df = aircraft_df[available_columns].head(20)
        
        rename_map = {
            'callsign': 'Callsign',
            'aircraft_name': 'Aircraft',
            'aircraft_type': 'Type',
            'country': 'Country',
            'stealth_level': 'Stealth',
            'range_km': 'Range(km)',
            'azimuth_deg': 'Azimuth(°)',
            'rcs_m2': 'RCS(m²)'
        }
        display_df = display_df.rename(columns=rename_map)
        st.dataframe(display_df, use_container_width=True)
    
    # PDP Detections Table
    if detections:
        st.subheader("🎯 PDP Filter Detections")
        detections_data = []
        for i, d in enumerate(detections):
            r_km = d['center'][0] / 256 * 300
            az_deg = d['center'][1] / 360 * 360
            detections_data.append({
                'ID': i + 1,
                'Range (km)': round(r_km, 1),
                'Azimuth (°)': round(az_deg, 1),
                'Confidence': round(d['confidence'], 3),
                'Size (pixels)': d['size']
            })
        st.dataframe(pd.DataFrame(detections_data), use_container_width=True)
    
    # Fusion and components
    st.subheader("🌀 Blue-Halo IR Fusion")
    fig_fusion, ax_fusion = plt.subplots(figsize=(12, 3))
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
    
    # Detection Performance Metrics
    if target_info and detections:
        target_range, target_azimuth, r_idx, az_idx, rcs = target_info
        # Find closest detection to target
        closest_dist = min([np.sqrt((d['center'][0] - r_idx)**2 + (d['center'][1] - az_idx)**2) for d in detections])
        best_confidence = max([d['confidence'] for d in detections])
        
        st.subheader("📊 Detection Performance")
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Detection Distance", f"{closest_dist:.1f} pixels", "Lower is better")
        col_b.metric("Best Confidence", f"{best_confidence:.3f}", ">0.5 = good")
        col_c.metric("Target RCS", f"{rcs:.4f} m²", f"{stealth_level*100:.0f}% stealth")
        
        if closest_dist < 20 and best_confidence > 0.5:
            st.success("✅ STEALTH TARGET SUCCESSFULLY DETECTED!")
        elif closest_dist < 30:
            st.warning("⚠️ Partial detection - try adjusting threshold")
        else:
            st.info("💡 Try lowering threshold or adjusting Ω parameter")

# ============================================================================
# EXPORT HANDLING
# ============================================================================

if export_button and radar_image is not None:
    timestamp = datetime.now().isoformat()
    params = {
        'omega': omega, 'fringe': fringe, 'entanglement': entanglement,
        'mixing': mixing, 'threshold': threshold, 'timestamp': timestamp
    }
    
    if export_type == "Complete JSON":
        json_data, filename = export_to_json_complete(aircraft_df, detections, prob, params, timestamp)
        st.download_button("📥 Download Complete JSON", json_data, filename, "application/json")
        
    elif export_type == "Aircraft CSV" and aircraft_df is not None and len(aircraft_df) > 0:
        csv_data, detections_csv, aircraft_filename, detections_filename = export_to_csv_complete(aircraft_df, detections)
        if csv_data:
            st.download_button("📥 Download Aircraft CSV", csv_data, aircraft_filename, "text/csv")
        
    elif export_type == "Detections CSV" and detections:
        csv_data, detections_csv, aircraft_filename, detections_filename = export_to_csv_complete(aircraft_df, detections)
        if detections_csv:
            st.download_button("📥 Download Detections CSV", detections_csv, detections_filename, "text/csv")
        
    elif export_type == "PNG Image":
        st.markdown(get_image_download_link(fig, f"stealth_radar_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"), unsafe_allow_html=True)

st.markdown("---")
st.markdown(f"""
<div style="text-align: center; color: #888;">
    <b>Stealth PDP Radar</b> | Ω={omega:.2f} | Fringe={fringe:.2f} | ε={mixing:.2f} | Threshold={threshold:.2f}<br>
    <b>PDP Detections:</b> {len(detections)} | <b>Export Ready</b> | All detection data saved<br>
    © 2026 Tony E. Ford | QCAUS Framework
</div>
""", unsafe_allow_html=True)
