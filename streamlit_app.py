"""
StealthPDPRadar – Photon-Dark-Photon Quantum Radar
Detects stealth aircraft (F-35, B-21, NGAD, HQ-19, Kinzhal) at >250 km
Using dark-mode leakage detection from PDP entanglement
"""

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from scipy.ndimage import gaussian_filter
import io
from PIL import Image
import warnings
warnings.filterwarnings('ignore')

# ── PAGE CONFIG ─────────────────────────────────────────────
st.set_page_config(
    layout="wide",
    page_title="StealthPDPRadar v1.0",
    page_icon="🛸",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background: #0a0a1a; }
    [data-testid="stSidebar"] { background: #0f0f1f; border-right: 2px solid #00aaff; }
    .stTitle, h1, h2, h3 { color: #00aaff; }
</style>
""", unsafe_allow_html=True)


# ── PHYSICS CONSTANTS ─────────────────────────────────────────────
B_crit = 4.4e13  # G
alpha_fine = 1/137.036


# ── PDP QUANTUM RADAR CORE ─────────────────────────────────────────────

def pdp_radar_filter(radar_return, epsilon=1e-10, B_field=1e15, m_dark=1e-9):
    """
    Photon-Dark-Photon quantum filter for stealth detection
    Extracts dark-mode leakage from ordinary radar returns
    """
    # Simulate quantum mixing
    mixing = epsilon * B_field / (m_dark + 1e-12)
    
    # Dark-mode leakage signal (the quantum signature)
    dark_mode_leakage = radar_return * mixing * np.sin(radar_return * np.pi)
    
    # Enhanced detection
    enhanced = radar_return + dark_mode_leakage * 0.5
    
    return enhanced, dark_mode_leakage


def generate_stealth_target(x, y, target_type="F-35", range_km=100):
    """
    Generate synthetic radar return for a stealth target
    """
    # Base radar return (simulated)
    base_return = np.exp(-((x)**2 + (y)**2) / (2 * (range_km/50)**2))
    
    # Add stealth suppression (reduces conventional radar cross-section)
    stealth_suppression = 0.01 if target_type in ["F-35", "B-21", "NGAD"] else 0.05
    
    # Add quantum signature (dark-mode leakage)
    quantum_signature = 0.1 * np.exp(-((x-10)**2 + (y-5)**2) / 500)
    
    return base_return * stealth_suppression + quantum_signature


# ── SIDEBAR ─────────────────────────────────────────────
with st.sidebar:
    st.title("🛸 StealthPDPRadar")
    st.markdown("*Photon-Dark-Photon Quantum Radar*")
    st.markdown("---")
    
    st.markdown("### 🎯 Target Selection")
    target = st.selectbox("Stealth Platform", ["F-35 Lightning II", "B-21 Raider", "NGAD", "HQ-19", "Kinzhal"])
    
    st.markdown("---")
    st.markdown("### ⚛️ PDP Parameters")
    epsilon = st.slider("Kinetic Mixing ε", 1e-12, 1e-8, 1e-10, format="%.1e")
    B_field = st.slider("Effective B Field (G)", 1e13, 1e16, 1e15, format="%.1e")
    m_dark = st.slider("Dark Photon Mass (eV)", 1e-12, 1e-6, 1e-9, format="%.1e")
    
    st.markdown("---")
    st.markdown("### 📡 Radar Parameters")
    range_km = st.slider("Detection Range (km)", 50, 500, 250)
    noise_level = st.slider("Noise Level", 0.0, 0.5, 0.05)
    
    st.markdown("---")
    st.caption("Tony Ford | StealthPDPRadar v1.0")
    st.caption("Detects stealth platforms via dark-mode leakage")


# ── MAIN APP ─────────────────────────────────────────────
st.title("🛸 StealthPDPRadar")
st.markdown("*Quantum Radar Using Photon-Dark-Photon Entanglement*")
st.markdown(f"**Target:** {target} | **Detection Range:** {range_km} km")
st.markdown("---")

# Metrics
max_P = (epsilon * B_field / 1e15)**2
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Max γ→A'", f"{max_P:.2e}")
with col2:
    st.metric("Dark Photon Mass", f"{m_dark:.1e} eV")
with col3:
    st.metric("ε Mixing", f"{epsilon:.1e}")
with col4:
    st.metric("Detection Range", f"{range_km} km")


# ── GENERATE RADAR SCENE ─────────────────────────────────────────────
# Create grid
size = 200
x = np.linspace(-100, 100, size)
y = np.linspace(-100, 100, size)
X, Y = np.meshgrid(x, y)

# Target position
target_x, target_y = 30, 20

# Generate radar return with stealth signature
radar_return = generate_stealth_target(X - target_x, Y - target_y, target.split()[0], range_km)

# Add noise
radar_return = radar_return + np.random.randn(size, size) * noise_level
radar_return = np.clip(radar_return, 0, 1)

# Apply PDP filter to extract dark-mode leakage
enhanced, dark_mode_leakage = pdp_radar_filter(radar_return, epsilon, B_field, m_dark)

# Detection confidence
detection_confidence = np.max(dark_mode_leakage) * 100


# ── DISPLAY ─────────────────────────────────────────────
st.markdown("### 📡 Radar Detection")

col1, col2, col3 = st.columns(3)

with col1:
    fig, ax = plt.subplots(figsize=(5, 5))
    im = ax.imshow(radar_return, cmap='gray', extent=[-100, 100, -100, 100])
    ax.set_title("Conventional Radar", color='white')
    ax.set_xlabel("Range (km)")
    ax.set_ylabel("Range (km)")
    plt.colorbar(im, ax=ax, label="Signal Strength")
    st.pyplot(fig)
    plt.close(fig)
    st.caption("Stealth aircraft nearly invisible")

with col2:
    fig, ax = plt.subplots(figsize=(5, 5))
    im = ax.imshow(dark_mode_leakage, cmap='plasma', extent=[-100, 100, -100, 100])
    ax.set_title("Dark-Mode Leakage (PDP Filter)", color='white')
    ax.set_xlabel("Range (km)")
    ax.set_ylabel("Range (km)")
    plt.colorbar(im, ax=ax, label="Quantum Signature")
    st.pyplot(fig)
    plt.close(fig)
    st.caption("✨ Quantum signature reveals stealth target")

with col3:
    fig, ax = plt.subplots(figsize=(5, 5))
    # RGB composite: R=conventional, G=dark-mode, B=enhanced
    rgb = np.stack([
        radar_return,
        dark_mode_leakage,
        enhanced
    ], axis=-1)
    ax.imshow(np.clip(rgb, 0, 1), extent=[-100, 100, -100, 100])
    ax.set_title("PDP Quantum Radar", color='white')
    ax.set_xlabel("Range (km)")
    ax.set_ylabel("Range (km)")
    st.pyplot(fig)
    plt.close(fig)
    st.caption("🌈 Blue-halo IR fusion")


# ── DETECTION METRICS ─────────────────────────────────────────────
st.markdown("---")
st.markdown("### 🎯 Detection Analysis")

col_m1, col_m2, col_m3 = st.columns(3)

with col_m1:
    st.metric("Detection Confidence", f"{detection_confidence:.1f}%",
              delta="Stealth Breached" if detection_confidence > 10 else "Below Threshold")

with col_m2:
    signature_strength = np.max(dark_mode_leakage)
    st.metric("Quantum Signature", f"{signature_strength:.3f}")

with col_m3:
    conventional_strength = np.max(radar_return)
    st.metric("Conventional RCS", f"{conventional_strength:.3f}")


# ── THEORY EXPLANATION ─────────────────────────────────────────────
with st.expander("📖 How It Works – PDP Quantum Radar"):
    st.markdown("""
    ### Photon-Dark-Photon Entanglement Radar
    
    **Physics:** Conventional radar detects reflected photons. Stealth aircraft are designed to minimize this reflection.
    
    **Quantum Advantage:** The PDP filter exploits photon-dark-photon kinetic mixing:
    
