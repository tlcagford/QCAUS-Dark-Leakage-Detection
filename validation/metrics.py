"""
Detection metrics for StealthPDPRadar validation
"""

import numpy as np
from typing import Dict

def compute_detection_metrics(probability_map: np.ndarray, 
                              ground_truth_mask: np.ndarray,
                              threshold: float = 0.5) -> Dict[str, float]:
    """
    Compute detection metrics for stealth probability map
    """
    # Binarize probability map
    detections = probability_map > threshold
    
    # Ensure boolean type
    detections = detections.astype(bool)
    ground_truth = ground_truth_mask.astype(bool)
    
    # Compute counts
    true_positives = np.sum(detections & ground_truth)
    false_positives = np.sum(detections & ~ground_truth)
    false_negatives = np.sum(~detections & ground_truth)
    
    # Calculate metrics
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
    f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return {
        'precision': precision,
        'recall': recall,
        'f1_score': f1_score,
        'true_positives': int(true_positives),
        'false_positives': int(false_positives),
        'false_negatives': int(false_negatives),
        'total_targets': int(np.sum(ground_truth))
    }
