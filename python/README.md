# Python Economic Simulations

> **AFI Settlement v1 note:** Parts of this document reference the **v0** per-signal mint / ERC-1155 receipt / direct-beneficiary path, which is **superseded as mainnet architecture** by AFI Settlement v1 — rewards settle **by epoch** through a RewardsVault / Merkle-claim layer funded from an EpochSettlementManifest, strategy/epoch receipts use **ERC-6909** (not ERC-1155), provenance is separated from payout, and ENS names are aliases (concrete addresses + chainId are the source of truth). See `afi-docs/specs/AFI_SETTLEMENT_V1_DOCTRINE.md` for the canonical architecture.

This directory contains Python notebooks and simulation modules for economic experimentation.

## Setup

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows

# Install dependencies (when requirements.txt is added)
pip install -r requirements.txt
```

## Jupyter Notebooks

The `notebooks/` directory contains Jupyter notebooks for interactive experimentation:

- `epoch_pulse_sandbox.ipynb` - Epoch Pulse emissions modeling
- `minting_sandbox.ipynb` - Token minting simulations
- `rewards_sandbox.ipynb` - Validator/agent reward modeling

To launch Jupyter:

```bash
jupyter notebook notebooks/
```

## Python Simulation Modules

The `sims/` directory contains Python equivalents of the TypeScript models in `src/models/`.

These modules mirror the TS logic and can be used in notebooks or standalone scripts.

## Philosophy

- Python notebooks are for **experimentation and visualization**
- TypeScript models in `src/` are the **canonical implementations**
- Keep Python and TS models in sync when possible
- Use notebooks to prototype, then port to TS for production use

## TODO

- [ ] Add requirements.txt with dependencies (numpy, pandas, matplotlib, jupyter)
- [ ] Implement Python equivalents of TS models
- [ ] Add visualization helpers (matplotlib/plotly)
- [ ] Add example notebooks with charts

