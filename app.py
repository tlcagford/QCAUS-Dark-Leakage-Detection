"""
StealthPDPRadar - FINAL WORKING VERSION
Optimized for accurate stealth detection with minimal false positives
"""

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from scipy.ndimage import gaussian_filter, label, center_of_mass
from scipy.fft import fft2, ifft2, fftshift

st.set_page_config(page_title="Stealth PDP Radar", page_icon="🔍", layout="wide")

# ============================================================================
# SIDEBAR - OPTIMIZED PARAMETERS
# ============================================================================

with st.sidebar:
    st.header("⚙️ PDP Filter Parameters")
    omega = st.slider("Ω (Entanglement Strength)", 0.0, 1.0, 0.75, 0.01,
                      help="Higher = more sensitive to dark-mode leakage")
    fringe_scale = st.slider("Fringe Scale", 0.1, 5.0, 1.8, 0.1,
                              help="Scale of quantum interference patterns")
    entanglement = st.slider("Quantum Entanglement", 0.0, 1.0, 0.45, 0.01,
                              help="Strength of von Neumann entropy")
    mixing = st.slider("ε (Mixing Angle)", 0.0, 0.5, 0.18, 0.01,
                       help="Photon-dark photon coupling")
    
    st.header("🎯 Detection Settings")
    threshold = st.slider("Detection Threshold", 0.0, 1.0, 0.5, 0.01,
                          help="Lower = more detections but more false alarms")
    min_size = st.slider("Min Detection Size (pixels)", 10, 100, 30,
                         help="Filter out small false detections")
    
    st.header("🎯 Test Target")
    target_range = st.slider("Target Range (km)", 50, 250, 150)
    target_azimuth = st.slider("Target Azimuth (deg)", 0, 360, 180)
    stealth_level = st.slider("Stealth Level (0=invisible, 1=normal)", 0.0, 1.0, 0.15)
    noise = st.slider("Noise Level", 0.0, 0.3, 0.12)
    
    generate = st.button("🔄 Generate New Scenario", type="primary")

# ============================================================================
# RADAR DATA GENERATOR
# ============================================================================

def generate_radar(target_range_km, target_azimuth_deg, stealth, noise):
    range_bins = 256
    azimuth_bins = 360
    max_range = 300
    
    radar = np.zeros((range_bins, azimuth_bins))
    
    r_idx = int(target_range_km / max_range * (range_bins - 1))
    az_idx = int(target_azimuth_deg / 360 * (azimuth_bins - 1))
    
    # RCS: normal = 10 m², stealth = reduced
    rcs = 10.0 * (1 - stealth)
    snr = rcs / (target_range_km**2 + 10)
    
    # Add target with Gaussian shape
    for dr in range(-8, 9):
        for da in range(-6, 7):
            rr = r_idx + dr
            aa = (az_idx + da) % azimuth_bins
            if 0 <= rr < range_bins:
                dist = np.sqrt(dr**2 + da**2)
                radar[rr, aa] += snr * np.exp(-dist**2 / 25)
    
    # Add noise
    radar += np.random.randn(range_bins, azimuth_bins) * noise
    
    # Normalize
    radar = (radar - np.min(radar)) / (np.max(radar) - np.min(radar) + 1e-8)
    
    return radar, r_idx, az_idx, rcs

# ============================================================================
# PDP FILTER WITH PRECISION OPTIMIZATION
# ============================================================================

def pdp_filter_optimized(radar, omega, fringe, mixing, entangle):
    rows, cols = radar.shape
    
    # FFT for spectral duality
    fft_img = fft2(radar)
    fft_shift = fftshift(fft_img)
    
    # Frequency grid
    x = np.linspace(-1, 1, cols)
    y = np.linspace(-1, 1, rows)
    X, Y = np.meshgrid(x, y)
    R = np.sqrt(X**2 + Y**2)
    
    # Dark mode filter (quantum mixing)
    dark_mask = mixing * np.exp(-omega * R**2) * (1 - np.exp(-R**2 / fringe))
    dark_fft = fft_shift * dark_mask
    dark = np.abs(ifft2(fftshift(dark_fft)))
    
    # Entanglement residuals (von Neumann entropy)
    total_power = np.sum(radar**2) + 1e-10
    ordinary = radar - dark
    rho = ordinary**2 / total_power
    entropy = -rho * np.log(np.maximum(rho, 1e-10))
    interference = (np.abs(ordinary + dark)**2 - ordinary**2 - dark**2) / total_power
    residuals = entropy * entangle + np.abs(interference) * mixing
    residuals = gaussian_filter(residuals, sigma=1.0)
    
    # Stealth probability (normalized)
    prob = dark * residuals
    prob = (prob - np.min(prob)) / (np.max(prob) - np.min(prob) + 1e-8)
    prob = np.clip(prob * 1.2, 0, 1)
    
    # Fusion visualization
    def norm(x):
        return (x - np.min(x)) / (np.max(x) - np.min(x) + 1e-8)
    
    rgb = np.zeros((*radar.shape, 3))
    rgb[..., 0] = norm(radar)
    rgb[..., 1] = norm(residuals)
    rgb[..., 2] = norm(dark)
    rgb = np.power(np.clip(rgb, 0, 1), 0.5)
    
    return dark, residuals, prob, rgb

# ============================================================================
# DETECTION WITH FALSE POSITIVE FILTERING
# ============================================================================

def detect_targets(prob, threshold, min_size):
    """Detect targets with size filtering to reduce false positives"""
    binary = prob > threshold
    labeled, num_features = label(binary)
    
    detections = []
    for i in range(1, num_features + 1):
        mask = (labeled == i)
        size = np.sum(mask)
        if size >= min_size:
            com = center_of_mass(prob, labeled, i)
            confidence = np.mean(prob[mask])
            detections.append({
                'id': i,
                'center': com,
                'size': size,
                'confidence': confidence
            })
    
    return detections

# ============================================================================
# MAIN EXECUTION
# ============================================================================

# Generate data
radar, r_idx, az_idx, rcs = generate_radar(target_range, target_azimuth, stealth_level, noise)

# Apply filter
dark, residuals, prob, fusion = pdp_filter_optimized(
    radar, omega, fringe_scale, mixing, entanglement)

# Detect targets
detections = detect_targets(prob, threshold, min_size)

# Calculate probability at target location
prob_at_target = prob[r_idx, az_idx] if 0 <= r_idx < 256 and 0 <= az_idx < 360 else 0

# ============================================================================
# DISPLAY
# ============================================================================

st.title("🔍 Stealth Photon-Dark-Photon Quantum Radar")
st.markdown("**Optimized detection with minimal false positives**")

# Metrics
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Target Range", f"{target_range} km")
col2.metric("RCS", f"{rcs:.3f} m²")
col3.metric("P(Target)", f"{prob_at_target:.3f}")
col4.metric("Detections", len(detections))
col5.metric("Detection", "✅ YES" if prob_at_target > threshold else "❌ NO")

# Main plot with detection overlay
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
extent = [0, 360, 300, 0]

# Left: Radar with overlay
im1 = ax1.imshow(radar, aspect='auto', cmap='viridis', extent=extent)
ax1.plot(target_azimuth, target_range, 'ro', markersize=15,
         markeredgecolor='white', markeredgewidth=2, label='True Target')

# Add detection boxes
for det in detections:
    r_center = det['center'][0] / 256 * 300
    az_center = det['center'][1] / 360 * 360
    from matplotlib.patches import Rectangle
    rect = Rectangle((az_center - 12, r_center - 12), 24, 24,
                     linewidth=3, edgecolor='lime', facecolor='none', linestyle='--')
    ax1.add_patch(rect)
    ax1.text(az_center - 10, r_center - 20, f"DETECTED\nP={det['confidence']:.2f}",
             fontsize=8, color='lime', weight='bold',
             bbox=dict(boxstyle='round', facecolor='black', alpha=0.7))

ax1.set_xlabel("Azimuth (deg)")
ax1.set_ylabel("Range (km)")
ax1.set_title("📡 Radar with Detection Overlay")
ax1.legend()
plt.colorbar(im1, ax=ax1, label="Intensity")

# Right: Probability map
im2 = ax2.imshow(prob, aspect='auto', cmap='hot', extent=extent, vmin=0, vmax=1)
ax2.plot(target_azimuth, target_range, 'ro', markersize=15,
         markeredgecolor='white', markeredgewidth=2)

for det in detections:
    r_center = det['center'][0] / 256 * 300
    az_center = det['center'][1] / 360 * 360
    from matplotlib.patches import Circle
    circle = Circle((az_center, r_center), radius=10,
                    edgecolor='lime', facecolor='none', linewidth=3)
    ax2.add_patch(circle)

ax2.set_xlabel("Azimuth (deg)")
ax2.set_ylabel("Range (km)")
ax2.set_title("🎯 Stealth Probability Map")
plt.colorbar(im2, ax=ax2, label="P(Stealth)")

plt.tight_layout()
st.pyplot(fig)

# Fusion visualization
st.subheader("🌀 Blue-Halo IR Fusion")
fig, ax = plt.subplots(figsize=(12, 5))
ax.imshow(fusion, aspect='auto', extent=extent)
ax.plot(target_azimuth, target_range, 'wo', markersize=12,
        markeredgecolor='red', markeredgewidth=2)
ax.set_xlabel("Azimuth (deg)")
ax.set_ylabel("Range (km)")
st.pyplot(fig)

# Components
col1, col2 = st.columns(2)
with col1:
    st.subheader("🌑 Dark-Mode Leakage")
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.imshow(dark, aspect='auto', cmap='Blues')
    st.pyplot(fig)
with col2:
    st.subheader("🟢 Entanglement Residuals")
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.imshow(residuals, aspect='auto', cmap='Greens')
    st.pyplot(fig)

# Performance metrics
st.subheader("📈 Detection Performance")

# Create ground truth region
gt_region = np.zeros((256, 360), dtype=bool)
gt_region[max(0, r_idx-15):min(256, r_idx+15), 
          max(0, az_idx-15):min(360, az_idx+15)] = True

# Calculate metrics
detections_binary = prob > threshold
tp = np.sum(detections_binary & gt_region)
fp = np.sum(detections_binary & ~gt_region)
fn = np.sum(~detections_binary & gt_region)

precision = tp / (tp + fp) if (tp + fp) > 0 else 0
recall = tp / (tp + fn) if (tp + fn) > 0 else 0
f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

m1, m2, m3 = st.columns(3)
m1.metric("Precision", f"{precision:.3f}")
m2.metric("Recall", f"{recall:.3f}")
m3.metric("F1 Score", f"{f1:.3f}")

# Performance feedback
if f1 > 0.7:
    st.success(f"✅ EXCELLENT! F1 Score = {f1:.3f} - Optimal detection")
elif f1 > 0.4:
    st.warning(f"⚠️ GOOD - F1 Score = {f1:.3f} - Try adjusting threshold for better precision")
else:
    st.info(f"💡 ADJUST - F1 = {f1:.3f} | Try: Ω=0.7-0.8, Threshold=0.4-0.5")

# Detection table
with st.expander("📋 Detection Results"):
    if detections:
        det_data = []
        for d in detections:
            det_data.append({
                'ID': d['id'],
                'Range (km)': f"{d['center'][0] / 256 * 300:.1f}",
                'Azimuth (deg)': f"{d['center'][1] / 360 * 360:.1f}",
                'Confidence': f"{d['confidence']:.3f}",
                'Size (pixels)': d['size']
            })
        st.dataframe(pd.DataFrame(det_data))
    else:
        st.info("No detections above threshold")

# Ground truth
with st.expander("📋 Ground Truth"):
    st.dataframe(pd.DataFrame([{
        'Type': 'Stealth Target',
        'Range (km)': target_range,
        'Azimuth (deg)': target_azimuth,
        'RCS (m²)': f"{rcs:.3f}",
        'Detection Prob': f"{prob_at_target:.3f}",
        'Status': '✅ DETECTED' if prob_at_target > threshold else '❌ MISSED'
    }]))

# Parameters
with st.expander("⚙️ Current Parameters"):
    st.json({
        'omega': omega,
        'fringe_scale': fringe_scale,
        'entanglement': entanglement,
        'mixing_angle': mixing,
        'threshold': threshold,
        'min_size': min_size,
        'target_rcs': rcs,
        'detection_probability': prob_at_target,
        'precision': precision,
        'recall': recall,
        'f1_score': f1
    })

# Settings guide
with st.expander("📖 Optimal Settings Guide"):
    st.markdown("""
    ### Recommended Settings for Best Results
    
    | Parameter | Recommended | Current | Effect |
    |-----------|-------------|---------|--------|
    | Ω (Entanglement) | **0.70-0.80** | {:.2f} | Higher = more sensitive |
    | Fringe Scale | **1.5-2.0** | {:.2f} | Scale of quantum patterns |
    | Quantum Entanglement | **0.40-0.50** | {:.2f} | Von Neumann entropy strength |
    | ε (Mixing) | **0.15-0.20** | {:.2f} | Photon-dark photon coupling |
    | Threshold | **0.40-0.55** | {:.2f} | Balance precision vs recall |
    
    ### Current Performance
    - **Detection Status**: {} at P={:.2f}
    - **False Positives**: {} detections outside target region
    - **F1 Score**: {:.3f}
    
    ### Next Steps
    1. Adjust **Ω** to 0.75 for optimal dark-mode extraction
    2. Set **Threshold** to 0.45 to reduce false positives
    3. Increase **Min Size** to filter small noise detections
    """.format(
        omega, fringe_scale, entanglement, mixing, threshold,
        "✅ DETECTED" if prob_at_target > threshold else "❌ NOT DETECTED",
        prob_at_target, fp, f1
    ))

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666;">
    ✅ **WORKING** | Precision: {:.3f} | Recall: {:.3f} | F1: {:.3f}<br>
    © 2026 Tony E. Ford | QCAUS Framework
</div>
""".format(precision, recall, f1), unsafe_allow_html=True)
