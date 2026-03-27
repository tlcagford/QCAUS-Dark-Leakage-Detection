import numpy as np
from typing import List, Dict, Tuple, Optional

class RadarDataConverter:
    def __init__(self, range_bins: int = 256, azimuth_bins: int = 360):
        self.range_bins = range_bins
        self.azimuth_bins = azimuth_bins
    
    def synthetic_stealth_target(self,
                                 image_shape: Tuple[int, int],
                                 position: Tuple[int, int],
                                 rcs_reduction: float = 0.1,
                                 halo_radius: int = 20) -> np.ndarray:
        stealth_map = np.zeros(image_shape)
        r, c = position
        
        for i in range(max(0, r - halo_radius), min(image_shape[0], r + halo_radius)):
            for j in range(max(0, c - halo_radius), min(image_shape[1], c + halo_radius)):
                dist = np.sqrt((i - r)**2 + (j - c)**2)
                if dist < halo_radius:
                    reduction = 1 - rcs_reduction * (1 - dist/halo_radius)
                    entanglement = np.sin(2 * np.pi * dist / 10) * (1 - dist/halo_radius)
                    stealth_map[i, j] = reduction * entanglement
        return stealth_map
    
    def add_clutter(self, image: np.ndarray, clutter_level: float = 0.1) -> np.ndarray:
        noise = np.random.randn(*image.shape) * clutter_level
        return np.maximum(image + noise, 0)
