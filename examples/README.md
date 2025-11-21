# AFI Econ Kit Examples

This directory contains example data files and configurations for testing and demonstrating the AFI Econ Kit functionality.

## Files Overview

### Configuration Files
- `config.yaml` - Main simulation configuration
- `params/gauge_v0.yaml` - Gauge allocation parameters
- `params/safety_v0.yaml` - Safety mechanism parameters

### Sample Data Files
- `receipts.json` - Sample receipt data with participant activities
- `payouts.json` - Sample payout data for index computation
- `epoch_budget.json` - Sample AFI emissions budget data
- `scores_min.json` - Minimal BenchKit scores for testing

### Integration Examples
- `pipeline_demo.sh` - Complete end-to-end pipeline demonstration
- `stage_by_stage.sh` - Individual stage processing example

## Quick Start Examples

### 1. Basic Simulation
```bash
# Run basic economic simulation
afi-econ-kit simulate --config examples/config.yaml --outdir basic_sim
```

### 2. Simulation with Budget Integration
```bash
# Run simulation with AFI emissions budget
afi-econ-kit simulate --config examples/config.yaml --outdir budget_sim \
  --budget examples/epoch_budget.json
```

### 3. Simulation with BenchKit Integration
```bash
# Run simulation with merit scores
afi-econ-kit simulate --config examples/config.yaml --outdir merit_sim \
  --scores examples/scores_min.json
```

### 4. Full Integration (Budget + Merit)
```bash
# Run simulation with both budget and merit scores
afi-econ-kit simulate --config examples/config.yaml --outdir full_sim \
  --budget examples/epoch_budget.json --scores examples/scores_min.json
```

### 5. AFI Index Computation
```bash
# Compute AFI Index from sample data
afi-econ-kit index --receipts examples/receipts.json \
  --payouts examples/payouts.json --epoch 1 --outdir index_demo
```

### 6. Stage-by-Stage Processing
```bash
# Run individual stages
afi-econ-kit gauge --receipts examples/receipts.json \
  --config examples/params/gauge_v0.yaml --outdir stage_gauge

afi-econ-kit safety --allocations stage_gauge/gauge_allocations.json \
  --config examples/params/gauge_v0.yaml --outdir stage_safety

afi-econ-kit payouts --allocations stage_safety/safety_allocations.json \
  --pool 1000.0 --outdir stage_payouts
```

## Data Schemas

### receipts.json Format
```json
[
  {
    "participant_id": "user_001",
    "role": "reputation",
    "region": "north_america", 
    "amount": 100.0,
    "timestamp": "2024-01-01T12:00:00Z"
  }
]
```

### payouts.json Format
```json
[
  {
    "participant_id": "user_001",
    "role": "reputation",
    "amount": 250.0,
    "epoch": 1
  }
]
```

### epoch_budget.json Format
```json
{
  "epoch": 208,
  "B_t": 126.19,
  "E_t": 132.05,
  "AIM": {
    "factor": 1.046,
    "adjustment": 5.86
  }
}
```

### scores_min.json Format (BenchKit)
```json
{
  "participants": {
    "user_001": {
      "role": "reputation",
      "total_score": 85.5,
      "benchmark_scores": {
        "latency": 90.0,
        "throughput": 81.0
      }
    }
  },
  "stamp": {
    "version": "0.1.0",
    "utc_ts": "2024-01-01T12:00:00Z"
  }
}
```

## Expected Outputs

### Simulation Outputs
- `econ_summary.json` - Complete economic summary
- `gauge_shares.png` - Allocation visualization
- `safety_smoothing.png` - Safety mechanism plot
- `payout_distribution.png` - Final distribution
- `monte_carlo_stats.json` - Statistical results

### Index Outputs  
- `afi_index.json` - Index computation results
- `afi_index.png` - Index visualization

### Stage Outputs
- `gauge_allocations.json` - Gauge stage results
- `safety_allocations.json` - Safety stage results  
- `final_payouts.json` - Payouts stage results

## Makefile Targets

The repository includes convenient Makefile targets:

```bash
make demo      # Run basic simulation demo
make index     # Run AFI Index computation demo
make golden    # Run golden tests (local mode)
make golden-ci # Run golden tests (CI strict mode)
```

## Integration with Other AFI Repositories

### With afi-emissions
```bash
# Generate budget in afi-emissions
cd ../afi-emissions
afi-emissions emit --config params/emissions_v0.yaml --epoch 208 --out budget_out

# Use budget in afi-econ-kit
cd ../afi-econ-kit  
afi-econ-kit simulate --config config.yaml --outdir integrated_sim \
  --budget ../afi-emissions/budget_out/epoch_budget.json
```

### With afi-benchkit
```bash
# Generate scores in afi-benchkit
cd ../afi-benchkit
afi-benchkit reputation --config config.yaml --out scores_out

# Use scores in afi-econ-kit
cd ../afi-econ-kit
afi-econ-kit simulate --config config.yaml --outdir integrated_sim \
  --scores ../afi-benchkit/scores_out/scores.json
```

## Testing and Validation

All example files are designed to work with the golden test suite:

```bash
# Run tests with example data
pytest tests/test_budget_ingest.py -v
pytest tests/test_index_golden.py -v
pytest tests/test_anti_gaming.py -v
```

The examples demonstrate:
- ✅ Deterministic computation
- ✅ Provenance tracking  
- ✅ Schema validation
- ✅ Error handling
- ✅ Integration patterns
