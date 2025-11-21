"""Safety and Smoothing module for AFI Economic Kit.

This module implements rate limiting, exponential smoothing, and circuit breakers
for the economic pipeline.
"""

from __future__ import annotations

from typing import Dict, Any, Optional
import numpy as np


def rate_limit(prev: float, new: float, limit: float) -> float:
    """Apply rate limiting to prevent large changes.
    
    Args:
        prev: Previous value
        new: New proposed value
        limit: Maximum fractional change allowed (e.g., 0.2 for 20%)
        
    Returns:
        Rate-limited value
    """
    if prev == 0:
        return new
    
    max_change = abs(prev * limit)
    change = new - prev
    
    if abs(change) <= max_change:
        return new
    
    # Limit the change
    if change > 0:
        return prev + max_change
    else:
        return prev - max_change


def exp_smooth(prev: float, new: float, alpha: float) -> float:
    """Apply exponential smoothing.
    
    Args:
        prev: Previous smoothed value
        new: New raw value
        alpha: Smoothing factor (0 = no change, 1 = no smoothing)
        
    Returns:
        Smoothed value
    """
    alpha = np.clip(alpha, 0.0, 1.0)
    return alpha * new + (1 - alpha) * prev


def circuit_breaker(metrics: Dict[str, float], thresholds: Dict[str, float]) -> Dict[str, Any]:
    """Check circuit breaker conditions.
    
    Args:
        metrics: Current system metrics
        thresholds: Threshold values for each metric
        
    Returns:
        Dictionary with:
        - tripped: Boolean indicating if breaker is tripped
        - reason: String describing why breaker tripped (None if not tripped)
        - triggered_metrics: List of metrics that exceeded thresholds
    """
    triggered_metrics = []
    reasons = []
    
    for metric, value in metrics.items():
        threshold = thresholds.get(metric)
        if threshold is not None and value > threshold:
            triggered_metrics.append(metric)
            reasons.append(f"{metric}={value:.3f} > {threshold:.3f}")
    
    tripped = len(triggered_metrics) > 0
    reason = "; ".join(reasons) if reasons else None
    
    return {
        "tripped": tripped,
        "reason": reason,
        "triggered_metrics": triggered_metrics
    }


def apply_safety_controls(
    prev_state: Dict[str, Any],
    new_state: Dict[str, Any],
    safety_config: Dict[str, Any]
) -> Dict[str, Any]:
    """Apply all safety controls to state transition.
    
    Args:
        prev_state: Previous system state
        new_state: Proposed new system state
        safety_config: Safety configuration parameters
        
    Returns:
        Safe state after applying all controls
    """
    safe_state = dict(new_state)
    
    # Apply budget rate limiting
    budget_limit = safety_config.get("budget_rate_limit", 0.2)
    if "budget" in prev_state and "budget" in new_state:
        safe_state["budget"] = rate_limit(
            prev_state["budget"], 
            new_state["budget"], 
            budget_limit
        )
    
    # Apply weight rate limiting
    weight_limit = safety_config.get("weight_rate_limit", 0.15)
    if "weights" in prev_state and "weights" in new_state:
        safe_weights = {}
        for role in new_state["weights"]:
            prev_weight = prev_state["weights"].get(role, 0.0)
            new_weight = new_state["weights"][role]
            safe_weights[role] = rate_limit(prev_weight, new_weight, weight_limit)
        safe_state["weights"] = safe_weights
    
    # Apply exponential smoothing
    smoothing_alpha = safety_config.get("smoothing_alpha", 0.25)
    if "smoothed_metrics" in prev_state:
        smoothed = {}
        for metric, new_value in new_state.get("metrics", {}).items():
            prev_value = prev_state["smoothed_metrics"].get(metric, new_value)
            smoothed[metric] = exp_smooth(prev_value, new_value, smoothing_alpha)
        safe_state["smoothed_metrics"] = smoothed
    
    # Check circuit breakers
    breaker_config = safety_config.get("breaker", {})
    if "metrics" in safe_state and breaker_config:
        breaker_result = circuit_breaker(safe_state["metrics"], breaker_config)
        safe_state["circuit_breaker"] = breaker_result
        
        # If breaker is tripped, revert to previous state for critical components
        if breaker_result["tripped"]:
            # Keep previous budget and weights if breaker trips
            if "budget" in prev_state:
                safe_state["budget"] = prev_state["budget"]
            if "weights" in prev_state:
                safe_state["weights"] = prev_state["weights"]
    
    return safe_state
