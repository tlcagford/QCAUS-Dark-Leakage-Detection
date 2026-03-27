"""
StealthPDPRadar - Main Streamlit Application
"""

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from pdp_radar_core import PDPRadarFilter
from radar_io.radar_converter import RadarDataConverter

st.set_page_config(page_title="Stealth PDP Radar", layout="wide")

st.title("🔍 Stealth Photon-Dark-Photon Quantum Radar")
st.markdown("""
    Spectral duality filter that extracts green-speck entanglement residuals 
    and blue-halo IR fusion to detect stealth objects by revealing dark-mode leakage.
""")

# Sidebar controls
with st.sidebar:
    st.header("PDP Filter Parameters")
    omega = st.slider("Entanglement Strength (Ω)", 0.0, 1.0, 0.5)
    fringe_scale = st.slider("Fringe Scale", 0.1, 5.0, 1.0)
    entanglement_strength = st.slider("Quantum Entanglement", 0.0, 1.0, 0.3)
    mixing_angle = st.slider("Mixing Angle (ε)", 0.0, 0.5, 0.1)
    
    st.header("Test Data")
    test_mode = st.selectbox("Select Test Case", 
                             ["Synthetic - Single Stealth", 
                              "Synthetic - Multiple Targets",
                              "Gaussian Noise"])
    
    if test_mode.startswith("Synthetic"):
        target_range = st.slider("Target Range (km)", 0, 300, 150)
        target_azimuth = st.slider("Target Azimuth (deg)", 0, 360, 180)
        rcs_reduction = st.slider("RCS Reduction Factor", 0.0, 1.0, 0.1)

# Initialize filter
filter = PDPRadarFilter(
    omega=omega,
    fringe_scale=fringe_scale,
    entanglement_strength=entanglement_strength,
    mixing_angle=mixing_angle
)
converter = RadarDataConverter(range_bins=256, azimuth_bins=360)

# Generate test data
if test_mode == "Synthetic - Single Stealth":
    radar_image = np.random.randn(256, 360) * 0.1
    
    range_idx = int(target_range / 300 * 256)
    azimuth_idx = int(target_azimuth / 360 * 360)
    stealth_sig = converter.synthetic_stealth_target(
        (256, 360), (range_idx, azimuth_idx), rcs_reduction)
    radar_image += stealth_sig
    radar_image = converter.add_clutter(radar_image, 0.05)
    ground_truth = np.zeros((256, 360), dtype=bool)
    ground_truth[range_idx-10:range_idx+10, azimuth_idx-10:azimuth_idx+10] = True
    
elif test_mode == "Synthetic - Multiple Targets":
    radar_image = np.random.randn(256, 360) * 0.1
    positions = [(50, 90), (150, 180), (200, 270)]
    ground_truth = np.zeros((256, 360), dtype=bool)
    for pos in positions:
        stealth_sig = converter.synthetic_stealth_target((256, 360), pos, 0.1)
        radar_image += stealth_sig
        ground_truth[pos[0]-10:pos[0]+10, pos[1]-10:pos[1]+10] = True
    radar_image = converter.add_clutter(radar_image, 0.05)
    
else:
    radar_image = np.random.randn(256, 360) * 0.5
    ground_truth = np.zeros((256, 360), dtype=bool)

# Process with PDP filter
with st.spinner("Processing with PDP quantum filter..."):
    results = filter.process(radar_image)

# Display results
col1, col2 = st.columns(2)

with col1:
    st.subheader("Original Radar Image")
    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(radar_image, aspect='auto', cmap='viridis', 
                   extent=[0, 360, 300, 0])
    ax.set_xlabel("Azimuth (deg)")
    ax.set_ylabel("Range (km)")
    ax.set_title("Original Radar Returns")
    plt.colorbar(im, ax=ax, label="Intensity")
    st.pyplot(fig)

with col2:
    st.subheader("Stealth Probability Map")
    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(results['stealth_probability'], aspect='auto', 
                   cmap='hot', extent=[0, 360, 300, 0],
                   vmin=0, vmax=1)
    ax.set_xlabel("Azimuth (deg)")
    ax.set_ylabel("Range (km)")
    ax.set_title("Dark-Mode Leakage (Stealth Signature)")
    plt.colorbar(im, ax=ax, label="Probability")
    st.pyplot(fig)

# Fusion visualization
st.subheader("Blue-Halo IR Fusion Visualization")
st.markdown("*Green speckles = entanglement residuals, Blue halos = dark-mode leakage*")

fig, ax = plt.subplots(figsize=(12, 8))
ax.imshow(results['fusion_visualization'], aspect='auto', extent=[0, 360, 300, 0])
ax.set_xlabel("Azimuth (deg)")
ax.set_ylabel("Range (km)")
st.pyplot(fig)

# Component analysis
st.subheader("Component Analysis")
col3, col4 = st.columns(2)

with col3:
    st.write("**Dark-Mode Leakage**")
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.imshow(results['dark_mode_leakage'], aspect='auto', cmap='Blues')
    st.pyplot(fig)

with col4:
    st.write("**Entanglement Residuals (Green Speck)**")
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.imshow(results['entanglement_residuals'], aspect='auto', cmap='Greens')
    st.pyplot(fig)

# Metrics
if test_mode.startswith("Synthetic"):
    from validation.metrics import compute_detection_metrics
    metrics = compute_detection_metrics(results['stealth_probability'], ground_truth)
    
    st.subheader("Detection Metrics")
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Precision", f"{metrics['precision']:.3f}")
    col_m2.metric("Recall", f"{metrics['recall']:.3f}")
    col_m3.metric("F1 Score", f"{metrics['f1_score']:.3f}")

# Parameters display
with st.expander("PDP Filter Parameters"):
    st.json(results['parameters'])

with st.expander("About the PDP Quantum Radar Filter"):
    st.markdown("""
    ### Photon-Dark-Photon (PDP) Quantum Radar Theory
    
    This filter implements a spectral duality transformation based on:
    
    1. **Kinetic Mixing**: ℒ_mix = (ε/2) F_μν F'^μν
    2. **Von Neumann Evolution**: i∂_tρ = [H_eff, ρ]
    3. **Entanglement Entropy**: S = -Tr(ρ log ρ)
    
    ### Key Parameters
    
    - **Ω (Entanglement Strength)**: Coupling constant between photon and dark photon fields
    - **Fringe Scale**: Characteristic length of quantum interference patterns
    - **Mixing Angle (ε)**: Kinetic mixing parameter from dark photon theory
    - **Quantum Entanglement**: Strength of von Neumann entropy effects
    
    ### Detection Capability
    
    The filter reveals dark-mode leakage that ordinary radar misses, enabling detection of:
    - Stealth aircraft (F-35, B-21, NGAD)
    - Hypersonic missiles (Kinzhal)
    - Low-observable targets at ranges >250 km
    """)

st.markdown("---")
st.markdown("*Built with QCAUS framework | For academic research use only*")
