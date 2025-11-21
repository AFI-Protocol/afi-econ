"""Allocation Gauge module for AFI Economic Kit.

This module implements the allocation gauge that blends policy weights with merit inputs
and enforces per-role caps with renormalization.
"""

from __future__ import annotations

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np


def compute_merit_inputs(receipts_df: pd.DataFrame) -> Dict[str, float]:
    """Compute normalized merit inputs from receipts data.
    
    Args:
        receipts_df: DataFrame containing receipt data with columns for merit computation
        
    Returns:
        Dictionary with normalized 0..1 merit components:
        - confidence: Average confidence score
        - novelty: Novelty metric
        - attestation_accuracy: Accuracy of attestations
        - timeliness: Timeliness metric
    """
    if receipts_df.empty:
        return {
            "confidence": 0.0,
            "novelty": 0.0,
            "attestation_accuracy": 0.0,
            "timeliness": 0.0
        }
    
    # Compute merit components (normalized to 0..1)
    # These are placeholder computations - in practice would use actual receipt data
    merit = {}
    
    # Confidence: average of confidence scores if available
    if "confidence" in receipts_df.columns:
        merit["confidence"] = float(np.clip(receipts_df["confidence"].mean(), 0, 1))
    else:
        merit["confidence"] = 0.5  # default
    
    # Novelty: based on uniqueness metrics
    if "novelty_score" in receipts_df.columns:
        merit["novelty"] = float(np.clip(receipts_df["novelty_score"].mean(), 0, 1))
    else:
        merit["novelty"] = 0.5  # default
    
    # Attestation accuracy: correctness of attestations
    if "attestation_correct" in receipts_df.columns:
        merit["attestation_accuracy"] = float(receipts_df["attestation_correct"].mean())
    else:
        merit["attestation_accuracy"] = 0.5  # default
    
    # Timeliness: based on response times
    if "response_time" in receipts_df.columns:
        # Invert and normalize response times (lower is better)
        max_time = receipts_df["response_time"].max()
        if max_time > 0:
            merit["timeliness"] = float(1.0 - (receipts_df["response_time"].mean() / max_time))
        else:
            merit["timeliness"] = 1.0
    else:
        merit["timeliness"] = 0.5  # default
    
    return merit


def _compute_bench_merit_multipliers(
    roles: list[str],
    bench_merit: Dict[str, float],
    bench_merit_weights: Dict[str, Any]
) -> Dict[str, float]:
    """Compute per-role merit multipliers from BenchKit scores.

    Args:
        roles: List of role names
        bench_merit: BenchKit scores (reputation, poi, poinsight)
        bench_merit_weights: Role mapping configuration

    Returns:
        Dictionary mapping role to merit multiplier
    """
    multipliers = {}
    epsilon = 1e-6  # Avoid zeros

    for role in roles:
        if role not in bench_merit_weights:
            # Default to neutral if role not configured
            multipliers[role] = epsilon + 0.5
            continue

        role_config = bench_merit_weights[role]

        if isinstance(role_config, (int, float)):
            # Simple scalar value (e.g., public_goods: 0.5)
            multipliers[role] = epsilon + float(role_config)
        elif isinstance(role_config, dict):
            # Weighted combination (e.g., producers: {poinsight: 0.7, reputation: 0.3})
            score = 0.0
            total_weight = 0.0

            for component, weight in role_config.items():
                if component in bench_merit and isinstance(weight, (int, float)):
                    score += bench_merit[component] * weight
                    total_weight += weight

            if total_weight > 0:
                multipliers[role] = epsilon + (score / total_weight)
            else:
                multipliers[role] = epsilon + 0.5  # Default neutral
        else:
            multipliers[role] = epsilon + 0.5  # Default neutral

    return multipliers


def allocation_gauge(
    weights: Dict[str, float],
    caps: Dict[str, float],
    merit: Dict[str, float],
    blend: float = 0.5,
    bench_merit: Optional[Dict[str, float]] = None,
    bench_merit_weights: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Apply allocation gauge with policy weights, merit inputs, and caps.

    Args:
        weights: Policy weights for each role (should sum to 1.0)
        caps: Caps configuration including per_role_max
        merit: Merit inputs for blending
        blend: Blend factor between policy (0.0) and merit (1.0)
        bench_merit: BenchKit scores (reputation, poi, poinsight)
        bench_merit_weights: Role mapping configuration for BenchKit scores

    Returns:
        Dictionary containing:
        - raw: Raw allocation before caps
        - capped: Final allocation after caps and renormalization
        - diag: Diagnostics including which roles were capped
    """
    roles = list(weights.keys())
    per_role_max = caps.get("per_role_max", 1.0)
    
    # Start with policy weights
    raw_allocation = dict(weights)
    
    # Blend with merit if blend > 0
    if blend > 0 and merit:
        # Simple merit blending - adjust weights based on merit scores
        merit_avg = np.mean(list(merit.values()))
        for role in roles:
            # Blend policy weight with merit-adjusted weight
            merit_weight = weights[role] * (1.0 + merit_avg)
            raw_allocation[role] = (1 - blend) * weights[role] + blend * merit_weight

    # Apply BenchKit merit multipliers if provided
    if bench_merit and bench_merit_weights:
        # Set default bench_merit_weights if not provided
        if bench_merit_weights is None:
            bench_merit_weights = {
                "producers": {"poinsight": 0.7, "reputation": 0.3},
                "validators": {"reputation": 1.0},
                "enrichment": {"poinsight": 0.6, "reputation": 0.4},
                "public_goods": 0.5
            }

        # Compute per-role multipliers
        multipliers = _compute_bench_merit_multipliers(roles, bench_merit, bench_merit_weights)

        # Apply multipliers to raw allocation
        for role in roles:
            raw_allocation[role] *= multipliers[role]

    # Normalize raw allocation to sum to 1.0
    total_raw = sum(raw_allocation.values())
    if total_raw > 0:
        raw_allocation = {role: val / total_raw for role, val in raw_allocation.items()}
    
    # Apply per-role caps with proper renormalization
    capped_allocation = {}
    capped_roles = []
    excess_allocation = 0.0

    # First pass: apply caps and track excess
    for role, allocation in raw_allocation.items():
        if allocation > per_role_max:
            capped_allocation[role] = per_role_max
            capped_roles.append(role)
            excess_allocation += allocation - per_role_max
        else:
            capped_allocation[role] = allocation

    # Second pass: redistribute excess to uncapped roles
    if excess_allocation > 0:
        uncapped_roles = [role for role in roles if role not in capped_roles]
        if uncapped_roles:
            # Distribute excess proportionally among uncapped roles
            uncapped_total = sum(capped_allocation[role] for role in uncapped_roles)
            if uncapped_total > 0:
                for role in uncapped_roles:
                    proportion = capped_allocation[role] / uncapped_total
                    additional = excess_allocation * proportion
                    # Make sure we don't exceed cap when redistributing
                    new_allocation = min(capped_allocation[role] + additional, per_role_max)
                    if new_allocation > capped_allocation[role]:
                        capped_allocation[role] = new_allocation

    # Final normalization to ensure sum equals 1.0
    total_capped = sum(capped_allocation.values())
    if total_capped > 0:
        # Only normalize if we're not at exactly 1.0 already
        if abs(total_capped - 1.0) > 1e-10:
            # For capped roles, maintain their caps during normalization
            # Only adjust uncapped roles
            uncapped_roles = [role for role in roles if role not in capped_roles]
            if uncapped_roles:
                uncapped_current = sum(capped_allocation[role] for role in uncapped_roles)
                target_uncapped = 1.0 - sum(capped_allocation[role] for role in capped_roles)
                if uncapped_current > 0 and target_uncapped > 0:
                    scale_factor = target_uncapped / uncapped_current
                    for role in uncapped_roles:
                        capped_allocation[role] *= scale_factor
            else:
                # All roles are capped, just normalize proportionally
                for role in roles:
                    capped_allocation[role] /= total_capped
    
    # Diagnostics
    diagnostics = {
        "capped_roles": capped_roles,
        "total_raw": total_raw,
        "total_capped": sum(capped_allocation.values()),
        "blend_factor": blend,
        "merit_applied": blend > 0 and bool(merit),
        "bench_merit_applied": bench_merit is not None and bench_merit_weights is not None
    }
    
    return {
        "raw": raw_allocation,
        "capped": capped_allocation,
        "diag": diagnostics
    }
