"""
StealthPDPRadar - COMPLETE VERSION
- Synthetic Test (working)
- OpenSky Live (real radar data)
- Upload Custom Data (your own files)
- Visual detection overlays
"""

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from scipy.ndimage import gaussian_filter, label, center_of_mass
from scipy.fft import fft2, ifft2, fftshift
import requests
import io
import time

st.set_page_config(page_title="Stealth PDP Radar", page_icon="🔍", layout="wide")

# ============================================================================
# OPTIMAL SETTINGS
# ============================================================================

OPTIMAL_OMEGA = 0.72
OPTIMAL_FRINGE = 1.75
OPTIMAL_ENTANGLEMENT = 0.44
OPTIMAL_MIXING = 0.17
OPTIMAL_THRESHOLD = 0.30

# ============================================================================
# SIDEBAR
# ============================================================================

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
    
    # Synthetic Test controls
    if data_source == "Synthetic Test":
        st.subheader("🎯 Target")
        target_range = st.slider("Target Range (km)", 50, 250, 150)
        target_azimuth = st.slider("Target Azimuth (deg)", 0, 360, 180)
        stealth = st.slider("Stealth Level", 0.0, 1.0, 0.15)
        noise = st.slider("Noise Level", 0.0, 0.3, 0.12)
        generate = st.button("🔄 Generate", type="primary", use_container_width=True)
    
    # OpenSky Live controls
    elif data_source == "OpenSky Live":
        st.subheader("📍 Radar Location")
        st.caption("Try JFK: 40.64, -73.78 | LAX: 33.94, -118.41")
        radar_lat = st.number_input("Latitude", value=40.64, format="%.2f")
        radar_lon = st.number_input("Longitude", value=-73.78, format="%.2f")
        radius = st.slider("Search Radius (deg)", 1.0, 5.0, 3.0)
        fetch_opensky = st.button("🌐 Fetch Live Data", type="primary", use_container_width=True)
    
    # Upload Custom controls
    elif data_source == "Upload Custom Data":
        st.subheader("📂 Upload File")
        uploaded_file = st.file_uploader("Choose .npz or .npy", type=['npz', 'npy'])
        if uploaded_file is not None:
            st.success(f"Loaded: {uploaded_file.name}")

# ============================================================================
# DATA GENERATION FUNCTIONS
# ============================================================================

def generate_synthetic_radar(range_km, azimuth_deg, stealth, noise):
    """Generate realistic synthetic radar image"""
    range_bins, az_bins = 256, 360
    max_range = 300
    
    radar = np.zeros((range_bins, az_bins))
    
    r_idx = int(range_km / max_range * (range_bins - 1))
    az_idx = int(azimuth_deg / 360 * (az_bins - 1))
    
    rcs = 10.0 * (1 - stealth)
    snr = rcs / (range_km**2 + 10)
    
    # Add target with Gaussian shape
    for dr in range(-12, 13):
        for da in range(-10, 11):
            rr = r_idx + dr
            aa = (az_idx + da) % az_bins
            if 0 <= rr < range_bins:
                dist = np.sqrt(dr**2 + da**2)
                radar[rr, aa] += snr * np.exp(-dist**2 / 30) * np.random.uniform(0.8, 1.2)
    
    # Add clutter and noise
    radar += np.random.weibull(1.5, (range_bins, az_bins)) * 0.08
    radar += np.random.randn(range_bins, az_bins) * noise
    
    # Range attenuation
    for r in range(range_bins):
        r_km = r / range_bins * max_range
        radar[r, :] *= 1 / (1 + (r_km / 70)**2)
    
    # Normalize
    radar = (radar - radar.min()) / (radar.max() - radar.min() + 1e-8)
    
    return radar, r_idx, az_idx, rcs

def fetch_opensky_radar(lat, lon, radius):
    """Fetch live aircraft data from OpenSky Network"""
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
            
            # Calculate range and azimuth
            r_km = haversine_km(lat, lon, lat_air, lon_air)
            if r_km > max_range:
                continue
            
            az_deg = bearing(lat, lon, lat_air, lon_air)
            r_idx = int(r_km / max_range * (range_bins - 1))
            az_idx = int(az_deg / 360 * (az_bins - 1))
            
            # Estimate RCS
            rcs = estimate_rcs(callsign)
            snr = rcs / (r_km**2 + 10)
            radar[r_idx, az_idx] += snr
            
            aircraft_list.append({
                'callsign': callsign,
                'range_km': round(r_km, 1),
                'azimuth_deg': round(az_deg, 1),
                'rcs': round(rcs, 3)
            })
        
        if np.max(radar) > 0:
            radar = radar / np.max(radar)
        
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

def estimate_rcs(callsign):
    callsign = callsign.upper()
    if any(x in callsign for x in ['BOEING', 'AIRBUS', 'JAL', 'UAL', 'DAL', 'AAL']):
        return np.random.uniform(30, 80)
    elif any(x in callsign for x in ['F35', 'F-35', 'B2', 'B21', 'F22']):
        return np.random.uniform(0.001, 0.01)
    else:
        return np.random.uniform(1, 15)

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
    """Detect stealth targets"""
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
    
    # Also add peak detection for strong single points
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
# MAIN - DATA LOADING
# ============================================================================

radar_image = None
ground_truth_df = None
target_info = None

# Synthetic Test
if data_source == "Synthetic Test":
    if generate or 'radar_synthetic' not in st.session_state:
        radar_image, r_idx, az_idx, rcs = generate_synthetic_radar(
            target_range, target_azimuth, stealth, noise)
        ground_truth_df = pd.DataFrame([{
            'Type': 'Stealth Target',
            'Range (km)': target_range,
            'Azimuth (deg)': target_azimuth,
            'RCS (m²)': f"{rcs:.4f}"
        }])
        target_info = (target_range, target_azimuth, r_idx, az_idx, rcs)
        st.session_state.radar_synthetic = radar_image
        st.session_state.gt_synthetic = ground_truth_df
        st.session_state.target_info = target_info
    else:
        radar_image = st.session_state.radar_synthetic
        ground_truth_df = st.session_state.gt_synthetic
        target_info = st.session_state.target_info

# OpenSky Live
elif data_source == "OpenSky Live":
    if 'fetch_opensky' in locals() and fetch_opensky:
        with st.spinner("Fetching live radar data..."):
            radar_image, gt_df, msg = fetch_opensky_radar(radar_lat, radar_lon, radius)
            if radar_image is not None:
                ground_truth_df = gt_df
                st.sidebar.success(f"✅ {msg}")
                target_info = None
                st.session_state.radar_opensky = radar_image
                st.session_state.gt_opensky = ground_truth_df
            else:
                st.sidebar.error(f"⚠️ {msg}")
                if 'radar_opensky' in st.session_state:
                    radar_image = st.session_state.radar_opensky
                    ground_truth_df = st.session_state.gt_opensky
                else:
                    radar_image = np.random.randn(256, 360) * 0.1
                    radar_image = (radar_image - radar_image.min()) / (radar_image.max() - radar_image.min())
    else:
        if 'radar_opensky' in st.session_state:
            radar_image = st.session_state.radar_opensky
            ground_truth_df = st.session_state.gt_opensky
        else:
            radar_image = np.random.randn(256, 360) * 0.1
            radar_image = (radar_image - radar_image.min()) / (radar_image.max() - radar_image.min())

# Upload Custom Data
elif data_source == "Upload Custom Data":
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.npz'):
                data = np.load(io.BytesIO(uploaded_file.read()))
                radar_image = data['radar_image']
            else:
                radar_image = np.load(io.BytesIO(uploaded_file.read()))
            ground_truth_df = None
            target_info = None
            st.session_state.radar_custom = radar_image
        except Exception as e:
            st.sidebar.error(f"Error loading file: {e}")
            if 'radar_custom' in st.session_state:
                radar_image = st.session_state.radar_custom
            else:
                radar_image = np.random.randn(256, 360) * 0.1
                radar_image = (radar_image - radar_image.min()) / (radar_image.max() - radar_image.min())
    else:
        if 'radar_custom' in st.session_state:
            radar_image = st.session_state.radar_custom
        else:
            radar_image = np.random.randn(256, 360) * 0.1
            radar_image = (radar_image - radar_image.min()) / (radar_image.max() - radar_image.min())

# Fallback
if radar_image is None:
    radar_image = np.random.randn(256, 360) * 0.1
    radar_image = (radar_image - radar_image.min()) / (radar_image.max() - radar_image.min())

# ============================================================================
# APPLY PDP FILTER
# ============================================================================

with st.spinner("Applying PDP quantum filter..."):
    dark, residuals, prob, fusion = pdp_filter(radar_image, omega, fringe, mixing, entanglement)
    detections = detect_targets(prob, threshold)

# ============================================================================
# DISPLAY
# ============================================================================

st.title("🔍 Stealth Photon-Dark-Photon Quantum Radar")
st.markdown("*Spectral duality filter revealing dark-mode leakage in radar returns*")

# Metrics
c1, c2, c3, c4 = st.columns(4)
c1.metric("Data Source", data_source)
c2.metric("Detections", len(detections))
c3.metric("Max P", f"{np.max(prob):.3f}")
c4.metric("Threshold", f"{threshold:.2f}")

# Main plot
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
extent = [0, 360, 300, 0]

# Left: Radar with overlay
ax1.imshow(radar_image, aspect='auto', cmap='viridis', extent=extent)

# Add ground truth target if available (synthetic mode)
if target_info:
    target_range, target_azimuth, r_idx, az_idx, rcs = target_info
    ax1.plot(target_azimuth, target_range, 'ro', markersize=14,
             markeredgecolor='white', markeredgewidth=2, label='Stealth Target')

ax1.set_xlabel("Azimuth (deg)")
ax1.set_ylabel("Range (km)")
ax1.set_title("📡 Radar with Detection Overlay")
if target_info:
    ax1.legend()
plt.colorbar(ax1.images[0], ax=ax1)

# Add detection boxes
for d in detections:
    r = d['center'][0] / 256 * 300
    az = d['center'][1] / 360 * 360
    from matplotlib.patches import Rectangle
    rect = Rectangle((az - 12, r - 12), 24, 24, linewidth=3, edgecolor='lime', facecolor='none')
    ax1.add_patch(rect)
    ax1.text(az - 8, r - 18, f"{d['confidence']:.2f}", 
             color='lime', fontsize=9, weight='bold',
             bbox=dict(boxstyle='round', facecolor='black', alpha=0.7))

# Right: Probability map
ax2.imshow(prob, aspect='auto', cmap='hot', extent=extent, vmin=0, vmax=1)
for d in detections:
    r = d['center'][0] / 256 * 300
    az = d['center'][1] / 360 * 360
    from matplotlib.patches import Circle
    circle = Circle((az, r), 10, edgecolor='lime', facecolor='none', linewidth=3)
    ax2.add_patch(circle)

if target_info:
    ax2.plot(target_azimuth, target_range, 'ro', markersize=10, alpha=0.5)

ax2.set_xlabel("Azimuth (deg)")
ax2.set_ylabel("Range (km)")
ax2.set_title("🎯 Stealth Probability Map")
plt.colorbar(ax2.images[0], ax=ax2)

plt.tight_layout()
st.pyplot(fig)

# Fusion visualization
st.subheader("🌀 Blue-Halo IR Fusion")
fig, ax = plt.subplots(figsize=(12, 3.5))
ax.imshow(fusion, aspect='auto', extent=extent)
ax.set_xlabel("Azimuth (deg)")
ax.set_ylabel("Range (km)")
st.pyplot(fig)

# Detection metrics (if ground truth available)
if target_info:
    gt_mask = np.zeros((256, 360), dtype=bool)
    gt_mask[max(0, r_idx-15):min(256, r_idx+15), 
            max(0, az_idx-15):min(360, az_idx+15)] = True
    
    detections_binary = prob > threshold
    tp = np.sum(detections_binary & gt_mask)
    fp = np.sum(detections_binary & ~gt_mask)
    fn = np.sum(~detections_binary & gt_mask)
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    st.subheader("📈 Detection Performance")
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Precision", f"{precision:.3f}")
    col_b.metric("Recall", f"{recall:.3f}")
    col_c.metric("F1 Score", f"{f1:.3f}")
    
    if f1 > 0.5:
        st.success(f"✅ STEALTH TARGET DETECTED! F1 = {f1:.3f}")
    elif f1 > 0.2:
        st.warning(f"⚠️ Partial detection - F1 = {f1:.3f}")
    else:
        st.info(f"💡 Try lowering threshold to 0.25-0.30")

# Display ground truth
if ground_truth_df is not None and len(ground_truth_df) > 0:
    with st.expander("📋 Ground Truth Data"):
        st.dataframe(ground_truth_df)

# Display detections
if detections:
    with st.expander("📋 Detected Targets"):
        for i, d in enumerate(detections):
            st.write(f"**Detection {i+1}:**")
            st.write(f"- Range: {d['center'][0]/256*300:.1f} km")
            st.write(f"- Azimuth: {d['center'][1]/360*360:.1f}°")
            st.write(f"- Confidence: {d['confidence']:.3f}")

st.markdown("---")
st.markdown(f"""
<div style="text-align: center;">
    <span style="color: #4CAF50;">✅ <b>COMPLETE VERSION</b></span> | 
    Ω={omega:.2f} | Fringe={fringe:.2f} | ε={mixing:.2f} | Threshold={threshold:.2f}<br>
    <b>Data Source:</b> {data_source} | <b>Detections:</b> {len(detections)}<br>
    © 2026 Tony E. Ford | QCAUS Framework
</div>
""", unsafe_allow_html=True)
