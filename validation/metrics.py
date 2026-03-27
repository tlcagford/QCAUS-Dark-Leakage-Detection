"""
Detection metrics for StealthPDPRadar validation
"""

import numpy as np
from typing import Dict, Tuple

def compute_detection_metrics(probability_map: np.ndarray, 
                              ground_truth_mask: np.ndarray,
                              threshold: float = 0.5) -> Dict[str, float]:
    """
    Compute detection metrics for stealth probability map
    
    Parameters:
    -----------
    probability_map : np.ndarray
        Stealth probability output from PDP filter
    ground_truth_mask : np.ndarray
        Binary mask of actual stealth object positions
    threshold : float
        Detection threshold (0-1)
    
    Returns:
    --------
    metrics : dict
        Precision, recall, F1 score, and counts
    """
    # Binarize probability map
    detections = probability_map > threshold
    
    # Ensure boolean type
    detections = detections.astype(bool)
    ground_truth = ground_truth_mask.astype(bool)
    
    # Compute true positives, false positives, false negatives
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

def compute_roc_curve(probability_map: np.ndarray, 
                      ground_truth_mask: np.ndarray,
                      num_thresholds: int = 50) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute ROC curve for detection performance
    
    Returns:
    --------
    fpr : array
        False positive rates
    tpr : array
        True positive rates
    thresholds : array
        Threshold values
    """
    thresholds = np.linspace(0, 1, num_thresholds)
    tpr = np.zeros(num_thresholds)
    fpr = np.zeros(num_thresholds)
    
    for i, thresh in enumerate(thresholds):
        detections = probability_map > thresh
        tp = np.sum(detections & ground_truth_mask)
        fp = np.sum(detections & ~ground_truth_mask)
        fn = np.sum(~detections & ground_truth_mask)
        tn = np.sum(~detections & ~ground_truth_mask)
        
        tpr[i] = tp / (tp + fn) if (tp + fn) > 0 else 0
        fpr[i] = fp / (fp + tn) if (fp + tn) > 0 else 0
    
    return fpr, tpr, thresholds

def compute_auc(fpr: np.ndarray, tpr: np.ndarray) -> float:
    """Compute Area Under Curve (AUC)"""
    return np.trapz(tpr, fpr)
