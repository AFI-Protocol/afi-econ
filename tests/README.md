# AFI Econ Kit - Testing Strategy

## Overview

This directory contains tests for the afi-econ-kit economic simulation toolkit.

## Testing Philosophy

### 1. **Golden Output Tests** (Regression Testing)

Golden output tests ensure that simulation results remain consistent across code changes.
They work by:

1. Running a simulation with a **fixed seed** and **fixed config**
2. Comparing the output to a **golden reference file**
3. Failing if the output differs (indicating a regression)

**Why Golden Tests?**
- Economic models are complex and hard to unit test
- Deterministic simulations (seeded RNG) produce reproducible outputs
- Golden tests catch unintended changes to economic formulas
- Easy to review changes: just diff the golden files

### 2. **Property-Based Tests**

Test invariants that should always hold:
- Cumulative supply should be monotonically increasing
- Emissions should never be negative
- Reputation scores should stay within [0, 100]
- Reward distribution should sum to reward pool

### 3. **Smoke Tests**

Quick sanity checks:
- CLI commands run without errors
- Simulations produce valid JSON/CSV output
- Config validation works correctly

## Golden Output Test Structure

```
tests/
├── golden/                    # Golden reference outputs
│   ├── epoch-pulse.golden.json
│   ├── minting.golden.json
│   ├── rewards.golden.json
│   └── signal-economy.golden.json
├── configs/                   # Test configs (fixed seeds)
│   ├── epoch-pulse.test.json
│   ├── minting.test.json
│   └── ...
└── test_golden_outputs.py     # Golden test runner
```

## Running Tests

### Python Tests (Existing)

```bash
# Run all Python tests
pytest

# Run specific test file
pytest tests/test_emissions.py

# Run with coverage
pytest --cov=src/afi_econ_kit
```

### TypeScript Golden Tests (TODO)

```bash
# Generate golden outputs (first time)
npm run test:golden:generate

# Run golden tests (compare to reference)
npm run test:golden

# Update golden outputs (after intentional changes)
npm run test:golden:update
```

## Creating New Golden Tests

1. **Create a test config** with a fixed seed:
   ```json
   {
     "seed": 42,
     "startEpoch": 0,
     "endEpoch": 10,
     "params": { ... }
   }
   ```

2. **Run the simulation** and save output:
   ```bash
   npm run cli simulate-epoch-pulse --config tests/configs/epoch-pulse.test.json > tests/golden/epoch-pulse.golden.json
   ```

3. **Write a test** that compares future runs to the golden file

4. **Commit the golden file** to version control

## Updating Golden Files

When you **intentionally** change economic formulas:

1. Review the changes carefully
2. Run `npm run test:golden:update` to regenerate golden files
3. Review the diff in git to ensure changes are expected
4. Commit the updated golden files with a clear message

## TODO

- [ ] Add TypeScript test framework (Vitest or Jest)
- [ ] Implement golden output test runner
- [ ] Create golden reference files for all models
- [ ] Add property-based tests for invariants
- [ ] Add CLI smoke tests
- [ ] Add config validation tests
- [ ] Set up CI/CD to run tests on every commit

## Notes

- **Always use fixed seeds** in test configs for reproducibility
- **Never modify golden files manually** - regenerate them with the test runner
- **Review golden file diffs carefully** before committing changes
- **Document breaking changes** in commit messages when updating golden files
