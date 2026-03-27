"""
StealthPDPRadar - COMPLETE WORKING VERSION WITH VISUAL OVERLAYS
Detects and highlights stealth targets with bounding boxes and confidence scores
"""

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Circle, Rectangle
import pandas as pd
from scipy.ndimage import gaussian_filter, label, center_of_mass
from scipy.fft import fft2, ifft2, fftshift

# Page config
st.set_page_config(page_title="Stealth PDP Radar", page_icon="🔍", layout="wide")

st.title("🔍 Stealth Photon-Dark-Photon Quantum Radar")
st.markdown("**Spectral duality filter** with **visual overlay detection** highlighting stealth objects")

# ============================================================================
# SIDEBAR CONTROLS
# ============================================================================

with st.sidebar:
    st.header("⚙️ PDP Filter Parameters")
    omega = st.slider("Ω (Entanglement Strength)", 0.0, 1.0, 0.75, 0.01)
    fringe_scale = st.slider("Fringe Scale", 0.1, 5.0, 1.8, 0.1)
    entanglement_strength = st.slider("Quantum Entanglement", 0.0, 1.0, 0.45, 0.01)
    mixing_angle = st.slider("ε (Mixing Angle)", 0.0, 0.5, 0.18, 0.01)
    
    st.header("🎯 Target Configuration")
    num_stealth = st.slider("Number of Stealth Targets", 1, 5, 2)
    num_normal = st.slider("Number of Normal Targets", 0, 5, 2)
    stealth_level = st.slider("Stealth Effectiveness (RCS Reduction)", 0.0, 1.0, 0.15, 0.01)
    
    st.header("🌊 Environment")
    noise_level = st.slider("Noise Level", 0.0, 0.5, 0.12, 0.01)
    clutter_level = st.slider("Clutter Level", 0.0, 0.3, 0.08, 0.01)
    
    st.header("🎨 Detection Settings")
    detection_threshold = st.slider("Detection Threshold", 0.0, 1.0, 0.45, 0.01)
    show_all_targets = st.checkbox("Show All Targets (Red=Stealth, Blue=Normal)", value=True)
    
    generate_button = st.button("🔄 Generate New Scenario", type="primary", use_container_width=True)

# ============================================================================
# RADAR DATA GENERATOR
# ============================================================================

def generate_radar_scenario(num_stealth, num_normal, stealth_level, noise, clutter):
    """Generate realistic radar image with multiple targets"""
    
    range_bins = 256
    azimuth_bins = 360
    max_range_km = 300
    
    radar = np.zeros((range_bins, azimuth_bins))
    targets = []
    
    # Normal RCS baseline (m²)
    normal_rcs = 10.0
    
    # Generate stealth targets (low RCS)
    for i in range(num_stealth):
        r_km = np.random.uniform(50, 250)
        az_deg = np.random.uniform(0, 360)
        
        r_idx = int(r_km / max_range_km * (range_bins - 1))
        az_idx = int(az_deg / 360 * (azimuth_bins - 1))
        
        # Stealth target RCS (reduced)
        rcs = normal_rcs * (1 - stealth_level * np.random.uniform(0.8, 1.2))
        
        # Radar equation
        snr = rcs / (r_km**2 + 10)
        
        # Add target with Gaussian shape
        for dr in range(-10, 11):
            for da in range(-8, 9):
                rr = r_idx + dr
                aa = (az_idx + da) % azimuth_bins
                if 0 <= rr < range_bins:
                    dist = np.sqrt(dr**2 + da**2)
                    intensity = snr * np.exp(-dist**2 / 30) * np.random.uniform(0.7, 1.3)
                    radar[rr, aa] += intensity
        
        targets.append({
            'type': 'stealth',
            'range_km': r_km,
            'azimuth_deg': az_deg,
            'range_idx': r_idx,
            'azimuth_idx': az_idx,
            'rcs': rcs,
            'confidence': 0.0  # Will be filled by detector
        })
    
    # Generate normal targets (high RCS)
    for i in range(num_normal):
        r_km = np.random.uniform(50, 250)
        az_deg = np.random.uniform(0, 360)
        
        r_idx = int(r_km / max_range_km * (range_bins - 1))
        az_idx = int(az_deg / 360 * (azimuth_bins - 1))
        
        # Normal target RCS
        rcs = normal_rcs * np.random.uniform(0.8, 1.5)
        
        snr = rcs / (r_km**2 + 10)
        
        for dr in range(-8, 9):
            for da in range(-6, 7):
                rr = r_idx + dr
                aa = (az_idx + da) % azimuth_bins
                if 0 <= rr < range_bins:
                    dist = np.sqrt(dr**2 + da**2)
                    intensity = snr * np.exp(-dist**2 / 25) * np.random.uniform(0.8, 1.2)
                    radar[rr, aa] += intensity
        
        targets.append({
            'type': 'normal',
            'range_km': r_km,
            'azimuth_deg': az_deg,
            'range_idx': r_idx,
            'azimuth_idx': az_idx,
            'rcs': rcs,
            'confidence': 0.0
        })
    
    # Add clutter and noise
    weibull_clutter = np.random.weibull(1.5, (range_bins, azimuth_bins)) * clutter
    radar += weibull_clutter
    
    thermal_noise = np.random.randn(range_bins, azimuth_bins) * noise
    radar += thermal_noise
    
    # Range attenuation
    for r in range(range_bins):
        r_km = r / range_bins * max_range_km
        attenuation = 1 / (1 + (r_km / 80)**2)
        radar[r, :] *= attenuation
    
    # Normalize
    radar = radar - np.min(radar)
    radar = radar / (np.max(radar) + 1e-8)
    
    return radar, targets

# ============================================================================
# PDP FILTER WITH DETECTION
# ============================================================================

def pdp_detector(radar_image, omega, fringe_scale, mixing_angle, entanglement_strength, threshold):
    """Apply PDP filter and detect stealth targets with bounding boxes"""
    
    # Step 1: Spectral Duality
    fft_image = fft2(radar_image)
    fft_shifted = fftshift(fft_image)
    
    rows, cols = radar_image.shape
    x = np.linspace(-1, 1, cols)
    y = np.linspace(-1, 1, rows)
    X, Y = np.meshgrid(x, y)
    R = np.sqrt(X**2 + Y**2)
    
    # Dark mode filter
    dark_mask = mixing_angle * np.exp(-omega * R**2) * (1 - np.exp(-R**2 / fringe_scale))
    dark_fft = fft_shifted * dark_mask
    dark_mode = np.abs(ifft2(fftshift(dark_fft)))
    
    # Step 2: Entanglement Residuals
    eps = 1e-10
    total_power = np.sum(radar_image**2) + eps
    ordinary_mode = radar_image - dark_mode
    
    rho = ordinary_mode**2 / total_power
    rho_safe = np.maximum(rho, eps)
    entropy = -rho_safe * np.log(rho_safe)
    
    interference = (np.abs(ordinary_mode + dark_mode)**2 - ordinary_mode**2 - dark_mode**2) / total_power
    residuals = entropy * entanglement_strength + np.abs(interference) * mixing_angle
    residuals = gaussian_filter(residuals, sigma=1.0)
    
    # Step 3: Stealth Probability
    stealth_prob = dark_mode * residuals
    stealth_prob = stealth_prob / (np.max(stealth_prob) + 1e-8)
    stealth_prob = np.clip(stealth_prob * 1.5, 0, 1)
    
    # Step 4: Detect and label regions
    binary_detections = stealth_prob > threshold
    labeled, num_features = label(binary_detections)
    
    detections = []
    for i in range(1, num_features + 1):
        mask = (labeled == i)
        if np.sum(mask) > 20:  # Minimum size filter
            # Get bounding box
            rows_idx, cols_idx = np.where(mask)
            min_row, max_row = np.min(rows_idx), np.max(rows_idx)
            min_col, max_col = np.min(cols_idx), np.max(cols_idx)
            
            # Center of mass
            com = center_of_mass(stealth_prob, labeled, i)
            
            # Average confidence
            confidence = np.mean(stealth_prob[mask])
            
            # Convert to km and degrees
            max_range_km = 300
            center_range_km = com[0] / rows * max_range_km
            center_az_deg = com[1] / cols * 360
            
            detections.append({
                'id': i,
                'bbox': (min_row, max_row, min_col, max_col),
                'center': com,
                'center_range_km': center_range_km,
                'center_az_deg': center_az_deg,
                'confidence': confidence,
                'size_pixels': np.sum(mask)
            })
    
    return dark_mode, residuals, stealth_prob, detections

# ============================================================================
# VISUALIZATION WITH OVERLAYS
# ============================================================================

def plot_with_overlays(radar_image, stealth_prob, detections, targets, show_all_targets):
    """Create visualization with bounding boxes and highlights"""
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    
    max_range_km = 300
    extent = [0, 360, max_range_km, 0]
    
    # Left: Original radar with overlays
    im1 = ax1.imshow(radar_image, aspect='auto', cmap='viridis', extent=extent)
    ax1.set_xlabel("Azimuth (deg)")
    ax1.set_ylabel("Range (km)")
    ax1.set_title("📡 Radar Image with Detection Overlay")
    plt.colorbar(im1, ax=ax1, label="Intensity")
    
    # Add detection bounding boxes
    for det in detections:
        min_row, max_row, min_col, max_col = det['bbox']
        
        # Convert to km and degrees
        y_min = min_row / 256 * max_range_km
        y_max = max_row / 256 * max_range_km
        x_min = min_col / 360 * 360
        x_max = max_col / 360 * 360
        
        # Create rectangle patch
        rect = Rectangle((x_min, y_min), x_max - x_min, y_max - y_min,
                         linewidth=3, edgecolor='lime', facecolor='none',
                         linestyle='--')
        ax1.add_patch(rect)
        
        # Add confidence label
        ax1.text(x_min, y_min - 10, f"P={det['confidence']:.2f}",
                fontsize=10, color='lime', weight='bold',
                bbox=dict(boxstyle='round', facecolor='black', alpha=0.7))
    
    # Add ground truth markers
    if show_all_targets:
        for target in targets:
            color = 'red' if target['type'] == 'stealth' else 'blue'
            marker = 'o' if target['type'] == 'stealth' else 's'
            ax1.plot(target['azimuth_deg'], target['range_km'], 
                    marker=marker, color=color, markersize=12,
                    markeredgecolor='white', markeredgewidth=2,
                    label=f"{target['type'].upper()}" if target == targets[0] else "")
        
        ax1.legend(loc='upper right')
    
    # Right: Stealth Probability Map with detection highlights
    im2 = ax2.imshow(stealth_prob, aspect='auto', cmap='hot', extent=extent, vmin=0, vmax=1)
    ax2.set_xlabel("Azimuth (deg)")
    ax2.set_ylabel("Range (km)")
    ax2.set_title("🎯 Stealth Probability Map")
    plt.colorbar(im2, ax=ax2, label="P(Stealth)")
    
    # Add detection circles
    for det in detections:
        circle = Circle((det['center_az_deg'], det['center_range_km']),
                        radius=8, edgecolor='lime', facecolor='none',
                        linewidth=3, linestyle='-')
        ax2.add_patch(circle)
        
        ax2.text(det['center_az_deg'] - 10, det['center_range_km'] - 15,
                f"STEALTH", fontsize=9, color='lime', weight='bold',
                bbox=dict(boxstyle='round', facecolor='black', alpha=0.8))
    
    plt.tight_layout()
    return fig

# ============================================================================
# MAIN EXECUTION
# ============================================================================

# Initialize session state
if 'radar_image' not in st.session_state or generate_button:
    with st.spinner("Generating radar scenario..."):
        radar_image, targets = generate_radar_scenario(
            num_stealth, num_normal, stealth_level, noise_level, clutter_level
        )
        st.session_state.radar_image = radar_image
        st.session_state.targets = targets

# Apply PDP filter
with st.spinner("Applying PDP quantum filter..."):
    dark_mode, residuals, stealth_prob, detections = pdp_detector(
        st.session_state.radar_image, omega, fringe_scale, mixing_angle,
        entanglement_strength, detection_threshold
    )

# Update target confidence
for target in st.session_state.targets:
    for det in detections:
        dist = np.sqrt((target['range_km'] - det['center_range_km'])**2 + 
                       (target['azimuth_deg'] - det['center_az_deg'])**2)
        if dist < 20:
            target['confidence'] = det['confidence']

# ============================================================================
# DISPLAY RESULTS
# ============================================================================

# Summary metrics
stealth_targets = [t for t in st.session_state.targets if t['type'] == 'stealth']
detected_stealth = [t for t in stealth_targets if t['confidence'] > 0.3]
detection_rate = len(detected_stealth) / len(stealth_targets) if stealth_targets else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Stealth Targets", len(stealth_targets))
col2.metric("Detected", len(detected_stealth))
col3.metric("Detection Rate", f"{detection_rate:.0%}")
col4.metric("Confidence", f"{np.mean([d['confidence'] for d in detections]):.2f}" if detections else "0.00")

# Main visualization with overlays
st.subheader("🔍 Detection Overlay - Stealth Targets Highlighted")
fig = plot_with_overlays(st.session_state.radar_image, stealth_prob, 
                         detections, st.session_state.targets, show_all_targets)
st.pyplot(fig)

# Component analysis
col1, col2 = st.columns(2)
with col1:
    st.subheader("🌑 Dark-Mode Leakage")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(dark_mode, aspect='auto', cmap='Blues')
    st.pyplot(fig)

with col2:
    st.subheader("🟢 Entanglement Residuals")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(residuals, aspect='auto', cmap='Greens')
    st.pyplot(fig)

# Detection table
st.subheader("📋 Detection Results")
detection_data = []
for det in detections:
    detection_data.append({
        'ID': det['id'],
        'Range (km)': f"{det['center_range_km']:.1f}",
        'Azimuth (deg)': f"{det['center_az_deg']:.1f}",
        'Confidence': f"{det['confidence']:.3f}",
        'Size (pixels)': det['size_pixels']
    })

if detection_data:
    st.dataframe(pd.DataFrame(detection_data))
else:
    st.info("No detections above threshold. Try lowering the detection threshold or adjusting filter parameters.")

# Ground truth comparison
st.subheader("🎯 Ground Truth vs Detection")
comparison_data = []
for target in st.session_state.targets:
    detected = "✅ DETECTED" if target['confidence'] > 0.3 else "❌ MISSED"
    comparison_data.append({
        'Type': target['type'].upper(),
        'Range (km)': f"{target['range_km']:.1f}",
        'Azimuth (deg)': f"{target['azimuth_deg']:.1f}",
        'RCS (m²)': f"{target['rcs']:.3f}",
        'Detection': detected,
        'Confidence': f"{target['confidence']:.3f}" if target['confidence'] > 0 else "-"
    })
st.dataframe(pd.DataFrame(comparison_data))

# Performance analysis
if detection_rate > 0.7:
    st.success(f"✅ Excellent! Detected {len(detected_stealth)}/{len(stealth_targets)} stealth targets with {detection_rate:.0%} success rate!")
elif detection_rate > 0.4:
    st.warning(f"⚠️ Partial detection: {len(detected_stealth)}/{len(stealth_targets)} stealth targets detected. Try increasing Ω to 0.8-0.9.")
else:
    st.info(f"💡 Low detection rate ({detection_rate:.0%}). Recommended settings: Ω=0.75-0.85, Fringe Scale=1.5-2.0, Threshold=0.4-0.5")

# Parameters
with st.expander("⚙️ Current Parameters"):
    st.json({
        'omega': omega,
        'fringe_scale': fringe_scale,
        'entanglement_strength': entanglement_strength,
        'mixing_angle': mixing_angle,
        'detection_threshold': detection_threshold,
        'detections_found': len(detections),
        'stealth_targets': len(stealth_targets),
        'detection_rate': detection_rate
    })

# Theory
with st.expander("📖 How the Visual Overlay Detection Works"):
    st.markdown("""
    ### Visual Overlay Detection System
    
    1. **PDP Quantum Filter** extracts dark-mode leakage from radar returns
    2. **Connected Component Analysis** identifies stealth candidate regions
    3. **Bounding Box Generation** creates visual overlays around detected objects
    4. **Confidence Scoring** assigns probability (0-1) for each detection
    
    ### Color Coding
    
    - **Green Boxes**: PDP filter detections (stealth candidates)
    - **Red Circles**: Ground truth stealth targets (for validation)
    - **Blue Squares**: Ground truth normal targets
    - **Confidence Text**: Detection probability score
    
    ### Optimal Detection Settings
    
    | Parameter | Recommended | Current |
    |-----------|-------------|---------|
    | Ω (Entanglement) | 0.7-0.8 | {:.2f} |
    | Fringe Scale | 1.5-2.0 | {:.2f} |
    | Threshold | 0.4-0.5 | {:.2f} |
    """.format(omega, fringe_scale, detection_threshold))

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666;">
    <b>🔍 Visual Overlay Detection</b> | Green boxes = PDP-detected stealth candidates<br>
    Red circles = ground truth stealth | Blue squares = normal targets<br>
    © 2026 Tony E. Ford | QCAUS Framework
</div>
""", unsafe_allow_html=True)
