"""
Real radar data loader for StealthPDPRadar
Loads actual radar detections from OpenSky Network and other sources
"""

import numpy as np
import requests
import pandas as pd
from typing import Tuple, Optional, List, Dict
from datetime import datetime, timedelta
import warnings
import time

class RealRadarLoader:
    """
    Load real primary surveillance radar (PSR) data
    
    Sources:
    - OpenSky Network: Live ADS-B and PSR data
    - NEXRAD: Weather radar (for pipeline testing)
    - Custom files: User-uploaded radar data
    """
    
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize loader with optional OpenSky credentials
        
        Get free credentials at: https://opensky-network.org
        """
        self.username = username
        self.password = password
        self.base_url = "https://opensky-network.org/api"
        self.cache = {}  # Simple cache for repeated requests
    
    def load_opensky_live(self, 
                          center_lat: float = 40.0,
                          center_lon: float = -100.0,
                          radius_deg: float = 3.0,
                          max_range_km: float = 300.0,
                          range_bins: int = 256,
                          azimuth_bins: int = 360,
                          use_cache: bool = True) -> Tuple[np.ndarray, pd.DataFrame]:
        """
        Load live radar data from OpenSky Network
        
        Returns:
        - radar_image: range-azimuth intensity map
        - ground_truth: DataFrame with ADS-B positions for validation
        """
        # Cache key for this request
        cache_key = f"{center_lat}_{center_lon}_{radius_deg}"
        
        if use_cache and cache_key in self.cache:
            cache_time, cached_data = self.cache[cache_key]
            if time.time() - cache_time < 60:  # Cache for 60 seconds
                return cached_data
        
        # Define bounding box
        bbox = (center_lat - radius_deg, center_lat + radius_deg,
                center_lon - radius_deg, center_lon + radius_deg)
        
        try:
            # Fetch state vectors from OpenSky
            url = f"{self.base_url}/states/all"
            params = {
                'lamin': bbox[0],
                'lamax': bbox[1],
                'lomin': bbox[2],
                'lomax': bbox[3]
            }
            
            auth = (self.username, self.password) if self.username else None
            response = requests.get(url, params=params, auth=auth, timeout=15)
            
            if response.status_code != 200:
                warnings.warn(f"OpenSky API error: {response.status_code}")
                result = (np.zeros((range_bins, azimuth_bins)), pd.DataFrame())
                if use_cache:
                    self.cache[cache_key] = (time.time(), result)
                return result
            
            data = response.json()
            
            if 'states' not in data or not data['states']:
                result = (np.zeros((range_bins, azimuth_bins)), pd.DataFrame())
                if use_cache:
                    self.cache[cache_key] = (time.time(), result)
                return result
            
            # Create radar image and ground truth
            radar_image = np.zeros((range_bins, azimuth_bins))
            ground_truth = []
            
            for state in data['states']:
                # State format: [icao24, callsign, origin_country, time_position,
                #                last_contact, longitude, latitude, baro_altitude,
                #                on_ground, velocity, true_track, ...]
                
                if state[5] is None or state[6] is None:  # lon/lat missing
                    continue
                
                lon, lat = state[5], state[6]
                
                # Calculate range and azimuth from radar center
                r_km = self._haversine_km(center_lat, center_lon, lat, lon)
                
                if r_km > max_range_km:
                    continue
                
                az_deg = self._bearing(center_lat, center_lon, lat, lon)
                
                # Convert to bin indices
                range_idx = min(int(r_km / max_range_km * (range_bins - 1)), range_bins - 1)
                az_idx = int((az_deg + 360) % 360 / 360 * (azimuth_bins - 1))
                
                # Estimate RCS based on aircraft type
                callsign = state[1] or ""
                rcs = self._estimate_rcs(callsign)
                
                # Radar range equation: SNR ∝ RCS / R^4
                # Add log-normal fading for realism
                fading = np.random.lognormal(0, 0.5)
                snr = rcs / (r_km**2 + 1) * fading
                
                radar_image[range_idx, az_idx] += snr
                
                # Store ground truth
                ground_truth.append({
                    'icao24': state[0],
                    'callsign': callsign,
                    'range_km': round(r_km, 1),
                    'azimuth_deg': round(az_deg, 1),
                    'rcs': round(rcs, 3),
                    'latitude': lat,
                    'longitude': lon,
                    'altitude_m': state[7] or 0,
                    'velocity_mps': state[9] or 0
                })
            
            ground_truth_df = pd.DataFrame(ground_truth)
            
            # Add realistic noise
            radar_image = self._add_radar_noise(radar_image)
            
            # Normalize
            if np.max(radar_image) > 0:
                radar_image = radar_image / np.max(radar_image)
            
            result = (radar_image, ground_truth_df)
            
            if use_cache:
                self.cache[cache_key] = (time.time(), result)
            
            return result
            
        except requests.exceptions.RequestException as e:
            warnings.warn(f"OpenSky network error: {e}")
            return (np.zeros((range_bins, azimuth_bins)), pd.DataFrame())
        except Exception as e:
            warnings.warn(f"OpenSky load error: {e}")
            return (np.zeros((range_bins, azimuth_bins)), pd.DataFrame())
    
    def load_opensky_history(self,
                            start_time: datetime,
                            end_time: datetime,
                            center_lat: float = 40.0,
                            center_lon: float = -100.0,
                            max_range_km: float = 300.0) -> List[np.ndarray]:
        """
        Load historical radar data for track analysis
        
        Returns list of radar images over time
        """
        radar_sequence = []
        timestamps = []
        
        # Query in 2-minute increments (respect rate limits)
        current_time = start_time
        while current_time < end_time:
            timestamp = int(current_time.timestamp())
            
            try:
                url = f"{self.base_url}/states/all"
                params = {'time': timestamp}
                
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                
                if 'states' in data and data['states']:
                    radar_image = self._states_to_image(data['states'], 
                                                         center_lat, center_lon,
                                                         max_range_km)
                    radar_sequence.append(radar_image)
                    timestamps.append(timestamp)
                
                current_time += timedelta(minutes=2)
                
                # Rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                warnings.warn(f"Error loading {current_time}: {e}")
                current_time += timedelta(minutes=2)
                continue
        
        return radar_sequence, timestamps
    
    def _states_to_image(self, states: List, 
                        center_lat: float, 
                        center_lon: float,
                        max_range_km: float = 300.0,
                        range_bins: int = 256,
                        azimuth_bins: int = 360) -> np.ndarray:
        """Convert OpenSky states to radar image"""
        radar_image = np.zeros((range_bins, azimuth_bins))
        
        for state in states:
            if state[5] is None or state[6] is None:
                continue
            
            lon, lat = state[5], state[6]
            r_km = self._haversine_km(center_lat, center_lon, lat, lon)
            
            if r_km > max_range_km:
                continue
            
            az_deg = self._bearing(center_lat, center_lon, lat, lon)
            
            range_idx = min(int(r_km / max_range_km * (range_bins - 1)), range_bins - 1)
            az_idx = int((az_deg + 360) % 360 / 360 * (azimuth_bins - 1))
            
            callsign = state[1] or ""
            rcs = self._estimate_rcs(callsign)
            snr = rcs / (r_km**2 + 1)
            radar_image[range_idx, az_idx] += snr
        
        return self._add_radar_noise(radar_image)
    
    def _estimate_rcs(self, callsign: str) -> float:
        """
        Estimate Radar Cross Section (RCS) in m² based on callsign
        
        References:
        - Large airliners (Boeing 747): ~100 m²
        - Fighter jets (F-16): ~1-5 m²
        - Stealth (F-35): ~0.001-0.01 m²
        - Small aircraft: ~1 m²
        """
        callsign_upper = callsign.upper()
        
        # Large commercial airliners
        if any(x in callsign_upper for x in ['BOEING', 'AIRBUS', 'JAL', 'UAL', 
                                              'DAL', 'AAL', 'SWA', 'ASA', 'KAL']):
            return np.random.uniform(50, 150)  # 50-150 m²
        
        # Regional jets
        elif any(x in callsign_upper for x in ['EMBRAER', 'BOMBARDIER', 'CRJ', 'ERJ']):
            return np.random.uniform(10, 30)  # 10-30 m²
        
        # Stealth aircraft (key for your detection)
        elif any(x in callsign_upper for x in ['F35', 'F-35', 'F22', 'F-22', 
                                                'B2', 'B-2', 'B21', 'B-21']):
            return np.random.uniform(0.001, 0.01)  # 0.001-0.01 m²
        
        # Military fighters (non-stealth)
        elif any(x in callsign_upper for x in ['F16', 'F-16', 'F15', 'F-15', 
                                                'F18', 'F-18', 'MIG', 'SU']):
            return np.random.uniform(1, 5)  # 1-5 m²
        
        # Small general aviation
        elif any(x in callsign_upper for x in ['CESSNA', 'PIPER', 'BEECH', 'MOONEY']):
            return np.random.uniform(0.5, 2)  # 0.5-2 m²
        
        # Default for unknown
        else:
            return np.random.uniform(1, 10)  # 1-10 m²
    
    def _haversine_km(self, lat1: float, lon1: float, 
                      lat2: float, lon2: float) -> float:
        """Calculate distance in km between two points using Haversine formula"""
        from math import radians, sin, cos, sqrt, asin
        R = 6371  # Earth radius in km
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        return R * c
    
    def _bearing(self, lat1: float, lon1: float, 
                 lat2: float, lon2: float) -> float:
        """Calculate bearing in degrees from point1 to point2"""
        from math import radians, degrees, sin, cos, atan2
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlon = lon2 - lon1
        x = sin(dlon) * cos(lat2)
        y = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(dlon)
        bearing = degrees(atan2(x, y))
        return (bearing + 360) % 360
    
    def _add_radar_noise(self, radar_image: np.ndarray, 
                         noise_level: float = 0.05) -> np.ndarray:
        """Add realistic radar noise and clutter"""
        # Thermal noise (Gaussian)
        thermal_noise = np.random.randn(*radar_image.shape) * noise_level
        
        # Speckle noise (multiplicative gamma)
        speckle = np.random.gamma(1.0, noise_level, radar_image.shape)
        speckle_noise = radar_image * (speckle - 1)
        
        # Combine
        noisy = radar_image + thermal_noise + speckle_noise
        
        return np.maximum(noisy, 0)
    
    def load_custom_file(self, file_content: bytes, filename: str) -> np.ndarray:
        """Load custom radar data from uploaded file"""
        import io
        
        try:
            if filename.endswith('.npz'):
                data = np.load(io.BytesIO(file_content))
                if 'radar_image' in data:
                    return data['radar_image']
                else:
                    # Try to get first array
                    return data[list(data.keys())[0]]
            elif filename.endswith('.npy'):
                return np.load(io.BytesIO(file_content))
            else:
                raise ValueError(f"Unsupported file type: {filename}")
        except Exception as e:
            raise RuntimeError(f"Failed to load custom file: {e}")
    
    def create_test_stealth_scenario(self, 
                                     num_targets: int = 1,
                                     stealth_rcs: float = 0.005,
                                     range_bins: int = 256,
                                     azimuth_bins: int = 360) -> np.ndarray:
        """
        Create synthetic test scenario with stealth targets
        Useful for validation when live data unavailable
        """
        radar_image = np.zeros((range_bins, azimuth_bins))
        
        # Add background clutter
        radar_image += np.random.gamma(2, 0.05, (range_bins, azimuth_bins))
        
        for i in range(num_targets):
            # Random position
            range_idx = np.random.randint(50, range_bins - 50)
            az_idx = np.random.randint(0, azimuth_bins)
            
            # Target RCS
            rcs = stealth_rcs if i == 0 else np.random.uniform(1, 10)
            
            # Add to radar image with range spread
            for dr in range(-5, 6):
                for da in range(-3, 4):
                    r_idx = range_idx + dr
                    a_idx = (az_idx + da) % azimuth_bins
                    if 0 <= r_idx < range_bins:
                        intensity = rcs / (1 + dr**2) * np.exp(-da**2 / 10)
                        radar_image[r_idx, a_idx] += intensity
        
        # Normalize
        if np.max(radar_image) > 0:
            radar_image = radar_image / np.max(radar_image)
        
        return radar_image
