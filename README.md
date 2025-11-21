# afi-econ-kit

**Economic Modeling & Simulation Toolkit for AFI Protocol**

`afi-econ-kit` (nickname: **afi-econ**) is the research and tooling repository for economic modeling, simulation, and scenario analysis for the AFI Protocol. This kit enables deterministic, config-driven experiments for token emissions, validator rewards, signal economics, and governance rhythms.

---

## ⚠️ Status: Research-Grade / Placeholder Models

**Current State (v0.1.0)**:
- ✅ **Deterministic simulation framework** - Seeded RNG, config-driven, reproducible outputs
- ✅ **TypeScript + Python dual stack** - CLI tools and Jupyter notebooks
- ⚠️ **Economic models are PLACEHOLDER / toy implementations** - Simple formulas for experimentation only
- ⚠️ **Not protocol-canonical yet** - Models use sinusoidal pulses, linear curves, random data
- 🔜 **Future work**: Integration with afi-math for real decay curves, time-value calculations, and production-grade formulas

**Use this toolkit for**:
- Exploring economic scenarios and parameter sensitivity
- Prototyping new economic mechanisms
- Generating reproducible simulation data for research

**Do NOT use for**:
- Production parameter decisions (models are placeholders)
- Whitepaper claims (formulas are not final)
- Smart contract configuration (wait for afi-math integration)

**Visibility & Roadmap**:
- Repository is currently **private** until canonical formulas are implemented
- Canonical formulas will be added after Factory.ai droid pass + afi-math integration
- Will transition to public once models are protocol-canonical

See individual model files for detailed PLACEHOLDER warnings and TODOs.

---

## Purpose

This repository provides:

- **Token Emissions & Minting Simulations**: PoI/PoInsight-driven minting, signal-based minting, supply curves
- **Validator/Agent Reward & Reputation Simulations**: Reward distribution, reputation decay, staking mechanics
- **Epoch Pulse Modeling**: Governance and emissions rhythm scenario modeling (the heartbeat of AFI)
- **Signal Economy Simulations**: Signal valuation, decay, and lifecycle economics
- **Deterministic Replayable Sims**: Seeded RNG for audits, regression testing, and reproducibility
- **Config-Driven Experiments**: JSON-based configuration for rapid iteration
- **Chart-Ready Outputs**: JSON/CSV exports designed to feed AFI Whitepaper charts and Notion summaries

---
- **Chart-Ready Outputs**: JSON/CSV exports designed to feed AFI Whitepaper charts and Notion summaries

---

## Relationship to Other AFI Repos

| Repo | Purpose | Relationship to afi-econ-kit |
|------|---------|------------------------------|
| **afi-token-finalized** | Smart contracts (AFIToken, emissions, governance) | afi-econ models inform contract parameters |
| **afi-core** | Protocol interfaces, signal lifecycle, validators | afi-econ simulates economic outcomes of core logic |
| **afi-engine** | Signal processing engine (ElizaOS integration) | afi-econ models signal flow economics |
| **afi-math** | Pure mathematical functions (curves, decay, valuation) | afi-econ uses afi-math for calculations |

**afi-econ-kit does NOT duplicate**:
- Core protocol logic (lives in afi-core)
- Smart contract implementation (lives in afi-token-finalized)
- Signal processing (lives in afi-engine)

**afi-econ-kit DOES provide**:
- Economic scenario modeling
- Parameter sensitivity analysis
- Long-term simulation and forecasting
- Research tooling for whitepaper and governance decisions

---

## Quickstart

### TypeScript CLI

```bash
# Install dependencies
yarn install

# Build TypeScript
yarn build

# Run simulations
yarn cli simulate-epoch-pulse --config configs/defaults/epochPulse.default.json
yarn cli simulate-minting --config configs/defaults/minting.default.json
yarn cli simulate-validator-rewards --config configs/defaults/rewards.default.json
yarn cli simulate-signal-economy --config configs/defaults/signalEconomy.default.json

# Development mode (auto-rebuild)
yarn dev
```

### Python Notebooks

```bash
# Create virtual environment
cd python
python3 -m venv venv
source venv/bin/activate

# Install dependencies (when added)
pip install -r requirements.txt

# Launch Jupyter
jupyter notebook notebooks/
```

---

## Experiment Philosophy

### 1. Deterministic by Default
- All simulations use **seeded RNG** for reproducibility
- Same config + same seed = same output (always)
- Critical for audits, regression testing, and collaborative research

### 2. Config-Driven
- Every simulation reads from JSON config files
- Configs define: seed, epoch range, parameters, output format
- Easy to version control experiments and share scenarios

### 3. Outputs as JSON/CSV for Charts
- All simulation outputs are structured data (JSON/CSV)
- Designed to be imported into charting tools, spreadsheets, or Notion
- Supports AFI Whitepaper visualization and governance reporting

### 4. Minimal Dependencies
- Lightweight TypeScript + Python stack
- No heavy ML frameworks or bloated dependencies
- Fast iteration, easy to run on Factory.ai droids

---

## Roadmap / TODO

- [ ] Implement Epoch Pulse emissions model (time-based minting rhythm)
- [ ] Implement PoI-driven minting model (signal quality → token supply)
- [ ] Implement validator reward distribution model
- [ ] Implement agent reputation decay model
- [ ] Implement signal economy lifecycle model (creation → decay → finalization)
- [ ] Add Python equivalents of TypeScript models for notebook experimentation
- [ ] Add sensitivity analysis utilities (parameter sweeps)
- [ ] Add visualization helpers (chart generation from outputs)
- [ ] Add regression test suite (golden outputs for known configs)
- [ ] Integrate with afi-math for curve calculations
- [ ] Add multi-epoch simulation runner (long-term forecasting)
- [ ] Add governance scenario modeling (proposal → vote → execution)

---

## File Structure

```
afi-econ-kit/
├── src/                          # TypeScript source
│   ├── cli/                      # CLI entrypoint and commands
│   ├── models/                   # Economic models (emissions, minting, rewards)
│   ├── configs/                  # Config schemas and defaults
│   └── utils/                    # RNG, math, logging utilities
├── python/                       # Python notebooks and sims
│   ├── notebooks/                # Jupyter notebooks for experimentation
│   └── sims/                     # Python equivalents of TS models
├── data/                         # Sample data and simulation outputs
│   ├── sample/                   # Sample input data
│   └── out/                      # Simulation outputs (gitignored)
└── scripts/                      # Shell scripts for common workflows
```

---

## Contributing

This is a research/tooling repo. Contributions should:
- Maintain deterministic behavior (seeded RNG)
- Follow config-driven patterns
- Include clear TODOs for unimplemented logic
- Avoid duplicating logic from other AFI repos

---

## License

MIT

