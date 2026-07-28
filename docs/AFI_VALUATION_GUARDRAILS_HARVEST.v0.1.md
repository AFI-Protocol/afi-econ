# AFI Valuation Guardrails Harvest v0.1

**Register:** NON-CANONICAL research input (per `afi-governance/decisions/math-authority-v0.1` §3: afi-econ content is non-canonical unless a formula is formally promoted). This document **decides nothing** and self-labels nothing canonical. It preserves, in current-architecture terms, the reverse-DCF production-discipline guardrail set from the pre-alpha whitepaper-era valuation research (Sept 2025 outbound memo + exhibits), so the original artifacts could be deleted forward-only (2026-07-28).

**Why harvested:** the governed USS signal contract defines the `terminalDiscipline` block and related fields (`afi-config/schemas/usignal/v1/core.schema.json:222-243` — `gStable`, `roiicIntangible`, `salesToCapital`, `halfLifeDays`, `capacityConstraints`; equity lens `scenarios`) but **no current register gives those fields weighting or lint semantics** — the only implementation that ever did (`afi-config/afi-uss-pr-v2p1/server/validateAndWeight.ts:54`, the nominal-GDP guardrail) lives in the stale staged residue copy already ruled for deletion on the owner cleanup backlog. This harvest is the design input for the two undecided consumers: (a) a future **USS lens-weighting / valuation-lint law**, and (b) candidate extensions to the canonical `afi-math` `reverseDcf` kernel.

**Doctrine framing (already governed — cited, not restated):** lenses are optional, never network-enforced at the schema level, but quality-weighted when present (`afi-config/docs/AFI_CONFIG_OVERVIEW.md:115-119`).

---

## The five-guardrail set

1. **Terminal-growth double bound.** `g_stable < WACC` (already enforced: `afi-math/src/valuation/reverseDcf.ts:82-83`) **and** `g_stable ≤ nominal-GDP proxy` (era default ceiling 0.05; the weighting code scored the discipline bonus when satisfied and flagged "terminal g_stable > nominal GDP guardrail" otherwise). This records the intended semantics of the governed `gStable` / `terminalDiscipline` fields.
2. **TV-dominance smell test.** If `PV(TV) / impliedEV` exceeds ~70–80%, flag and revisit pre-terminal assumptions — a flag, never a hard fail. `reverseDcf` already outputs `pvTerminalValue` and `impliedEV`; the dominance flag is a kernel-extension candidate.
3. **Margin fade path.** Pre-terminal EBIT margin fades linearly from starting to target margin over `fade_years` instead of being held constant (the current kernel takes a single constant margin — `reverseDcf.ts:19`). Kernel-extension candidate.
4. **Intangible maintenance discipline ("no free perpetuity").** Intangible effectiveness decays `E(t) = E₀·e^(−λt)` with half-life `H` (decay kernels already canonical in afi-math); refresh/retrain cadence ≈ `H`; growth funded as `g ≈ reinvestment_rate × ROIIC`; terminal FCF must embed ongoing maintenance cost. Binds the governed `roiicIntangible` / `halfLifeDays` fields.
5. **Capacity gates + scar scenario.** Bound period growth by real capacity limits (salesforce, compute/QPS, market depth) using the logistic capacity curve (canonical in `afi-math/src/curves/curves.ts`), and require at least one adverse "scar" scenario (higher rates, lower margins, slower adoption). Binds the governed `capacityConstraints` and equity-lens `scenarios` fields.

Items 1–2 are standard expectation-investing heuristics; they are recorded here only as part of the coherent set that binds the governed schema fields into a future weighting/lint law, not as novel mechanisms.
