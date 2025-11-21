#!/bin/bash
# AFI Econ Kit Stage-by-Stage Processing Demo
# Shows individual pipeline stages in detail

set -e

echo "⚙️  AFI Econ Kit Stage-by-Stage Demo"
echo "==================================="

# Clean up any previous runs
rm -rf stage_demo_out

echo ""
echo "This demo shows how to run individual pipeline stages:"
echo "  1. Gauge: Policy + Merit → Allocations"
echo "  2. Safety: Smoothing + Caps → Safe Allocations"  
echo "  3. Payouts: Budget → Final Payouts"
echo ""

# Stage 1: Gauge Allocation
echo "📊 Stage 1: Gauge Allocation"
echo "----------------------------"
echo "Input: receipts.json + optional scores.json"
echo "Output: gauge_allocations.json"
echo ""

afi-econ-kit gauge --receipts examples/receipts.json \
  --config params/gauge_v0.yaml --outdir stage_demo_out/gauge

echo "✅ Gauge stage complete"
echo ""

# Show gauge results
if [ -f "stage_demo_out/gauge/gauge_allocations.json" ]; then
    echo "Gauge allocations preview:"
    python3 -c "
import json
with open('stage_demo_out/gauge/gauge_allocations.json', 'r') as f:
    data = json.load(f)
    allocations = data.get('allocations', {})
    print(f'  Participants: {len(allocations)}')
    if allocations:
        total = sum(allocations.values())
        print(f'  Total allocation: {total:.3f}')
        print('  Top 3 allocations:')
        sorted_allocs = sorted(allocations.items(), key=lambda x: x[1], reverse=True)[:3]
        for participant, alloc in sorted_allocs:
            print(f'    {participant}: {alloc:.3f}')
"
fi

echo ""

# Stage 2: Safety Smoothing
echo "🛡️  Stage 2: Safety Smoothing"
echo "-----------------------------"
echo "Input: gauge_allocations.json + optional prev_allocations.json"
echo "Output: safety_allocations.json"
echo ""

afi-econ-kit safety --allocations stage_demo_out/gauge/gauge_allocations.json \
  --config params/gauge_v0.yaml --outdir stage_demo_out/safety

echo "✅ Safety stage complete"
echo ""

# Show safety results
if [ -f "stage_demo_out/safety/safety_allocations.json" ]; then
    echo "Safety allocations preview:"
    python3 -c "
import json
with open('stage_demo_out/safety/safety_allocations.json', 'r') as f:
    data = json.load(f)
    allocations = data.get('smoothed_allocations', {})
    print(f'  Participants: {len(allocations)}')
    if allocations:
        total = sum(allocations.values())
        print(f'  Total allocation: {total:.3f}')
        print('  Top 3 allocations:')
        sorted_allocs = sorted(allocations.items(), key=lambda x: x[1], reverse=True)[:3]
        for participant, alloc in sorted_allocs:
            print(f'    {participant}: {alloc:.3f}')
"
fi

echo ""

# Stage 3: Final Payouts
echo "💰 Stage 3: Final Payouts"
echo "-------------------------"
echo "Input: safety_allocations.json + budget.json"
echo "Output: final_payouts.json"
echo ""

afi-econ-kit payouts --allocations stage_demo_out/safety/safety_allocations.json \
  --budget examples/epoch_budget.json --outdir stage_demo_out/payouts

echo "✅ Payouts stage complete"
echo ""

# Show payout results
if [ -f "stage_demo_out/payouts/final_payouts.json" ]; then
    echo "Final payouts preview:"
    python3 -c "
import json
with open('stage_demo_out/payouts/final_payouts.json', 'r') as f:
    data = json.load(f)
    payouts = data.get('payouts', [])
    total_distributed = data.get('total_distributed', 0)
    print(f'  Participants: {len(payouts)}')
    print(f'  Total distributed: {total_distributed:.2f}')
    if payouts:
        print('  Top 3 payouts:')
        sorted_payouts = sorted(payouts, key=lambda x: x['amount'], reverse=True)[:3]
        for payout in sorted_payouts:
            print(f'    {payout[\"participant_id\"]}: {payout[\"amount\"]:.2f}')
"
fi

echo ""

# Summary
echo "📋 Stage-by-Stage Demo Summary"
echo "=============================="
echo "Pipeline stages completed:"
echo "  1. ✅ Gauge: Policy + Merit → Allocations"
echo "  2. ✅ Safety: Smoothing + Caps → Safe Allocations"
echo "  3. ✅ Payouts: Budget → Final Payouts"
echo ""
echo "Generated files:"
find stage_demo_out -name "*.json" | sort | while read file; do
    echo "  📄 $file"
done

echo ""
echo "🎉 Stage-by-stage demo complete!"
echo ""
echo "Compare with full simulation:"
echo "  afi-econ-kit simulate --config config.yaml --outdir comparison \\"
echo "    --budget examples/epoch_budget.json"
echo ""
echo "To clean up: rm -rf stage_demo_out"
