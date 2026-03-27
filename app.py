"""
StealthPDPRadar - Main Streamlit Application
Full version with real radar data integration
"""

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
import time

# Import modules
from pdp_radar_core import PDPRadarFilter
from radar_io.radar_converter import RadarDataConverter
from radar_io.real_radar_loader import RealRadarLoader

# Page config
st.set_page_config(
    page_title="Stealth PDP Radar",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stAlert {
        font-size: 0.9rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.title("🔍 Stealth Photon-Dark-Photon Quantum Radar")
st.markdown("""
    **Spectral duality filter** that extracts green-speck entanglement residuals 
    and blue-halo IR fusion to detect stealth objects by revealing **dark-mode leakage** 
    in ordinary radar returns.
""")

# Sidebar
with st.sidebar:
    st.header("⚙️ PDP Filter Parameters")
    
    omega = st.slider("Ω (Entanglement Strength)", 0.0, 1.0, 0.5, 0.01)
    fringe_scale = st.slider("Fringe Scale", 0.1, 5.0, 1.0, 0.1)
    entanglement_strength = st.slider("Quantum Entanglement", 0.0, 1.0, 0.3, 0.01)
    mixing_angle = st.slider("ε (Mixing Angle)", 0.0, 0.5, 0.1, 0.01)
    
    st.header("📡 Data Source")
    data_source = st.radio(
        "Select data source",
        ["Synthetic Test", "OpenSky Live", "Upload Custom Data"],
        help="Synthetic: Generate test targets | OpenSky: Live aircraft data | Custom: Your own radar files"
    )
    
    # Radar location settings (for OpenSky)
    if data_source == "OpenSky Live":
        st.subheader("📍 Radar Location")
        radar_lat = st.number_input("Latitude", value=40.0, format="%.2f", 
                                     help="Radar installation latitude")
        radar_lon = st.number_input("Longitude", value=-100.0, format="%.2f",
                                     help="Radar installation longitude")
        search_radius = st.slider("Search Radius (deg)", 1.0, 10.0, 3.0, 0.5,
                                   help="Area to scan around radar")
        
        st.subheader("🔐 OpenSky Credentials (Optional)")
        use_creds = st.checkbox("Use registered account", help="Higher rate limits")
        if use_creds:
            opensky_user = st.text_input("Username")
            opensky_pass = st.text_input("Password", type="password")
        else:
            opensky_user = opensky_pass = None
        
        fetch_button = st.button("🔄 Fetch Live Data", type="primary", use_container_width=True)
    
    # Synthetic test parameters
    elif data_source == "Synthetic Test":
        st.subheader("🎯 Synthetic Scenario")
        test_mode = st.selectbox(
            "Test Scenario",
            ["Single Stealth", "Multiple Targets", "Stealth + Non-Stealth", "Gaussian Noise"]
        )
        
        if test_mode != "Gaussian Noise":
            target_range = st.slider("Target Range (km)", 0, 300, 150)
            target_azimuth = st.slider("Target Azimuth (deg)", 0, 360, 180)
            rcs_reduction = st.slider("RCS Reduction Factor", 0.0, 1.0, 0.1, 0.01,
                                       help="0 = invisible, 1 = normal radar cross section")
        
        if test_mode == "Multiple Targets":
            num_targets = st.slider("Number of Targets", 1, 10, 3)
        elif test_mode == "Stealth + Non-Stealth":
            num_stealth = st.slider("Number of Stealth Targets", 0, 5, 1)
            num_normal = st.slider("Number of Normal Targets", 0, 10, 3)
    
    # Custom upload
    elif data_source == "Upload Custom Data":
        st.subheader("📂 Upload Radar Data")
        uploaded_file = st.file_uploader(
            "Choose file",
            type=['npz', 'npy'],
            help="File should contain 'radar_image' array (range x azimuth)"
        )

# Initialize filter
filter = PDPRadarFilter(
    omega=omega,
    fringe_scale=fringe_scale,
    entanglement_strength=entanglement_strength,
    mixing_angle=mixing_angle,
    dark_photon_mass=1e-9
)
converter = RadarDataConverter(range_bins=256, azimuth_bins=360)

# Data generation based on source
radar_image = None
ground_truth = None

# SYNTHETIC DATA
if data_source == "Synthetic Test":
    if test_mode == "Gaussian Noise":
        radar_image = np.random.randn(256, 360) * 0.3
        ground_truth = pd.DataFrame()
        
    else:
        radar_image = np.random.randn(256, 360) * 0.05
        
        if test_mode == "Single Stealth":
            range_idx = int(target_range / 300 * 256)
            azimuth_idx = int(target_azimuth / 360 * 360)
            stealth_sig = converter.synthetic_stealth_target(
                (256, 360), (range_idx, azimuth_idx), rcs_reduction)
            radar_image += stealth_sig
            
            ground_truth = pd.DataFrame([{
                'type': 'stealth',
                'range_km': target_range,
                'azimuth_deg': target_azimuth,
                'rcs_reduction': rcs_reduction
            }])
            
        elif test_mode == "Multiple Targets":
            positions = []
            for i in range(num_targets):
                r = np.random.randint(50, 250)
                az = np.random.randint(0, 360)
                positions.append((r, az))
                stealth_sig = converter.synthetic_stealth_target(
                    (256, 360), (r, az), np.random.uniform(0.05, 0.3))
                radar_image += stealth_sig
            
            ground_truth = pd.DataFrame(positions, columns=['range_km', 'azimuth_deg'])
            
        elif test_mode == "Stealth + Non-Stealth":
            # Add stealth targets
            for i in range(num_stealth):
                r = np.random.randint(50, 250)
                az = np.random.randint(0, 360)
                stealth_sig = converter.synthetic_stealth_target(
                    (256, 360), (r, az), np.random.uniform(0.05, 0.2))
                radar_image += stealth_sig
            
            # Add normal targets (higher RCS)
            for i in range(num_normal):
                r = np.random.randint(50, 250)
                az = np.random.randint(0, 360)
                normal_sig = np.random.randn(5, 5) * 0.5
                r_idx, az_idx = r, az
                for dr in range(-2, 3):
                    for da in range(-2, 3):
                        if 0 <= r_idx+dr < 256 and 0 <= az_idx+da < 360:
                            radar_image[r_idx+dr, az_idx+da] += np.random.uniform(0.3, 0.8)
            
            ground_truth = pd.DataFrame()
        
        radar_image = converter.add_clutter(radar_image, 0.05)

# OPENSKY LIVE DATA
elif data_source == "OpenSky Live" and 'fetch_button' in locals() and fetch_button:
    with st.spinner("🌐 Fetching live radar data from OpenSky Network..."):
        loader = RealRadarLoader(username=opensky_user, password=opensky_pass)
        radar_image, ground_truth = loader.load_opensky_live(
            center_lat=radar_lat,
            center_lon=radar_lon,
            radius_deg=search_radius,
            max_range_km=300.0,
            range_bins=256,
            azimuth_bins=360
        )
        
        if len(ground_truth) > 0:
            st.sidebar.success(f"✅ {len(ground_truth)} aircraft detected")
        else:
            st.sidebar.warning("⚠️ No aircraft detected in area")

# CUSTOM UPLOAD
elif data_source == "Upload Custom Data" and uploaded_file is not None:
    with st.spinner("Loading custom radar data..."):
        loader = RealRadarLoader()
        radar_image = loader.load_custom_file(uploaded_file.getvalue(), uploaded_file.name)
        ground_truth = None
        st.sidebar.success(f"✅ Loaded: {uploaded_file.name}")

# Default fallback
if radar_image is None:
    radar_image = np.random.randn(256, 360) * 0.1

# Process with PDP filter
with st.spinner("🔄 Processing with PDP quantum filter..."):
    results = filter.process(radar_image)

# Create ground truth mask for metrics
if ground_truth is not None and len(ground_truth) > 0:
    gt_mask = np.zeros((256, 360), dtype=bool)
    if 'range_km' in ground_truth.columns:
        for _, row in ground_truth.iterrows():
            r_idx = int(row['range_km'] / 300 * 255)
            az_idx = int(row['azimuth_deg'] / 360 * 359)
            gt_mask[max(0, r_idx-5):min(256, r_idx+5), 
                    max(0, az_idx-5):min(360, az_idx+5)] = True
else:
    gt_mask = None

# Display results
col1, col2 = st.columns(2)

with col1:
    st.subheader("📡 Original Radar Image")
    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(radar_image, aspect='auto', cmap='viridis', 
                   extent=[0, 360, 300, 0])
    ax.set_xlabel("Azimuth (deg)")
    ax.set_ylabel("Range (km)")
    ax.set_title("Radar Returns (Range-Azimuth)")
    plt.colorbar(im, ax=ax, label="Intensity")
    st.pyplot(fig)

with col2:
    st.subheader("🎯 Stealth Probability Map")
    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(results['stealth_probability'], aspect='auto', 
                   cmap='hot', extent=[0, 360, 300, 0],
                   vmin=0, vmax=1)
    ax.set_xlabel("Azimuth (deg)")
    ax.set_ylabel("Range (km)")
    ax.set_title("Dark-Mode Leakage Probability")
    plt.colorbar(im, ax=ax, label="P(Stealth)")
    st.pyplot(fig)

# Fusion visualization
st.subheader("🌀 Blue-Halo IR Fusion Visualization")
st.markdown("*🟢 Green speckles = entanglement residuals | 🔵 Blue halos = dark-mode leakage*")

fig, ax = plt.subplots(figsize=(12, 8))
ax.imshow(results['fusion_visualization'], aspect='auto', extent=[0, 360, 300, 0])
ax.set_xlabel("Azimuth (deg)")
ax.set_ylabel("Range (km)")
st.pyplot(fig)

# Component analysis
st.subheader("📊 Component Analysis")
col3, col4 = st.columns(2)

with col3:
    st.write("**🌑 Dark-Mode Leakage**")
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.imshow(results['dark_mode_leakage'], aspect='auto', cmap='Blues')
    st.pyplot(fig)

with col4:
    st.write("**🟢 Entanglement Residuals (Green Speck)**")
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.imshow(results['entanglement_residuals'], aspect='auto', cmap='Greens')
    st.pyplot(fig)

# Detection metrics (if ground truth available)
if gt_mask is not None:
    from validation.metrics import compute_detection_metrics
    metrics = compute_detection_metrics(results['stealth_probability'], gt_mask)
    
    st.subheader("📈 Detection Metrics")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Precision", f"{metrics['precision']:.3f}")
    m2.metric("Recall", f"{metrics['recall']:.3f}")
    m3.metric("F1 Score", f"{metrics['f1_score']:.3f}")
    m4.metric("Detections", f"{metrics['true_positives']}")
    
    if metrics['precision'] < 0.5 and metrics['recall'] < 0.5:
        st.warning("⚠️ Low detection metrics. Try adjusting Ω (entanglement strength) or fringe scale.")

# Ground truth display
if ground_truth is not None and len(ground_truth) > 0:
    with st.expander("📋 Ground Truth Data (ADS-B)"):
        st.dataframe(ground_truth.head(20))

# Parameters display
with st.expander("⚙️ PDP Filter Parameters"):
    st.json(results['parameters'])

# Theory explanation
with st.expander("📖 About the PDP Quantum Radar Filter"):
    st.markdown(r"""
    ### Photon-Dark-Photon (PDP) Quantum Radar Theory
    
    This filter implements a spectral duality transformation based on:
    
    1. **Kinetic Mixing**: $\mathcal{L}_{\text{mix}} = \frac{\varepsilon}{2} F_{\mu\nu} F'^{\mu\nu}$
    2. **Von Neumann Evolution**: $i\partial_t\rho = [H_{\text{eff}}, \rho]$
    3. **Entanglement Entropy**: $S = -\text{Tr}(\rho \log \rho)$
    
    ### Key Parameters
    
    | Parameter | Symbol | Description |
    |-----------|--------|-------------|
    | Entanglement Strength | Ω | Coupling between photon and dark photon fields |
    | Fringe Scale | λ | Quantum interference pattern scale |
    | Mixing Angle | ε | Kinetic mixing parameter from dark photon theory |
    | Quantum Entanglement | κ | Strength of von Neumann entropy effects |
    
    ### Detection Capability
    
    The filter reveals dark-mode leakage that ordinary radar misses, enabling detection of:
    - Stealth aircraft (F-35, B-21, NGAD)
    - Hypersonic missiles (Kinzhal)
    - Low-observable targets at ranges >250 km
    
    ### References
    
    - Quantum Cosmology & Astrophysics Unified Suite (QCAUS)
    - Primordial Photon-DarkPhoton Entanglement
    - Spectral duality in quantum field theory
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 20px;">
    Built with QCAUS framework | For academic research use only<br>
    © 2026 Tony E. Ford | <a href="https://github.com/tlcagford/StealthPDPRadar">GitHub Repository</a>
</div>
""", unsafe_allow_html=True)
