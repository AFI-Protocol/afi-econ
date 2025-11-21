"""Anti-gaming mechanisms for AFI economic system.

This module provides light anti-gaming helpers that can be integrated
as hooks in the payout system. All mechanisms are disabled by default
and must be explicitly enabled.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta


def detect_sybil_clusters(participants_data: pd.DataFrame, 
                         similarity_threshold: float = 0.8) -> List[List[str]]:
    """Detect potential Sybil attack clusters based on behavioral similarity.
    
    Args:
        participants_data: DataFrame with participant behavior data
        similarity_threshold: Threshold for clustering similar participants
        
    Returns:
        List of clusters, each containing participant IDs
    """
    if participants_data.empty or 'participant_id' not in participants_data.columns:
        return []
    
    # Simple clustering based on activity patterns
    clusters = []
    processed = set()
    
    for _, participant in participants_data.iterrows():
        if participant['participant_id'] in processed:
            continue
            
        # Find similar participants
        cluster = [participant['participant_id']]
        processed.add(participant['participant_id'])
        
        # Simple similarity check based on timing patterns
        if 'timestamp' in participants_data.columns:
            participant_times = participants_data[
                participants_data['participant_id'] == participant['participant_id']
            ]['timestamp'].tolist()
            
            for _, other in participants_data.iterrows():
                if (other['participant_id'] not in processed and 
                    other['participant_id'] != participant['participant_id']):
                    
                    other_times = participants_data[
                        participants_data['participant_id'] == other['participant_id']
                    ]['timestamp'].tolist()
                    
                    # Check temporal similarity (simplified)
                    if len(participant_times) > 0 and len(other_times) > 0:
                        # If activities happen within similar time windows
                        time_similarity = _compute_temporal_similarity(participant_times, other_times)
                        if time_similarity > similarity_threshold:
                            cluster.append(other['participant_id'])
                            processed.add(other['participant_id'])
        
        if len(cluster) > 1:
            clusters.append(cluster)
    
    return clusters


def _compute_temporal_similarity(times1: List[str], times2: List[str]) -> float:
    """Compute temporal similarity between two activity patterns."""
    try:
        # Convert to datetime objects
        dt1 = [datetime.fromisoformat(t.replace('Z', '+00:00')) for t in times1]
        dt2 = [datetime.fromisoformat(t.replace('Z', '+00:00')) for t in times2]
        
        # Simple similarity: check if activities happen within 1 hour windows
        similar_count = 0
        total_comparisons = 0
        
        for t1 in dt1:
            for t2 in dt2:
                total_comparisons += 1
                if abs((t1 - t2).total_seconds()) < 3600:  # Within 1 hour
                    similar_count += 1
        
        return similar_count / max(total_comparisons, 1)
    except (ValueError, TypeError):
        return 0.0


def detect_wash_trading(transactions_data: pd.DataFrame,
                       min_round_trips: int = 3,
                       time_window_hours: int = 24) -> List[Dict[str, Any]]:
    """Detect potential wash trading patterns.
    
    Args:
        transactions_data: DataFrame with transaction data
        min_round_trips: Minimum round trips to flag as suspicious
        time_window_hours: Time window for detecting round trips
        
    Returns:
        List of suspicious wash trading patterns
    """
    if transactions_data.empty:
        return []
    
    required_cols = ['participant_id', 'counterparty_id', 'amount', 'timestamp']
    if not all(col in transactions_data.columns for col in required_cols):
        return []
    
    suspicious_patterns = []
    
    # Group by participant pairs
    for participant in transactions_data['participant_id'].unique():
        participant_txs = transactions_data[
            transactions_data['participant_id'] == participant
        ]
        
        for counterparty in participant_txs['counterparty_id'].unique():
            if counterparty == participant:
                continue
                
            # Find round trips between this pair
            pair_txs = transactions_data[
                ((transactions_data['participant_id'] == participant) & 
                 (transactions_data['counterparty_id'] == counterparty)) |
                ((transactions_data['participant_id'] == counterparty) & 
                 (transactions_data['counterparty_id'] == participant))
            ].sort_values('timestamp')
            
            if len(pair_txs) >= min_round_trips * 2:
                # Check for rapid back-and-forth transactions
                round_trips = _count_round_trips(pair_txs, time_window_hours)
                
                if round_trips >= min_round_trips:
                    suspicious_patterns.append({
                        'participants': [participant, counterparty],
                        'round_trips': round_trips,
                        'total_volume': pair_txs['amount'].sum(),
                        'transaction_count': len(pair_txs),
                        'pattern_type': 'wash_trading'
                    })
    
    return suspicious_patterns


def _count_round_trips(transactions: pd.DataFrame, time_window_hours: int) -> int:
    """Count round trips in transaction data."""
    round_trips = 0
    
    for i in range(len(transactions) - 1):
        current = transactions.iloc[i]
        next_tx = transactions.iloc[i + 1]
        
        # Check if it's a round trip (opposite direction within time window)
        try:
            current_time = datetime.fromisoformat(current['timestamp'].replace('Z', '+00:00'))
            next_time = datetime.fromisoformat(next_tx['timestamp'].replace('Z', '+00:00'))
            
            time_diff = (next_time - current_time).total_seconds() / 3600
            
            if (time_diff <= time_window_hours and
                current['participant_id'] == next_tx['counterparty_id'] and
                current['counterparty_id'] == next_tx['participant_id']):
                round_trips += 1
        except (ValueError, TypeError):
            continue
    
    return round_trips


def apply_gaming_penalties(payouts_data: pd.DataFrame,
                          gaming_detections: List[Dict[str, Any]],
                          penalty_rate: float = 0.1) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Apply penalties to participants flagged for gaming behavior.
    
    Args:
        payouts_data: DataFrame with payout data
        gaming_detections: List of gaming detection results
        penalty_rate: Penalty rate (0.0 to 1.0)
        
    Returns:
        Tuple of (modified_payouts, penalty_report)
    """
    if payouts_data.empty or not gaming_detections:
        return payouts_data.copy(), {"penalties_applied": 0, "total_penalty_amount": 0.0}
    
    modified_payouts = payouts_data.copy()
    penalties_applied = 0
    total_penalty_amount = 0.0
    flagged_participants = set()
    
    # Collect all flagged participants
    for detection in gaming_detections:
        if 'participants' in detection:
            flagged_participants.update(detection['participants'])
        elif 'participant_id' in detection:
            flagged_participants.add(detection['participant_id'])
    
    # Apply penalties
    for participant in flagged_participants:
        participant_mask = modified_payouts['participant_id'] == participant
        if participant_mask.any():
            original_amounts = modified_payouts.loc[participant_mask, 'amount'].copy()
            penalty_amounts = original_amounts * penalty_rate
            
            modified_payouts.loc[participant_mask, 'amount'] -= penalty_amounts
            
            penalties_applied += participant_mask.sum()
            total_penalty_amount += penalty_amounts.sum()
    
    penalty_report = {
        "penalties_applied": penalties_applied,
        "total_penalty_amount": total_penalty_amount,
        "flagged_participants": list(flagged_participants),
        "penalty_rate": penalty_rate
    }
    
    return modified_payouts, penalty_report


def run_anti_gaming_checks(participants_data: pd.DataFrame,
                          transactions_data: Optional[pd.DataFrame] = None,
                          config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Run comprehensive anti-gaming checks.
    
    Args:
        participants_data: DataFrame with participant data
        transactions_data: Optional DataFrame with transaction data
        config: Optional configuration for detection parameters
        
    Returns:
        Dictionary with all detection results
    """
    if config is None:
        config = {
            "sybil_similarity_threshold": 0.8,
            "wash_trading_min_round_trips": 3,
            "wash_trading_time_window_hours": 24,
            "enable_sybil_detection": True,
            "enable_wash_trading_detection": True
        }
    
    results = {
        "sybil_clusters": [],
        "wash_trading_patterns": [],
        "total_flags": 0,
        "config": config
    }
    
    # Sybil detection
    if config.get("enable_sybil_detection", True):
        sybil_clusters = detect_sybil_clusters(
            participants_data, 
            config.get("sybil_similarity_threshold", 0.8)
        )
        results["sybil_clusters"] = sybil_clusters
        results["total_flags"] += sum(len(cluster) for cluster in sybil_clusters)
    
    # Wash trading detection
    if (config.get("enable_wash_trading_detection", True) and 
        transactions_data is not None and not transactions_data.empty):
        wash_patterns = detect_wash_trading(
            transactions_data,
            config.get("wash_trading_min_round_trips", 3),
            config.get("wash_trading_time_window_hours", 24)
        )
        results["wash_trading_patterns"] = wash_patterns
        results["total_flags"] += len(wash_patterns)
    
    return results


def create_anti_gaming_report(detection_results: Dict[str, Any],
                             penalty_report: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create comprehensive anti-gaming report.
    
    Args:
        detection_results: Results from anti-gaming checks
        penalty_report: Optional penalty application report
        
    Returns:
        Comprehensive report dictionary
    """
    report = {
        "timestamp": datetime.now().isoformat(),
        "detection_summary": {
            "sybil_clusters_found": len(detection_results.get("sybil_clusters", [])),
            "wash_trading_patterns_found": len(detection_results.get("wash_trading_patterns", [])),
            "total_flags": detection_results.get("total_flags", 0)
        },
        "detection_details": detection_results,
        "penalties": penalty_report or {"penalties_applied": 0, "total_penalty_amount": 0.0}
    }
    
    return report
