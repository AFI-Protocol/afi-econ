"""Payouts module for AFI Economic Kit.

This module handles budget computation, gauge application, and role-based payouts
with maturity holdbacks.
"""

from __future__ import annotations

from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np


def compute_pool(B_t: float, aim_enabled: bool, aim_params: Dict[str, float]) -> float:
    """Compute the total pool for the epoch.
    
    Args:
        B_t: Base budget for the epoch
        aim_enabled: Whether AIM (Adaptive Issuance Mechanism) is enabled
        aim_params: AIM parameters including 'k' factor
        
    Returns:
        Total pool amount for distribution
    """
    if not aim_enabled:
        return B_t
    
    # Apply AIM adjustment
    k = aim_params.get("k", 0.0)
    # Simple AIM formula: pool = B_t * (1 + k)
    # In practice, this would be more sophisticated based on network metrics
    return B_t * (1.0 + k)


def apply_gauge(pool: float, shares: Dict[str, float]) -> Dict[str, float]:
    """Apply gauge shares to distribute pool across roles.
    
    Args:
        pool: Total pool amount to distribute
        shares: Share allocation for each role (should sum to 1.0)
        
    Returns:
        Dictionary mapping role to pool amount
    """
    role_pools = {}
    
    # Normalize shares to ensure they sum to 1.0
    total_shares = sum(shares.values())
    if total_shares > 0:
        normalized_shares = {role: share / total_shares for role, share in shares.items()}
    else:
        # Equal distribution if no shares provided
        num_roles = len(shares)
        normalized_shares = {role: 1.0 / num_roles for role in shares.keys()}
    
    # Distribute pool according to shares
    for role, share in normalized_shares.items():
        role_pools[role] = pool * share
    
    return role_pools


def role_payouts(
    role_pool: float,
    credits_df: pd.DataFrame,
    maturity_hold_frac: float
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Compute payouts and holdbacks for a specific role.
    
    Args:
        role_pool: Total pool amount for this role
        credits_df: DataFrame with credit information (participant_id, credits, etc.)
        maturity_hold_frac: Fraction to hold back for maturity (e.g., 0.15 for 15%)
        
    Returns:
        Tuple of (payouts_df, holdback_df)
    """
    if credits_df.empty:
        # Return empty DataFrames with correct structure
        empty_df = pd.DataFrame(columns=["participant_id", "amount"])
        return empty_df, empty_df
    
    # Calculate total credits for proportional distribution
    total_credits = credits_df["credits"].sum()
    
    if total_credits <= 0:
        # No credits to distribute
        empty_df = pd.DataFrame(columns=["participant_id", "amount"])
        return empty_df, empty_df
    
    # Calculate immediate payout pool (after holdback)
    immediate_pool = role_pool * (1.0 - maturity_hold_frac)
    holdback_pool = role_pool * maturity_hold_frac
    
    # Proportional distribution based on credits
    payouts_data = []
    holdback_data = []
    
    for _, row in credits_df.iterrows():
        participant_id = row["participant_id"]
        credits = row["credits"]
        
        # Proportional share
        share = credits / total_credits
        
        # Immediate payout
        payout_amount = immediate_pool * share
        payouts_data.append({
            "participant_id": participant_id,
            "amount": payout_amount,
            "credits": credits,
            "share": share
        })
        
        # Holdback amount
        holdback_amount = holdback_pool * share
        holdback_data.append({
            "participant_id": participant_id,
            "amount": holdback_amount,
            "credits": credits,
            "share": share
        })
    
    payouts_df = pd.DataFrame(payouts_data)
    holdback_df = pd.DataFrame(holdback_data)
    
    return payouts_df, holdback_df


def compute_epoch_payouts(
    budget: float,
    aim_config: Dict[str, Any],
    gauge_shares: Dict[str, float],
    role_credits: Dict[str, pd.DataFrame],
    maturity_hold_frac: float
) -> Dict[str, Any]:
    """Compute complete epoch payouts across all roles.
    
    Args:
        budget: Base budget for the epoch
        aim_config: AIM configuration
        gauge_shares: Share allocation from gauge
        role_credits: Dictionary mapping role to credits DataFrame
        maturity_hold_frac: Maturity holdback fraction
        
    Returns:
        Dictionary containing:
        - total_pool: Total pool computed
        - role_pools: Pool amounts per role
        - payouts: Payouts per role
        - holdbacks: Holdbacks per role
        - summary: Summary statistics
    """
    # Compute total pool
    total_pool = compute_pool(
        budget,
        aim_config.get("aim_enabled", False),
        aim_config.get("aim_params", {})
    )
    
    # Apply gauge to get role pools
    role_pools = apply_gauge(total_pool, gauge_shares)
    
    # Compute payouts and holdbacks for each role
    payouts = {}
    holdbacks = {}
    
    for role, pool_amount in role_pools.items():
        credits_df = role_credits.get(role, pd.DataFrame())
        
        role_payouts_df, role_holdbacks_df = role_payouts(
            pool_amount, credits_df, maturity_hold_frac
        )
        
        payouts[role] = role_payouts_df
        holdbacks[role] = role_holdbacks_df
    
    # Compute summary statistics
    total_payouts = sum(
        df["amount"].sum() if not df.empty else 0.0 
        for df in payouts.values()
    )
    total_holdbacks = sum(
        df["amount"].sum() if not df.empty else 0.0 
        for df in holdbacks.values()
    )
    
    summary = {
        "total_pool": total_pool,
        "total_payouts": total_payouts,
        "total_holdbacks": total_holdbacks,
        "utilization": (total_payouts + total_holdbacks) / total_pool if total_pool > 0 else 0.0
    }
    
    return {
        "total_pool": total_pool,
        "role_pools": role_pools,
        "payouts": payouts,
        "holdbacks": holdbacks,
        "summary": summary
    }
