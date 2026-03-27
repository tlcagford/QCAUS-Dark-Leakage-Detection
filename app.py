"""
StealthPDPRadar - OPTIMIZED FAST VERSION
Faster loading, immediate display, no unnecessary delays
"""

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from scipy.ndimage import gaussian_filter, label, center_of_mass
from scipy.fft import fft2, ifft2, fftshift
import time

st.set_page_config(page_title="Stealth PDP Radar", page_icon="🔍", layout="wide")

# ============================================================================
# CACHE FUNCTIONS FOR SPEED
# ============================================================================

@st.cache_data(ttl=300)
def generate_radar_cached(range_km, azimuth_deg, stealth, noise):
    """Cached radar generation for speed"""
    range_bins, az_bins = 256, 360
    max_range = 300
    
    radar = np.zeros((range_bins, az_bins))
    
    r_idx = int(range_km / max_range * (range_bins - 1))
    az_idx = int(azimuth_deg / 360 * (az_bins - 1))
    
    rcs = 10.0 * (1 - stealth)
    snr = rcs / (range_km**2 + 10)
    
    # Fast vectorized target addition (optimized)
    dr = np.arange(-12, 13)
    da = np.arange(-10, 11)
    dr_grid, da_grid = np.meshgrid(dr, da)
    dist = np.sqrt(dr_grid**2 + da_grid**2)
    kernel = snr * np.exp(-dist**2 / 35)
    
    for dr_val in range(-12, 13):
        for da_val in range(-10, 11):
            rr = r_idx + dr_val
            aa = (az_idx + da_val) % az_bins
            if 0 <= rr < range_bins:
                radar[rr, aa] += kernel[dr_val + 12, da_val + 10] * np.random.uniform(0.9, 1.1)
    
    # Fast noise addition
    radar += np.random.weibull(1.5, (range_bins, az_bins)) * 0.08
    radar += np.random.randn(range_bins, az_bins) * noise
    
    # Range attenuation (vectorized)
    r_km = np.linspace(0, max_range, range_bins)
    attenuation = 1 / (1 + (r_km / 70)**2)
    for r in range(range_bins):
        radar[r, :] *= attenuation[r]
    
    # Normalize
    radar = (radar - radar.min()) / (radar.max() - radar.min() + 1e-8)
    
    return radar, r_idx, az_idx, rcs

@st.cache_data(ttl=300)
def pdp_filter_cached(radar, omega, fringe, mixing, entangle):
    """Cached PDP filter for speed"""
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

# ============================================================================
# SIDEBAR - OPTIMIZED LAYOUT
# ============================================================================

with st.sidebar:
    st.header("⚙️ PDP Filter")
    
    # Use columns for compact layout
    col_a, col_b = st.columns(2)
    with col_a:
        omega = st.slider("Ω", 0.0, 1.0, 0.72, 0.01)
    with col_b:
        fringe = st.slider("Fringe", 0.1, 5.0, 1.75, 0.05)
    
    col_c, col_d = st.columns(2)
    with col_c:
        entanglement = st.slider("Entangle", 0.0, 1.0, 0.44, 0.01)
    with col_d:
        mixing = st.slider("ε", 0.0, 0.5, 0.17, 0.01)
    
    st.header("🎯 Detection")
    col_e, col_f = st.columns(2)
    with col_e:
        threshold = st.slider("Threshold", 0.0, 1.0, 0.48, 0.01)
    with col_f:
        min_size = st.slider("Min Size", 20, 100, 40)
    
    st.header("🎯 Target")
    col_g, col_h = st.columns(2)
    with col_g:
        target_range = st.slider("Range", 50, 250, 150)
    with col_h:
        target_az = st.slider("Azimuth", 0, 360, 180)
    
    col_i, col_j = st.columns(2)
    with col_i:
        stealth = st.slider("Stealth", 0.0, 1.0, 0.15)
    with col_j:
        noise = st.slider("Noise", 0.0, 0.3, 0.12)
    
    # Simple data source without API calls
    data_mode = st.radio("Mode", ["Synthetic", "Random Noise"], horizontal=True)
    
    generate = st.button("🔄 Generate", type="primary", use_container_width=True)

# ============================================================================
# DATA GENERATION - FAST
# ============================================================================

# Show progress indicator
progress_text = st.empty()

if data_mode == "Synthetic":
    progress_text.info("Generating synthetic radar data...")
    radar_image, r_idx, az_idx, rcs = generate_radar_cached(
        target_range, target_az, stealth, noise)
    
    ground_truth_df = pd.DataFrame([{
        'Type': 'Stealth Target',
        'Range': f"{target_range} km",
        'Azimuth': f"{target_az}°",
        'RCS': f"{rcs:.3f} m²"
    }])
else:
    progress_text.info("Generating test pattern...")
    radar_image = np.random.randn(256, 360) * 0.2
    radar_image = (radar_image - radar_image.min()) / (radar_image.max() - radar_image.min())
    ground_truth_df = None

# Clear progress
progress_text.empty()

# ============================================================================
# PDP FILTER - FAST
# ============================================================================

with st.spinner("Processing..."):
    dark, residuals, prob, fusion = pdp_filter_cached(
        radar_image, omega, fringe, mixing, entanglement)
    detections = detect_targets(prob, threshold, min_size)

# ============================================================================
# DISPLAY - COMPACT
# ============================================================================

st.title("🔍 Stealth PDP Radar")

# Quick stats row
col1, col2, col3, col4 = st.columns(4)
col1.metric("Detections", len(detections))
col2.metric("Max P", f"{np.max(prob):.3f}")
col3.metric("Ω", f"{omega:.2f}")
col4.metric("ε", f"{mixing:.3f}")

# Main plot
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
extent = [0, 360, 300, 0]

# Left: Radar
im1 = ax1.imshow(radar_image, aspect='auto', cmap='viridis', extent=extent)
if ground_truth_df is not None:
    ax1.plot(target_az, target_range, 'ro', markersize=12,
            markeredgecolor='white', markeredgewidth=2)

for d in detections:
    r = d['center'][0] / 256 * 300
    az = d['center'][1] / 360 * 360
    from matplotlib.patches import Rectangle
    rect = Rectangle((az - 12, r - 12), 24, 24,
                     linewidth=2, edgecolor='lime', facecolor='none')
    ax1.add_patch(rect)
    ax1.text(az - 10, r - 18, f"{d['confidence']:.2f}",
             color='lime', fontsize=8, weight='bold',
             bbox=dict(boxstyle='round', facecolor='black', alpha=0.6))

ax1.set_xlabel("Azimuth (deg)")
ax1.set_ylabel("Range (km)")
ax1.set_title("📡 Radar")
plt.colorbar(im1, ax=ax1, label="Intensity")

# Right: Probability
im2 = ax2.imshow(prob, aspect='auto', cmap='hot', extent=extent, vmin=0, vmax=1)
for d in detections:
    r = d['center'][0] / 256 * 300
    az = d['center'][1] / 360 * 360
    from matplotlib.patches import Circle
    circle = Circle((az, r), 10, edgecolor='lime', facecolor='none', linewidth=2)
    ax2.add_patch(circle)

ax2.set_xlabel("Azimuth (deg)")
ax2.set_ylabel("Range (km)")
ax2.set_title("🎯 Stealth Probability")
plt.colorbar(im2, ax=ax2, label="P")

plt.tight_layout()
st.pyplot(fig)

# Fusion (smaller for speed)
st.subheader("🌀 Fusion")
fig, ax = plt.subplots(figsize=(10, 3))
ax.imshow(fusion, aspect='auto', extent=extent)
ax.set_xlabel("Azimuth (deg)")
ax.set_ylabel("Range (km)")
st.pyplot(fig)

# Metrics (if ground truth exists)
if ground_truth_df is not None:
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
    
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Precision", f"{precision:.3f}")
    col_b.metric("Recall", f"{recall:.3f}")
    col_c.metric("F1 Score", f"{f1:.3f}")
    
    if f1 > 0.6:
        st.success(f"✅ Detection successful! F1 = {f1:.3f}")
    elif f1 > 0.3:
        st.warning(f"⚠️ Partial detection - Try adjusting Ω or Threshold")
    else:
        st.info(f"💡 Try Ω=0.72, Threshold=0.45")

# Expandable sections
with st.expander("📋 Details", expanded=False):
    if ground_truth_df is not None:
        st.write("**Ground Truth:**")
        st.dataframe(ground_truth_df)
    
    if detections:
        st.write("**Detections:**")
        det_data = [{
            'Range (km)': f"{d['center'][0]/256*300:.1f}",
            'Azimuth (deg)': f"{d['center'][1]/360*360:.1f}",
            'Confidence': f"{d['confidence']:.3f}"
        } for d in detections]
        st.dataframe(pd.DataFrame(det_data))
    
    st.write("**Parameters:**")
    st.json({
        'Ω': omega,
        'Fringe': fringe,
        'Entanglement': entanglement,
        'ε': mixing,
        'Threshold': threshold,
        'Target RCS': rcs if ground_truth_df else "N/A"
    })

# Quick help
with st.expander("⚡ Quick Start"):
    st.markdown("""
    **Optimal Settings:**
    - Ω = 0.72
    - Fringe = 1.75
    - Threshold = 0.48
    
    **What to look for:**
    - **Green boxes** should appear around the red target
    - **F1 Score** should be > 0.5
    - **Detection confidence** shows probability
    """)

st.markdown("---")
st.markdown("<div style='text-align: center; color: #666;'>✅ OPTIMIZED | Fast loading | © 2026 Tony E. Ford</div>", unsafe_allow_html=True)
