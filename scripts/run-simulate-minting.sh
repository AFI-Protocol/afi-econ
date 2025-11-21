#!/bin/bash

# Run PoI Minting simulation with default config

set -e

echo "Building TypeScript..."
npm run build

echo "Running PoI Minting simulation..."
npm run cli simulate-minting --config src/configs/defaults/minting.default.json

echo "✅ Simulation complete. Check data/out/ for results."

