"""Tests for safety operations: rate limiting, smoothing, and circuit breakers."""

import pytest
from afi_econ_kit.safety import rate_limit, exp_smooth, circuit_breaker, apply_safety_controls


def test_rate_limit_no_change():
    """Test rate limiting when change is within limits."""
    prev = 100.0
    new = 110.0  # 10% increase
    limit = 0.2  # 20% limit
    
    result = rate_limit(prev, new, limit)
    assert result == new  # Should allow the change


def test_rate_limit_positive_clamp():
    """Test rate limiting clamps positive changes."""
    prev = 100.0
    new = 150.0  # 50% increase
    limit = 0.2  # 20% limit
    
    result = rate_limit(prev, new, limit)
    expected = prev + (prev * limit)  # 100 + 20 = 120
    assert result == expected


def test_rate_limit_negative_clamp():
    """Test rate limiting clamps negative changes."""
    prev = 100.0
    new = 50.0  # 50% decrease
    limit = 0.2  # 20% limit
    
    result = rate_limit(prev, new, limit)
    expected = prev - (prev * limit)  # 100 - 20 = 80
    assert result == expected


def test_rate_limit_zero_prev():
    """Test rate limiting with zero previous value."""
    prev = 0.0
    new = 50.0
    limit = 0.2
    
    result = rate_limit(prev, new, limit)
    assert result == new  # Should return new value when prev is 0


def test_exp_smooth_no_smoothing():
    """Test exponential smoothing with alpha=1 (no smoothing)."""
    prev = 10.0
    new = 20.0
    alpha = 1.0
    
    result = exp_smooth(prev, new, alpha)
    assert result == new


def test_exp_smooth_no_change():
    """Test exponential smoothing with alpha=0 (no change)."""
    prev = 10.0
    new = 20.0
    alpha = 0.0
    
    result = exp_smooth(prev, new, alpha)
    assert result == prev


def test_exp_smooth_partial():
    """Test exponential smoothing with partial alpha."""
    prev = 10.0
    new = 20.0
    alpha = 0.5
    
    result = exp_smooth(prev, new, alpha)
    expected = 0.5 * 20.0 + 0.5 * 10.0  # 15.0
    assert result == expected


def test_exp_smooth_alpha_clipping():
    """Test that alpha is clipped to [0, 1] range."""
    prev = 10.0
    new = 20.0
    
    # Test alpha > 1
    result1 = exp_smooth(prev, new, 1.5)
    assert result1 == new  # Should be clipped to alpha=1
    
    # Test alpha < 0
    result2 = exp_smooth(prev, new, -0.5)
    assert result2 == prev  # Should be clipped to alpha=0


def test_circuit_breaker_no_trip():
    """Test circuit breaker with metrics below thresholds."""
    metrics = {
        "dispute_rate": 0.05,
        "error_rate": 0.02
    }
    thresholds = {
        "dispute_rate": 0.08,
        "error_rate": 0.05
    }
    
    result = circuit_breaker(metrics, thresholds)
    
    assert result["tripped"] is False
    assert result["reason"] is None
    assert result["triggered_metrics"] == []


def test_circuit_breaker_single_trip():
    """Test circuit breaker with one metric exceeding threshold."""
    metrics = {
        "dispute_rate": 0.10,  # Exceeds threshold
        "error_rate": 0.02
    }
    thresholds = {
        "dispute_rate": 0.08,
        "error_rate": 0.05
    }
    
    result = circuit_breaker(metrics, thresholds)
    
    assert result["tripped"] is True
    assert "dispute_rate=0.100 > 0.080" in result["reason"]
    assert result["triggered_metrics"] == ["dispute_rate"]


def test_circuit_breaker_multiple_trip():
    """Test circuit breaker with multiple metrics exceeding thresholds."""
    metrics = {
        "dispute_rate": 0.10,  # Exceeds threshold
        "error_rate": 0.08     # Exceeds threshold
    }
    thresholds = {
        "dispute_rate": 0.08,
        "error_rate": 0.05
    }
    
    result = circuit_breaker(metrics, thresholds)
    
    assert result["tripped"] is True
    assert "dispute_rate=0.100 > 0.080" in result["reason"]
    assert "error_rate=0.080 > 0.050" in result["reason"]
    assert set(result["triggered_metrics"]) == {"dispute_rate", "error_rate"}


def test_circuit_breaker_missing_threshold():
    """Test circuit breaker ignores metrics without thresholds."""
    metrics = {
        "dispute_rate": 0.10,
        "unknown_metric": 0.95  # No threshold defined
    }
    thresholds = {
        "dispute_rate": 0.08
    }
    
    result = circuit_breaker(metrics, thresholds)
    
    assert result["tripped"] is True
    assert result["triggered_metrics"] == ["dispute_rate"]


def test_apply_safety_controls_budget_rate_limit():
    """Test safety controls apply budget rate limiting."""
    prev_state = {
        "budget": 1000.0,
        "weights": {"role1": 0.5, "role2": 0.5}
    }
    
    new_state = {
        "budget": 1500.0,  # 50% increase
        "weights": {"role1": 0.6, "role2": 0.4}
    }
    
    safety_config = {
        "budget_rate_limit": 0.2,  # 20% limit
        "weight_rate_limit": 0.15
    }
    
    result = apply_safety_controls(prev_state, new_state, safety_config)
    
    # Budget should be rate limited
    expected_budget = 1000.0 + (1000.0 * 0.2)  # 1200.0
    assert result["budget"] == expected_budget


def test_apply_safety_controls_weight_rate_limit():
    """Test safety controls apply weight rate limiting."""
    prev_state = {
        "budget": 1000.0,
        "weights": {"role1": 0.5, "role2": 0.5}
    }
    
    new_state = {
        "budget": 1000.0,
        "weights": {"role1": 0.8, "role2": 0.2}  # Large change in role1
    }
    
    safety_config = {
        "budget_rate_limit": 0.2,
        "weight_rate_limit": 0.1  # 10% limit
    }
    
    result = apply_safety_controls(prev_state, new_state, safety_config)
    
    # role1 weight should be rate limited
    expected_role1 = 0.5 + (0.5 * 0.1)  # 0.55
    assert result["weights"]["role1"] == expected_role1


def test_apply_safety_controls_circuit_breaker():
    """Test safety controls with circuit breaker activation."""
    prev_state = {
        "budget": 1000.0,
        "weights": {"role1": 0.5, "role2": 0.5}
    }
    
    new_state = {
        "budget": 1100.0,
        "weights": {"role1": 0.6, "role2": 0.4},
        "metrics": {"dispute_rate": 0.15}  # High dispute rate
    }
    
    safety_config = {
        "budget_rate_limit": 0.2,
        "weight_rate_limit": 0.15,
        "breaker": {"dispute_rate": 0.08}  # Low threshold
    }
    
    result = apply_safety_controls(prev_state, new_state, safety_config)
    
    # Circuit breaker should be tripped
    assert result["circuit_breaker"]["tripped"] is True
    
    # Budget and weights should revert to previous state
    assert result["budget"] == prev_state["budget"]
    assert result["weights"] == prev_state["weights"]


def test_apply_safety_controls_smoothing():
    """Test safety controls apply exponential smoothing."""
    prev_state = {
        "smoothed_metrics": {"load": 0.5, "latency": 100.0}
    }
    
    new_state = {
        "metrics": {"load": 0.8, "latency": 200.0}
    }
    
    safety_config = {
        "smoothing_alpha": 0.3
    }
    
    result = apply_safety_controls(prev_state, new_state, safety_config)
    
    # Metrics should be smoothed
    expected_load = 0.3 * 0.8 + 0.7 * 0.5  # 0.59
    expected_latency = 0.3 * 200.0 + 0.7 * 100.0  # 130.0
    
    assert result["smoothed_metrics"]["load"] == pytest.approx(expected_load, abs=1e-10)
    assert result["smoothed_metrics"]["latency"] == pytest.approx(expected_latency, abs=1e-10)
