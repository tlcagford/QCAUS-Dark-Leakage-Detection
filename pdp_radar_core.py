"""
StealthPDPRadar - Core Photon-Dark-Photon Quantum Radar Filter
"""

import numpy as np
from scipy.fft import fft2, ifft2, fftshift
from scipy.ndimage import gaussian_filter, convolve
from typing import Tuple, Dict, Optional

class PDPRadarFilter:
    """
    Photon-Dark-Photon (PDP) Quantum Radar Filter
    """
    
    def __init__(self, 
                 omega: float = 0.5,
                 fringe_scale: float = 1.0,
                 entanglement_strength: float = 0.3,
                 mixing_angle: float = 0.1,
                 dark_photon_mass: float = 1e-9):
        
        self.omega = omega
        self.fringe_scale = fringe_scale
        self.entanglement_strength = entanglement_strength
        self.mixing_angle = mixing_angle
        self.dark_photon_mass = dark_photon_mass
        self.oscillation_length = self._compute_oscillation_length()
        
    def _compute_oscillation_length(self) -> float:
        if self.dark_photon_mass > 0:
            return 100.0 / (self.dark_photon_mass * 1e9)
        return 100.0
    
    def apply_spectral_duality(self, radar_image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        rows, cols = radar_image.shape
        crow, ccol = rows // 2, cols // 2
        
        fft_image = fft2(radar_image)
        fft_shifted = fftshift(fft_image)
        
        x = np.linspace(-1, 1, cols)
        y = np.linspace(-1, 1, rows)
        X, Y = np.meshgrid(x, y)
        R = np.sqrt(X**2 + Y**2)
        
        oscillation = np.sin(2 * np.pi * R * self.oscillation_length / self.fringe_scale)
        
        dark_mode_mask = (self.mixing_angle * np.exp(-self.omega * R**2) * 
                         np.abs(oscillation) * (1 - np.exp(-R**2 / self.fringe_scale)))
        
        ordinary_mode_mask = np.exp(-R**2 / self.fringe_scale) - dark_mode_mask
        
        dark_mode_fft = fft_shifted * dark_mode_mask
        ordinary_mode_fft = fft_shifted * ordinary_mode_mask
        
        dark_mode = np.abs(ifft2(fftshift(dark_mode_fft)))
        ordinary_mode = np.abs(ifft2(fftshift(ordinary_mode_fft)))
        
        return ordinary_mode, dark_mode
    
    def compute_entanglement_residuals(self, 
                                       radar_image: np.ndarray,
                                       ordinary_mode: np.ndarray,
                                       dark_mode: np.ndarray) -> np.ndarray:
        eps = 1e-10
        total_power = np.sum(radar_image**2) + eps
        
        rho_ordinary = ordinary_mode**2 / total_power
        rho_dark = dark_mode**2 / total_power
        
        rho_ordinary_safe = np.maximum(rho_ordinary, eps)
        local_entropy = -rho_ordinary_safe * np.log(rho_ordinary_safe)
        
        interference = (np.abs(ordinary_mode + dark_mode)**2 - 
                       ordinary_mode**2 - dark_mode**2) / total_power
        
        residuals = (local_entropy * self.entanglement_strength + 
                    np.abs(interference) * self.mixing_angle)
        
        kernel_size = int(max(3, self.fringe_scale))
        if kernel_size % 2 == 0:
            kernel_size += 1
        
        kernel = np.outer(np.hanning(kernel_size), np.hanning(kernel_size))
        kernel = kernel / np.sum(kernel)
        residuals = convolve(residuals, kernel, mode='constant')
        
        return residuals
    
    def generate_blue_halo_fusion(self, 
                                  radar_image: np.ndarray,
                                  dark_mode: np.ndarray,
                                  residuals: np.ndarray) -> np.ndarray:
        radar_norm = self._perceptual_normalize(radar_image)
        dark_norm = self._perceptual_normalize(dark_mode)
        residual_norm = self._perceptual_normalize(residuals)
        
        rgb = np.zeros((*radar_image.shape, 3))
        rgb[..., 0] = radar_norm
        rgb[..., 1] = self._enhance_contrast(residual_norm)
        
        dark_blurred = gaussian_filter(dark_norm, sigma=2.0)
        rgb[..., 2] = dark_blurred + 0.3 * dark_norm
        
        gamma = 0.45
        rgb = np.power(np.clip(rgb, 0, 1), gamma)
        
        return rgb
    
    def _perceptual_normalize(self, array: np.ndarray) -> np.ndarray:
        min_val = np.min(array)
        max_val = np.max(array)
        if max_val - min_val < 1e-10:
            return np.zeros_like(array)
        normalized = (array - min_val) / (max_val - min_val)
        return np.sqrt(normalized)
    
    def _enhance_contrast(self, array: np.ndarray) -> np.ndarray:
        kernel = np.ones((5, 5)) / 25
        local_mean = convolve(array, kernel, mode='constant')
        enhanced = array * (1 + 2 * np.abs(array - local_mean))
        return np.clip(enhanced, 0, 1)
    
    def compute_stealth_probability(self, 
                                   dark_mode: np.ndarray,
                                   residuals: np.ndarray) -> np.ndarray:
        dark_evidence = dark_mode / (np.mean(dark_mode) + 0.1)
        local_entropy = self._local_entropy(residuals, window=5)
        residual_evidence = local_entropy / (np.mean(local_entropy) + 0.1)
        
        prior = self.entanglement_strength
        likelihood = dark_evidence * residual_evidence
        stealth_prob = prior * likelihood / (prior * likelihood + (1 - prior))
        stealth_prob = gaussian_filter(stealth_prob, sigma=1.0)
        
        return np.clip(stealth_prob, 0, 1)
    
    def _local_entropy(self, array: np.ndarray, window: int = 5) -> np.ndarray:
        from scipy.ndimage import generic_filter
        
        def entropy_window(window_vals):
            hist, _ = np.histogram(window_vals, bins=10, density=True)
            hist = hist[hist > 0]
            return -np.sum(hist * np.log(hist))
        
        local_entropy = generic_filter(array, entropy_window, size=window)
        return local_entropy
    
    def process(self, radar_image: np.ndarray) -> Dict[str, np.ndarray]:
        ordinary_mode, dark_mode = self.apply_spectral_duality(radar_image)
        residuals = self.compute_entanglement_residuals(radar_image, ordinary_mode, dark_mode)
        fusion = self.generate_blue_halo_fusion(radar_image, dark_mode, residuals)
        stealth_probability = self.compute_stealth_probability(dark_mode, residuals)
        
        return {
            'ordinary_mode': ordinary_mode,
            'dark_mode_leakage': dark_mode,
            'entanglement_residuals': residuals,
            'fusion_visualization': fusion,
            'stealth_probability': stealth_probability,
            'parameters': {
                'omega': self.omega,
                'fringe_scale': self.fringe_scale,
                'entanglement_strength': self.entanglement_strength,
                'mixing_angle': self.mixing_angle,
                'dark_photon_mass': self.dark_photon_mass
            }
        }
