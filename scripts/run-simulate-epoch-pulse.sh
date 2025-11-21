#!/bin/bash

# Run Epoch Pulse simulation with default config

set -e

echo "Building TypeScript..."
npm run build

echo "Running Epoch Pulse simulation..."
npm run cli simulate-epoch-pulse --config src/configs/defaults/epochPulse.default.json

echo "✅ Simulation complete. Check data/out/ for results."

