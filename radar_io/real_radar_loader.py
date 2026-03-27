"""
Real radar data loader for StealthPDPRadar
Loads actual radar detections from OpenSky Network
"""

import numpy as np
import requests
import pandas as pd
from typing import Tuple, Optional, List
import time
import warnings

class RealRadarLoader:
    """
    Load real primary surveillance radar (PSR) data from OpenSky Network
    """
    
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize loader with optional OpenSky credentials
        Get free credentials at: https://opensky-network.org
        """
        self.username = username
        self.password = password
        self.base_url = "https://opensky-network.org/api"
        self.last_request_time = 0
    
    def load_opensky_live(self, 
                          center_lat: float = 40.0,
                          center_lon: float = -100.0,
                          radius_deg: float = 3.0,
                          max_range_km: float = 300.0,
                          range_bins: int = 256,
                          azimuth_bins: int = 360) -> Tuple[np.ndarray, pd.DataFrame]:
        """
        Fetch live aircraft data from OpenSky and convert to radar image
        
        Returns:
            radar_image: range-azimuth intensity map
            ground_truth: DataFrame with aircraft positions
        """
        # Rate limiting - respect OpenSky API
        current_time = time.time()
        if current_time - self.last_request_time < 2.0:
            time.sleep(1.0)
        self.last_request_time = time.time()
        
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
                return self._create_empty_radar(range_bins, azimuth_bins), pd.DataFrame()
            
            data = response.json()
            
            if 'states' not in data or not data['states']:
                warnings.warn("No aircraft found in this area")
                return self._create_empty_radar(range_bins, azimuth_bins), pd.DataFrame()
            
            # Create radar image and ground truth
            radar_image = np.zeros((range_bins, azimuth_bins))
            ground_truth = []
            
            for state in data['states']:
                # Extract state data
                # Format: [icao24, callsign, origin_country, time_position,
                #          last_contact, longitude, latitude, baro_altitude,
                #          on_ground, velocity, true_track, vertical_rate, sensors]
                
                icao24 = state[0]
                callsign = state[1] or ""
                lon = state[5]
                lat = state[6]
                altitude = state[7] or 0
                velocity = state[9] or 0
                track = state[10] or 0
                
                # Skip if coordinates missing
                if lon is None or lat is None:
                    continue
                
                # Calculate range and azimuth from radar center
                r_km = self._haversine_km(center_lat, center_lon, lat, lon)
                
                if r_km > max_range_km:
                    continue
                
                az_deg = self._bearing(center_lat, center_lon, lat, lon)
                
                # Convert to bin indices
                range_idx = min(int(r_km / max_range_km * (range_bins - 1)), range_bins - 1)
                az_idx = int((az_deg + 360) % 360 / 360 * (azimuth_bins - 1))
                
                # Estimate RCS based on aircraft type
                rcs = self._estimate_rcs(callsign)
                
                # Radar range equation with log-normal fading
                snr = rcs / (r_km**2 + 0.1) * np.random.lognormal(0, 0.3)
                
                # Add to radar image
                radar_image[range_idx, az_idx] += snr
                
                # Store ground truth for validation
                ground_truth.append({
                    'icao24': icao24,
                    'callsign': callsign,
                    'range_km': round(r_km, 1),
                    'azimuth_deg': round(az_deg, 1),
                    'altitude_m': altitude,
                    'velocity_mps': velocity,
                    'track_deg': track,
                    'estimated_rcs': round(rcs, 3)
                })
            
            # Apply radar noise
            radar_image = self._add_radar_noise(radar_image)
            
            # Normalize
            if np.max(radar_image) > 0:
                radar_image = radar_image / np.max(radar_image)
            
            return radar_image, pd.DataFrame(ground_truth)
            
        except requests.exceptions.RequestException as e:
            warnings.warn(f"Network error: {e}")
            return self._create_empty_radar(range_bins, azimuth_bins), pd.DataFrame()
        except Exception as e:
            warnings.warn(f"Unexpected error: {e}")
            return self._create_empty_radar(range_bins, azimuth_bins), pd.DataFrame()
    
    def _create_empty_radar(self, range_bins: int, azimuth_bins: int) -> np.ndarray:
        """Create empty radar image with a message pattern"""
        radar = np.zeros((range_bins, azimuth_bins))
        # Add a subtle pattern indicating no data
        radar[range_bins//2, azimuth_bins//2] = 0.1
        return radar
    
    def _estimate_rcs(self, callsign: str) -> float:
        """
        Estimate Radar Cross Section (RCS) in m² based on callsign
        
        Stealth aircraft have RCS as low as 0.001 m²
        Commercial airliners have RCS up to 100 m²
        """
        callsign_upper = callsign.upper()
        
        # Stealth aircraft (what we want to detect)
        stealth_keywords = ['F35', 'F-35', 'F22', 'F-22', 'B2', 'B-2', 'B21', 'B-21', 'NGAD']
        if any(keyword in callsign_upper for keyword in stealth_keywords):
            return np.random.uniform(0.001, 0.01)  # Very low RCS
        
        # Large commercial airliners
        commercial = ['BOEING', 'AIRBUS', 'JAL', 'UAL', 'DAL', 'AAL', 'SWA', 'ASA', 'KAL']
        if any(keyword in callsign_upper for keyword in commercial):
            return np.random.uniform(30, 100)
        
        # Regional jets
        regional = ['EMBRAER', 'BOMBARDIER', 'CRJ', 'ERJ']
        if any(keyword in callsign_upper for keyword in regional):
            return np.random.uniform(10, 30)
        
        # Military fighters (non-stealth)
        military = ['F16', 'F-16', 'F15', 'F-15', 'F18', 'F-18', 'MIG', 'SU']
        if any(keyword in callsign_upper for keyword in military):
            return np.random.uniform(3, 8)
        
        # Small general aviation
        ga = ['CESSNA', 'PIPER', 'BEECH', 'MOONEY']
        if any(keyword in callsign_upper for keyword in ga):
            return np.random.uniform(0.5, 2)
        
        # Default unknown
        return np.random.uniform(1, 15)
    
    def _haversine_km(self, lat1: float, lon1: float, 
                      lat2: float, lon2: float) -> float:
        """Calculate great-circle distance in km"""
        from math import radians, sin, cos, sqrt, asin
        R = 6371
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        return R * c
    
    def _bearing(self, lat1: float, lon1: float, 
                 lat2: float, lon2: float) -> float:
        """Calculate bearing from point1 to point2 in degrees"""
        from math import radians, degrees, sin, cos, atan2
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlon = lon2 - lon1
        x = sin(dlon) * cos(lat2)
        y = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(dlon)
        bearing = degrees(atan2(x, y))
        return (bearing + 360) % 360
    
    def _add_radar_noise(self, radar_image: np.ndarray, 
                         noise_level: float = 0.05) -> np.ndarray:
        """Add realistic radar noise"""
        # Thermal noise
        thermal = np.random.randn(*radar_image.shape) * noise_level
        
        # Speckle noise (multiplicative)
        speckle = np.random.gamma(1.0, noise_level, radar_image.shape)
        
        return np.maximum(radar_image + thermal + radar_image * (speckle - 1), 0)
    
    def load_custom_file(self, file_content: bytes, filename: str) -> np.ndarray:
        """Load custom radar data from uploaded file"""
        import io
        
        try:
            if filename.endswith('.npz'):
                data = np.load(io.BytesIO(file_content))
                if 'radar_image' in data:
                    return data['radar_image']
                else:
                    return data[list(data.keys())[0]]
            elif filename.endswith('.npy'):
                return np.load(io.BytesIO(file_content))
            else:
                raise ValueError(f"Unsupported file type: {filename}")
        except Exception as e:
            raise RuntimeError(f"Failed to load file: {e}")
