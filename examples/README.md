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
- `merit_scores.synthetic.json` - Synthetic merit scores for the `--scores` path (see "Merit scores (synthetic)" below)

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

### 3. Simulation with Merit Scores (synthetic)
```bash
# Run simulation with the synthetic merit scores
afi-econ-kit simulate --config examples/config.yaml --outdir merit_sim \
  --scores examples/merit_scores.synthetic.json
```

### 4. Full Integration (Budget + Merit)
```bash
# Run simulation with both budget and merit scores
afi-econ-kit simulate --config examples/config.yaml --outdir full_sim \
  --budget examples/epoch_budget.json --scores examples/merit_scores.synthetic.json
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

### merit_scores.synthetic.json Format (merit scores, synthetic)
```json
{
  "reputation": {"score": 0.58},
  "poi": {"score": 0.55},
  "poinsight": {"score": 0.60},
  "n": 20,
  "stamp": {
    "source": "synthetic",
    "version": "0.1.0",
    "utc_ts": "2026-08-24T00:00:00Z"
  }
}
```

`reputation.score` is required; `poi.score` and `poinsight.score` default to 0.5 when
absent. Scores are clipped to [0, 1]. `n` is the row count behind the scores and `stamp`
is passed through unchanged into the simulation's provenance stamp (as `merit_stamp`).
These are synthetic research inputs -- see "Merit scores (synthetic)" below for what
they are and are not.

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

### Merit scores (synthetic)

The `--scores` merit path takes a **synthetic** merit-scores file:

```bash
afi-econ-kit simulate --config config.yaml --outdir integrated_sim \
  --scores examples/merit_scores.synthetic.json
```

These scores are research-plane inputs only. The protocol source of analyst merit is
the CAL-GOV analyst calibration record (`afi.analyst-calibration.v1`) -- **not a
scalar** -- and any conversion of it into a merit value is **CHAIN-GOV reserved**.
afi-econ consumes no such value from the protocol; edit the synthetic file to explore
how merit multipliers move gauge allocations. Proof-of-Intelligence (PoI) and
Proof-of-Insight (PoInsight) remain reserved protocol reputation primitives
(CONST-GOV D-CONST-5; CAL-GOV D-CAL-5); the `poi` / `poinsight` keys here are
synthetic placeholders that stand in for no protocol value.

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
