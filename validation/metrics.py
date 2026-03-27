import numpy as np

def compute_detection_metrics(probability_map, ground_truth_mask, threshold=0.5):
    detections = probability_map > threshold
    true_positives = np.sum(detections & ground_truth_mask)
    false_positives = np.sum(detections & ~ground_truth_mask)
    false_negatives = np.sum(~detections & ground_truth_mask)
    
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    return {
        'precision': precision,
        'recall': recall,
        'f1_score': f1,
        'true_positives': true_positives,
        'false_positives': false_positives,
        'false_negatives': false_negatives
    }
