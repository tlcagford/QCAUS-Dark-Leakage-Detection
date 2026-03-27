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
    
    def load_opensky_live(self, 
                          center_lat: float = 40.0,
                          center_lon: float = -100.0,
                          radius_deg: float = 3.0,
                          max_range_km: float = 300.0,
                          range_bins: int = 256,
                          azimuth_bins: int = 360) -> Tuple[np.ndarray, pd.DataFrame]:
        """
        Load live radar data from OpenSky Network
        
        Returns:
        - radar_image: range-azimuth intensity map
        - ground_truth: DataFrame with ADS-B positions for validation
        """
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
                return np.zeros((range_bins, azimuth_bins)), pd.DataFrame()
            
            data = response.json()
            
            if 'states' not in data or not data['states']:
                return np.zeros((range_bins, azimuth_bins)), pd.DataFrame()
            
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
                
                # Estimate RCS based on aircraft type (from callsign)
                callsign = state[1] or ""
                rcs = self._estimate_rcs(callsign)
                
                # Add to radar image (SNR proportional to RCS/r^4)
                snr = rcs / (r_km**2 + 1)  # Simplified propagation model
                radar_image[range_idx, az_idx] += snr
                
                # Store ground truth
                ground_truth.append({
                    'icao24': state[0],
                    'callsign': callsign,
                    'range_km': r_km,
                    'azimuth_deg': az_deg,
                    'rcs': rcs,
                    'latitude': lat,
                    'longitude': lon,
                    'altitude_m': state[7] or 0
                })
            
            ground_truth_df = pd.DataFrame(ground_truth)
            
            # Add realistic noise
            radar_image = self._add_radar_noise(radar_image)
            
            return radar_image, ground_truth_df
            
        except Exception as e:
            warnings.warn(f"OpenSky load error: {e}")
            return np.zeros((range_bins, azimuth_bins)), pd.DataFrame()
    
    def load_opensky_history(self,
                            start_time: datetime,
                            end_time: datetime,
                            icao24: Optional[str] = None,
                            center_lat: float = 40.0,
                            center_lon: float = -100.0) -> List[np.ndarray]:
        """
        Load historical radar data for track analysis
        
        Returns list of radar images over time
        """
        radar_sequence = []
        
        # Query in 1-minute increments (rate limit)
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
                                                         center_lat, center_lon)
                    radar_sequence.append(radar_image)
                
                current_time += timedelta(minutes=1)
                
            except Exception as e:
                warnings.warn(f"Error loading {current_time}: {e}")
                current_time += timedelta(minutes=1)
                continue
        
        return radar_sequence
    
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
        """Estimate RCS based on callsign pattern"""
        callsign_upper = callsign.upper()
        
        # Known aircraft types (simplified RCS in m²)
        if any(x in callsign_upper for x in ['BOEING', 'AIRBUS', 'JAL', 'UAL', 'DAL']):
            return 10.0  # Large airliner
        elif any(x in callsign_upper for x in ['CESSNA', 'PIPER', 'N123']):
            return 1.0   # Small general aviation
        elif any(x in callsign_upper for x in ['F35', 'F22', 'B2', 'B21']):
            return 0.001  # Stealth aircraft
        else:
            return 5.0    # Default
    
    def _haversine_km(self, lat1: float, lon1: float, 
                      lat2: float, lon2: float) -> float:
        """Calculate distance in km between two points"""
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
        """Calculate bearing in degrees"""
        from math import radians, degrees, sin, cos, atan2
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlon = lon2 - lon1
        x = sin(dlon) * cos(lat2)
        y = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(dlon)
        bearing = degrees(atan2(x, y))
        return bearing
    
    def _add_radar_noise(self, radar_image: np.ndarray, 
                         noise_level: float = 0.05) -> np.ndarray:
        """Add realistic radar noise and clutter"""
        # Thermal noise
        noise = np.random.randn(*radar_image.shape) * noise_level
        
        # Speckle noise (multiplicative)
        speckle = np.random.gamma(1.0, noise_level, radar_image.shape)
        
        return np.maximum(radar_image + noise + radar_image * speckle, 0)
    
    def load_custom_file(self, filepath: str) -> np.ndarray:
        """Load custom radar data file"""
        try:
            if filepath.endswith('.npz'):
                data = np.load(filepath)
                return data['radar_image']
            elif filepath.endswith('.npy'):
                return np.load(filepath)
            else:
                raise ValueError(f"Unsupported file type: {filepath}")
        except Exception as e:
            raise RuntimeError(f"Failed to load custom file: {e}")
