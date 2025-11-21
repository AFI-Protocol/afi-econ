"""Pydantic schemas for AFI Econ Kit data structures."""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator


class ParticipantData(BaseModel):
    """Schema for participant data."""
    participant_id: str = Field(..., description="Unique participant identifier")
    role: Optional[str] = Field(None, description="Participant role (reputation, poi, poinsight, etc.)")
    region: Optional[str] = Field(None, description="Geographic region")
    amount: Optional[float] = Field(None, ge=0, description="Associated amount")
    timestamp: Optional[str] = Field(None, description="ISO timestamp")


class ReceiptData(BaseModel):
    """Schema for receipt data."""
    participant_id: str = Field(..., description="Participant identifier")
    role: str = Field(..., description="Participant role")
    region: Optional[str] = Field(None, description="Geographic region")
    amount: float = Field(..., ge=0, description="Receipt amount")
    timestamp: str = Field(..., description="ISO timestamp")
    receipt_id: Optional[str] = Field(None, description="Unique receipt identifier")


class PayoutData(BaseModel):
    """Schema for payout data."""
    participant_id: str = Field(..., description="Participant identifier")
    role: str = Field(..., description="Participant role")
    amount: float = Field(..., ge=0, description="Payout amount")
    epoch: int = Field(..., ge=1, description="Epoch number")
    payout_type: Optional[str] = Field(None, description="Type of payout")


class GaugeConfig(BaseModel):
    """Schema for gauge configuration."""
    policy_weight: float = Field(0.7, ge=0, le=1, description="Weight for policy allocation")
    merit_weight: float = Field(0.3, ge=0, le=1, description="Weight for merit allocation")
    smoothing_factor: float = Field(0.1, ge=0, le=1, description="Smoothing factor")
    min_allocation: float = Field(0.01, ge=0, le=1, description="Minimum allocation per participant")
    
    @validator('merit_weight')
    def weights_sum_to_one(cls, v, values):
        if 'policy_weight' in values:
            if abs(v + values['policy_weight'] - 1.0) > 1e-6:
                raise ValueError('policy_weight + merit_weight must equal 1.0')
        return v


class SafetyConfig(BaseModel):
    """Schema for safety mechanism configuration."""
    max_change_rate: float = Field(0.2, ge=0, le=1, description="Maximum change rate per epoch")
    smoothing_window: int = Field(3, ge=1, description="Smoothing window size")
    enable_caps: bool = Field(True, description="Enable allocation caps")
    cap_percentile: float = Field(0.95, ge=0, le=1, description="Cap percentile")


class BudgetData(BaseModel):
    """Schema for AFI emissions budget data."""
    epoch: int = Field(..., ge=1, description="Epoch number")
    B_t: float = Field(..., ge=0, description="Baseline emissions")
    E_t: float = Field(..., ge=0, description="Final epoch pool")
    AIM: Dict[str, Any] = Field(..., description="AIM adjustment data")


class IndexWeights(BaseModel):
    """Schema for AFI Index weights."""
    an: float = Field(0.4, ge=0, le=1, description="Active Network weight")
    eg: float = Field(0.35, ge=0, le=1, description="Economic Growth weight")
    cov: float = Field(0.25, ge=0, le=1, description="Coverage weight")
    
    @validator('cov')
    def weights_sum_to_one(cls, v, values):
        total = v + values.get('an', 0) + values.get('eg', 0)
        if abs(total - 1.0) > 1e-6:
            raise ValueError('Index weights must sum to 1.0')
        return v


class IndexComponents(BaseModel):
    """Schema for AFI Index components."""
    AN_t: float = Field(..., ge=0, le=1, description="Active Network metric")
    EG_t: float = Field(..., ge=0, le=1, description="Economic Growth metric")
    Cov_t: float = Field(..., ge=0, le=1, description="Coverage metric")


class IndexResults(BaseModel):
    """Schema for AFI Index computation results."""
    epoch: int = Field(..., ge=1, description="Epoch number")
    components: IndexComponents = Field(..., description="Index components")
    weights: IndexWeights = Field(..., description="Index weights")
    I_t: float = Field(..., ge=0, le=1, description="Final AFI Index")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ProvenanceStamp(BaseModel):
    """Schema for provenance stamp."""
    version: str = Field(..., description="Package version")
    git_sha: str = Field(..., description="Git commit SHA")
    utc_ts: str = Field(..., description="UTC timestamp")
    module: str = Field(..., description="Module name")
    config_hash: Optional[str] = Field(None, description="Configuration file hash")
    data_hash: Optional[str] = Field(None, description="Input data hash")


class SimulationConfig(BaseModel):
    """Schema for simulation configuration."""
    monte_carlo_runs: int = Field(100, ge=1, description="Number of Monte Carlo runs")
    random_seed: int = Field(42, ge=0, description="Random seed for reproducibility")
    output_plots: bool = Field(True, description="Generate output plots")
    save_intermediate: bool = Field(False, description="Save intermediate results")


class EconomicSummary(BaseModel):
    """Schema for economic summary results."""
    total_participants: int = Field(..., ge=0, description="Total number of participants")
    total_payouts: float = Field(..., ge=0, description="Total payout amount")
    average_payout: float = Field(..., ge=0, description="Average payout per participant")
    payout_distribution: Dict[str, float] = Field(..., description="Payout distribution by role")
    epoch: int = Field(..., ge=1, description="Epoch number")
    stamp: ProvenanceStamp = Field(..., description="Provenance information")


class AntiGamingConfig(BaseModel):
    """Schema for anti-gaming configuration."""
    enable_sybil_detection: bool = Field(False, description="Enable Sybil attack detection")
    enable_wash_trading_detection: bool = Field(False, description="Enable wash trading detection")
    sybil_similarity_threshold: float = Field(0.8, ge=0, le=1, description="Sybil similarity threshold")
    wash_trading_min_round_trips: int = Field(3, ge=1, description="Minimum round trips for wash trading")
    wash_trading_time_window_hours: int = Field(24, ge=1, description="Time window for wash trading detection")
    penalty_rate: float = Field(0.1, ge=0, le=1, description="Penalty rate for gaming behavior")


class AntiGamingReport(BaseModel):
    """Schema for anti-gaming report."""
    timestamp: str = Field(..., description="Report timestamp")
    detection_summary: Dict[str, int] = Field(..., description="Detection summary")
    detection_details: Dict[str, Any] = Field(..., description="Detailed detection results")
    penalties: Dict[str, Any] = Field(..., description="Penalty information")


class StageInput(BaseModel):
    """Base schema for stage inputs."""
    epoch: int = Field(..., ge=1, description="Epoch number")
    config: Dict[str, Any] = Field(default_factory=dict, description="Stage configuration")
    input_data: List[Dict[str, Any]] = Field(..., description="Input data")


class StageOutput(BaseModel):
    """Base schema for stage outputs."""
    epoch: int = Field(..., ge=1, description="Epoch number")
    output_data: List[Dict[str, Any]] = Field(..., description="Output data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Stage metadata")
    stamp: ProvenanceStamp = Field(..., description="Provenance information")


class GaugeInput(StageInput):
    """Schema for gauge stage input."""
    receipts: List[ReceiptData] = Field(..., description="Receipt data")
    policy_allocation: Dict[str, float] = Field(..., description="Policy-based allocation")
    merit_scores: Optional[Dict[str, float]] = Field(None, description="Merit scores from BenchKit")


class GaugeOutput(StageOutput):
    """Schema for gauge stage output."""
    allocations: Dict[str, float] = Field(..., description="Final allocations")
    policy_component: Dict[str, float] = Field(..., description="Policy component")
    merit_component: Dict[str, float] = Field(..., description="Merit component")


class SafetyInput(StageInput):
    """Schema for safety stage input."""
    current_allocations: Dict[str, float] = Field(..., description="Current epoch allocations")
    previous_allocations: Optional[Dict[str, float]] = Field(None, description="Previous epoch allocations")


class SafetyOutput(StageOutput):
    """Schema for safety stage output."""
    smoothed_allocations: Dict[str, float] = Field(..., description="Smoothed allocations")
    applied_caps: Dict[str, float] = Field(..., description="Applied caps")
    change_rates: Dict[str, float] = Field(..., description="Change rates")


class PayoutsInput(StageInput):
    """Schema for payouts stage input."""
    allocations: Dict[str, float] = Field(..., description="Final allocations")
    budget: Optional[BudgetData] = Field(None, description="Budget data")
    total_pool: float = Field(..., ge=0, description="Total payout pool")


class PayoutsOutput(StageOutput):
    """Schema for payouts stage output."""
    payouts: List[PayoutData] = Field(..., description="Final payouts")
    total_distributed: float = Field(..., ge=0, description="Total amount distributed")
    distribution_summary: Dict[str, float] = Field(..., description="Distribution summary by role")


# Validation functions
def validate_receipts_data(data: List[Dict[str, Any]]) -> List[ReceiptData]:
    """Validate and convert receipts data."""
    return [ReceiptData(**item) for item in data]


def validate_payouts_data(data: List[Dict[str, Any]]) -> List[PayoutData]:
    """Validate and convert payouts data."""
    return [PayoutData(**item) for item in data]


def validate_budget_data(data: Dict[str, Any]) -> BudgetData:
    """Validate and convert budget data."""
    return BudgetData(**data)


def validate_index_results(data: Dict[str, Any]) -> IndexResults:
    """Validate and convert index results."""
    return IndexResults(**data)
