"""
StealthPDPRadar - FIXED WITH WORKING THRESHOLD
"""

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from scipy.ndimage import gaussian_filter, label, center_of_mass
from scipy.fft import fft2, ifft2, fftshift

st.set_page_config(page_title="Stealth PDP Radar", page_icon="🔍", layout="wide")

# ============================================================================
# OPTIMAL SETTINGS
# ============================================================================

OPTIMAL_OMEGA = 0.72
OPTIMAL_FRINGE = 1.75
OPTIMAL_ENTANGLEMENT = 0.44
OPTIMAL_MIXING = 0.17
OPTIMAL_THRESHOLD = 0.35  # Lowered for better detection

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
    
    st.header("🎯 Target")
    target_range = st.slider("Target Range (km)", 50, 250, 150)
    target_azimuth = st.slider("Target Azimuth (deg)", 0, 360, 180)
    stealth = st.slider("Stealth Level", 0.0, 1.0, 0.15)
    noise = st.slider("Noise Level", 0.0, 0.3, 0.12)
    
    generate = st.button("🔄 Generate Radar Data", type="primary", use_container_width=True)

# ============================================================================
# FUNCTIONS
# ============================================================================

def generate_radar(range_km, azimuth_deg, stealth, noise):
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
    """Detect stealth targets using the threshold"""
    binary = prob > threshold
    labeled, num = label(binary)
    
    detections = []
    for i in range(1, num + 1):
        mask = (labeled == i)
        if np.sum(mask) > 20:  # Min size filter
            com = center_of_mass(prob, labeled, i)
            confidence = np.mean(prob[mask])
            detections.append({
                'center': com,
                'confidence': confidence,
                'size': np.sum(mask)
            })
    return detections

# ============================================================================
# MAIN
# ============================================================================

# Generate data
if generate or 'radar' not in st.session_state:
    with st.spinner("Generating radar data..."):
        radar, r_idx, az_idx, rcs = generate_radar(target_range, target_azimuth, stealth, noise)
        dark, residuals, prob, fusion = pdp_filter(radar, omega, fringe, mixing, entanglement)
        detections = detect_targets(prob, threshold)  # Uses the current threshold
        
        st.session_state.radar = radar
        st.session_state.dark = dark
        st.session_state.residuals = residuals
        st.session_state.prob = prob
        st.session_state.fusion = fusion
        st.session_state.detections = detections
        st.session_state.r_idx = r_idx
        st.session_state.az_idx = az_idx
        st.session_state.rcs = rcs
else:
    radar = st.session_state.radar
    dark = st.session_state.dark
    residuals = st.session_state.residuals
    prob = st.session_state.prob
    fusion = st.session_state.fusion
    detections = st.session_state.detections
    r_idx = st.session_state.r_idx
    az_idx = st.session_state.az_idx
    rcs = st.session_state.rcs

# ============================================================================
# DISPLAY
# ============================================================================

st.title("🔍 Stealth Photon-Dark-Photon Quantum Radar")
st.markdown("*Spectral duality filter revealing dark-mode leakage in radar returns*")

# Metrics row
c1, c2, c3, c4 = st.columns(4)
c1.metric("Target RCS", f"{rcs:.4f} m²")
c2.metric("Detections", len(detections))
c3.metric("Max P", f"{np.max(prob):.3f}")
c4.metric("Threshold", f"{threshold:.2f}")

# Main plot
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
extent = [0, 360, 300, 0]

# Left: Radar with overlay
ax1.imshow(radar, aspect='auto', cmap='viridis', extent=extent)
ax1.plot(target_azimuth, target_range, 'ro', markersize=14,
         markeredgecolor='white', markeredgewidth=2, label='Stealth Target')

for d in detections:
    r = d['center'][0] / 256 * 300
    az = d['center'][1] / 360 * 360
    from matplotlib.patches import Rectangle
    rect = Rectangle((az - 12, r - 12), 24, 24, linewidth=3, edgecolor='lime', facecolor='none')
    ax1.add_patch(rect)
    ax1.text(az - 8, r - 18, f"{d['confidence']:.2f}", 
             color='lime', fontsize=9, weight='bold',
             bbox=dict(boxstyle='round', facecolor='black', alpha=0.7))

ax1.set_xlabel("Azimuth (deg)")
ax1.set_ylabel("Range (km)")
ax1.set_title("📡 Radar with Detection Overlay")
ax1.legend()
plt.colorbar(ax1.images[0], ax=ax1)

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

# ============================================================================
# DETECTION METRICS - USING ACTUAL THRESHOLD
# ============================================================================

# Create ground truth mask
gt_mask = np.zeros((256, 360), dtype=bool)
gt_mask[max(0, r_idx-15):min(256, r_idx+15), 
        max(0, az_idx-15):min(360, az_idx+15)] = True

# Use the current threshold for detection
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

# Status message
if f1 > 0.6:
    st.success(f"✅ EXCELLENT! F1 = {f1:.3f} - Stealth target detected!")
elif f1 > 0.3:
    st.warning(f"⚠️ GOOD - F1 = {f1:.3f}")
elif tp > 0:
    st.info(f"✅ Target detected! F1 = {f1:.3f} - Try lowering threshold to 0.30-0.35 for better precision")
else:
    st.info(f"💡 Try lowering threshold to 0.30-0.35")

# Show detection info
if detections:
    with st.expander("📋 Detected Targets"):
        for d in detections:
            st.write(f"- Range: {d['center'][0]/256*300:.1f} km, Azimuth: {d['center'][1]/360*360:.1f}°, Confidence: {d['confidence']:.3f}")

# Ground truth
with st.expander("📋 Ground Truth"):
    st.dataframe(pd.DataFrame([{
        'Type': 'Stealth Target',
        'Range (km)': target_range,
        'Azimuth (deg)': target_azimuth,
        'RCS (m²)': f"{rcs:.4f}",
        'Stealth Level': f"{stealth*100:.0f}%"
    }]))

st.markdown("---")
st.markdown(f"""
<div style="text-align: center; color: #4CAF50;">
    ✅ <b>OPTIMAL SETTINGS</b> | Ω={omega:.2f} | Fringe={fringe:.2f} | ε={mixing:.2f} | Threshold={threshold:.2f}<br>
    Detections: {len(detections)} | F1 Score: {f1:.3f}<br>
    © 2026 Tony E. Ford | QCAUS Framework
</div>
""", unsafe_allow_html=True)
