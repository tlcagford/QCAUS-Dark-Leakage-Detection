"""
StealthPDPRadar - Main Streamlit Application
Full version with real radar data integration
"""

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

# Import modules
from pdp_radar_core import PDPRadarFilter
from radar_io.radar_converter import RadarDataConverter
from radar_io.real_radar_loader import RealRadarLoader

# Page config
st.set_page_config(
    page_title="Stealth PDP Radar",
    page_icon="🔍",
    layout="wide"
)

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
        ["Synthetic Test", "OpenSky Live", "Upload Custom Data"]
    )
    
    # Radar location settings (for OpenSky)
    if data_source == "OpenSky Live":
        st.subheader("📍 Radar Location")
        st.info("Try these busy airports:\n- JFK: 40.64, -73.78\n- LAX: 33.94, -118.41\n- LHR: 51.47, -0.45")
        
        radar_lat = st.number_input("Latitude", value=40.64, format="%.2f")
        radar_lon = st.number_input("Longitude", value=-73.78, format="%.2f")
        search_radius = st.slider("Search Radius (deg)", 1.0, 10.0, 3.0, 0.5)
        
        st.subheader("🔐 OpenSky Credentials")
        st.caption("Optional - leave blank for anonymous access")
        opensky_user = st.text_input("Username", value="", placeholder="your_username")
        opensky_pass = st.text_input("Password", type="password", value="", placeholder="your_password")
        
        fetch_button = st.button("🔄 Fetch Live Data", type="primary", use_container_width=True)
    
    # Synthetic test parameters
    elif data_source == "Synthetic Test":
        st.subheader("🎯 Synthetic Scenario")
        test_mode = st.selectbox(
            "Test Scenario",
            ["Single Stealth", "Multiple Targets", "Stealth + Non-Stealth", "Gaussian Noise"]
        )
        
        if test_mode == "Single Stealth":
            target_range = st.slider("Target Range (km)", 0, 300, 150)
            target_azimuth = st.slider("Target Azimuth (deg)", 0, 360, 180)
            rcs_reduction = st.slider("RCS Reduction Factor", 0.0, 1.0, 0.1, 0.01)
        
        if test_mode == "Multiple Targets":
            num_targets = st.slider("Number of Targets", 1, 10, 3)
    
    # Custom upload
    elif data_source == "Upload Custom Data":
        st.subheader("📂 Upload Radar Data")
        uploaded_file = st.file_uploader(
            "Choose file", type=['npz', 'npy'],
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
data_source_status = ""

# SYNTHETIC DATA
if data_source == "Synthetic Test":
    if test_mode == "Gaussian Noise":
        radar_image = np.random.randn(256, 360) * 0.3
        ground_truth = pd.DataFrame()
        data_source_status = f"Using: Gaussian Noise"
        
    elif test_mode == "Single Stealth":
        radar_image = np.random.randn(256, 360) * 0.05
        range_idx = int(target_range / 300 * 256)
        azimuth_idx = int(target_azimuth / 360 * 360)
        stealth_sig = converter.synthetic_stealth_target(
            (256, 360), (range_idx, azimuth_idx), rcs_reduction)
        radar_image += stealth_sig
        radar_image = converter.add_clutter(radar_image, 0.05)
        ground_truth = pd.DataFrame([{
            'type': 'stealth', 'range_km': target_range, 
            'azimuth_deg': target_azimuth, 'rcs_reduction': rcs_reduction
        }])
        data_source_status = f"Using: Single Stealth at {target_range}km, {target_azimuth}°"
        
    elif test_mode == "Multiple Targets":
        radar_image = np.random.randn(256, 360) * 0.05
        positions = []
        for i in range(num_targets):
            r = np.random.randint(50, 250)
            az = np.random.randint(0, 360)
            positions.append((r, az))
            stealth_sig = converter.synthetic_stealth_target(
                (256, 360), (r, az), np.random.uniform(0.05, 0.3))
            radar_image += stealth_sig
        radar_image = converter.add_clutter(radar_image, 0.05)
        ground_truth = pd.DataFrame(positions, columns=['range_km', 'azimuth_deg'])
        data_source_status = f"Using: {num_targets} stealth targets"
        
    elif test_mode == "Stealth + Non-Stealth":
        radar_image = np.random.randn(256, 360) * 0.05
        # Stealth targets
        for i in range(1):
            r = np.random.randint(50, 250)
            az = np.random.randint(0, 360)
            stealth_sig = converter.synthetic_stealth_target((256, 360), (r, az), 0.1)
            radar_image += stealth_sig
        # Non-stealth targets (brighter)
        for i in range(3):
            r = np.random.randint(50, 250)
            az = np.random.randint(0, 360)
            for dr in range(-3, 4):
                for da in range(-2, 3):
                    if 0 <= r+dr < 256 and 0 <= az+da < 360:
                        radar_image[r+dr, az+da] += np.random.uniform(0.3, 0.7)
        radar_image = converter.add_clutter(radar_image, 0.05)
        ground_truth = pd.DataFrame()
        data_source_status = "Using: 1 stealth + 3 non-stealth targets"

# OPENSKY LIVE DATA
elif data_source == "OpenSky Live" and 'fetch_button' in locals() and fetch_button:
    with st.spinner("🌐 Fetching live aircraft data from OpenSky Network..."):
        loader = RealRadarLoader(
            username=opensky_user if opensky_user else None,
            password=opensky_pass if opensky_pass else None
        )
        radar_image, ground_truth = loader.load_opensky_live(
            center_lat=radar_lat,
            center_lon=radar_lon,
            radius_deg=search_radius,
            max_range_km=300.0,
            range_bins=256,
            azimuth_bins=360
        )
        
        if len(ground_truth) > 0:
            data_source_status = f"✅ OpenSky: {len(ground_truth)} aircraft detected at ({radar_lat}, {radar_lon})"
        else:
            data_source_status = f"⚠️ No aircraft detected. Try different coordinates (JFK: 40.64, -73.78)"

# CUSTOM UPLOAD
elif data_source == "Upload Custom Data" and 'uploaded_file' in locals() and uploaded_file is not None:
    with st.spinner("Loading custom radar data..."):
        loader = RealRadarLoader()
        radar_image = loader.load_custom_file(uploaded_file.getvalue(), uploaded_file.name)
        ground_truth = None
        data_source_status = f"✅ Loaded: {uploaded_file.name}"

# Default fallback
if radar_image is None:
    radar_image = np.random.randn(256, 360) * 0.1
    data_source_status = "⚠️ No data loaded - using noise"

# Process with PDP filter
with st.spinner("🔄 Processing with PDP quantum filter..."):
    results = filter.process(radar_image)

# Create ground truth mask for metrics
if ground_truth is not None and len(ground_truth) > 0 and 'range_km' in ground_truth.columns:
    gt_mask = np.zeros((256, 360), dtype=bool)
    for _, row in ground_truth.iterrows():
        if 'range_km' in row and 'azimuth_deg' in row:
            r_idx = int(row['range_km'] / 300 * 255) if row['range_km'] <= 300 else 255
            az_idx = int(row['azimuth_deg'] / 360 * 359)
            gt_mask[max(0, r_idx-5):min(256, r_idx+5), 
                    max(0, az_idx-5):min(360, az_idx+5)] = True
else:
    gt_mask = None

# Status bar
st.info(f"📊 {data_source_status}")

# Display results
col1, col2 = st.columns(2)

with col1:
    st.subheader("📡 Original Radar Image")
    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(radar_image, aspect='auto', cmap='viridis', 
                   extent=[0, 360, 300, 0])
    ax.set_xlabel("Azimuth (deg)")
    ax.set_ylabel("Range (km)")
    ax.set_title("Radar Returns")
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
    m4.metric("Detections", f"{metrics['true_positives']}/{metrics['total_targets']}")

# Ground truth display
if ground_truth is not None and len(ground_truth) > 0:
    with st.expander("📋 Ground Truth Data (ADS-B)"):
        st.dataframe(ground_truth)

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
    | Mixing Angle | ε | Kinetic mixing parameter |
    | Quantum Entanglement | κ | Strength of von Neumann entropy effects |
    
    ### Detection Capability
    
    The filter reveals dark-mode leakage that ordinary radar misses, enabling detection of:
    - Stealth aircraft (F-35, B-21, NGAD)
    - Hypersonic missiles (Kinzhal)
    - Low-observable targets at ranges >250 km
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 20px;">
    Built with QCAUS framework | For academic research use only<br>
    © 2026 Tony E. Ford
</div>
""", unsafe_allow_html=True)
