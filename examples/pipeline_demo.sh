#!/bin/bash
# AFI Econ Kit Pipeline Demonstration
# Shows complete end-to-end economic pipeline

set -e

echo "🚀 AFI Econ Kit Pipeline Demo"
echo "=============================="

# Clean up any previous runs
rm -rf demo_pipeline_out

# Step 1: Basic simulation
echo ""
echo "📊 Step 1: Basic Economic Simulation"
echo "------------------------------------"
afi-econ-kit simulate --config config.yaml --outdir demo_pipeline_out/basic
echo "✅ Basic simulation complete"

# Step 2: Simulation with budget
echo ""
echo "💰 Step 2: Simulation with Budget Integration"
echo "--------------------------------------------"
afi-econ-kit simulate --config config.yaml --outdir demo_pipeline_out/budget \
  --budget examples/epoch_budget.json
echo "✅ Budget integration complete"

# Step 3: Simulation with merit scores
echo ""
echo "🏆 Step 3: Simulation with Merit Scores"
echo "--------------------------------------"
afi-econ-kit simulate --config config.yaml --outdir demo_pipeline_out/merit \
  --scores tests/fixtures/scores_min.json
echo "✅ Merit integration complete"

# Step 4: Full integration
echo ""
echo "🔗 Step 4: Full Integration (Budget + Merit)"
echo "-------------------------------------------"
afi-econ-kit simulate --config config.yaml --outdir demo_pipeline_out/full \
  --budget examples/epoch_budget.json --scores tests/fixtures/scores_min.json
echo "✅ Full integration complete"

# Step 5: AFI Index computation
echo ""
echo "📈 Step 5: AFI Index Computation"
echo "-------------------------------"
afi-econ-kit index --receipts examples/receipts.json \
  --payouts examples/payouts.json --epoch 208 --outdir demo_pipeline_out/index
echo "✅ AFI Index computation complete"

# Step 6: Stage-by-stage processing
echo ""
echo "⚙️  Step 6: Stage-by-Stage Processing"
echo "------------------------------------"

# Gauge stage
afi-econ-kit gauge --receipts examples/receipts.json \
  --config params/gauge_v0.yaml --outdir demo_pipeline_out/stages/gauge
echo "  ✅ Gauge stage complete"

# Safety stage
afi-econ-kit safety --allocations demo_pipeline_out/stages/gauge/gauge_allocations.json \
  --config params/gauge_v0.yaml --outdir demo_pipeline_out/stages/safety
echo "  ✅ Safety stage complete"

# Payouts stage
afi-econ-kit payouts --allocations demo_pipeline_out/stages/safety/safety_allocations.json \
  --budget examples/epoch_budget.json --outdir demo_pipeline_out/stages/payouts
echo "  ✅ Payouts stage complete"

# Summary
echo ""
echo "📋 Pipeline Demo Summary"
echo "======================="
echo "Generated outputs in demo_pipeline_out/:"
echo ""

find demo_pipeline_out -name "*.json" -o -name "*.png" | sort | while read file; do
    echo "  📄 $file"
done

echo ""
echo "🎉 Pipeline demo complete!"
echo ""
echo "Key files to examine:"
echo "  • demo_pipeline_out/full/econ_summary.json - Complete economic summary"
echo "  • demo_pipeline_out/full/gauge_shares.png - Allocation visualization"
echo "  • demo_pipeline_out/index/afi_index.json - AFI Index results"
echo "  • demo_pipeline_out/index/afi_index.png - Index visualization"
echo ""
echo "To clean up: rm -rf demo_pipeline_out"
