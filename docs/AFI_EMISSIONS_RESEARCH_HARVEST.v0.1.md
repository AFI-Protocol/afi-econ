# AFI Emissions Research Harvest v0.1

**Register:** NON-CANONICAL research input (per `afi-governance/decisions/math-authority-v0.1` §3: afi-econ content is non-canonical unless a formula is formally promoted). This document **decides nothing**, self-labels nothing canonical, and authorizes no implementation. Every mechanism named here that touches mint, rewards, settlement, or economic activation is **reserved to the unfiled CHAIN-GOV governance domain**. Its purpose is to preserve the forward-facing design inputs from the pre-alpha emissions research corpus ("Emissions Article", Sept–Oct 2025) in current-architecture terms, so that the original artifacts could be deleted forward-only (2026-07-28). BT-86b (`mint-formula-bt-86b-alignment-v0.1`, accepted) cites this research's whitepaper doctrine (*"AFI: An Agentic Financial Intelligence Market"* §9.4/§9.5/§9.7); this harvest is the surviving in-org record of the parts of that research not already governed or implemented.

What is already covered elsewhere and deliberately NOT restated here: the three-phase 86B emissions schedule (canonical implementation: `afi-math` `src/emissions/emissionsSchedule.ts`, pinned as production B(t) by BT-86b D1); the epoch-budget → role-pools → pro-rata-verified-credits skeleton (BT-86b D3); the AFI Index and AIM simulation mechanics (implemented in this repo's `afi_econ_kit`: `index.py`, `emissions.py`).

---

## 1. Launch stance (as designed in the research; consistent with BT-86b)

Emissions follow the published baseline schedule B(t). The AFI Index is computed and published each epoch as a KPI but **does not modulate issuance at launch** (AIM_t ≡ 1 — matching BT-86b D6). The adaptive layer below is optional, bounded, and OFF until a governance activation decision.

## 2. Adaptive Issuance Multiplier (AIM) — designed form

Per-epoch issuance: `E_t = B(t) · AIM_t`, with AIM within published floor/ceiling.

- Smoothed impact signal (EMA): `Ī_t = (1−λ)·Ī_{t−1} + λ·I_t`, where I_t is the AFI Index.
- Coupling (clipped affine): `AIM_t = clip(1 + κ·(Ī_t − I*), minMult, maxMult)`.
- Per-epoch rate limit: `|AIM_t − AIM_{t−1}| ≤ δ_max`.
- Monthly budget guardrail bounding deviation from baseline: ≤ B_max.
- Circuit breakers pause adaptation / revert AIM_t to 1 on safety breaches (e.g., excessive reversions); parameters are public, versioned, and change only at epoch boundaries. Setting AIM_t ≡ 1 recovers the policy-constant path.

Stability layer generalized to allocation as well: `|E_t − E_{t−1}| ≤ Δ_E` and per-role gauge movement `|g_r(t) − g_r(t−1)| ≤ Δ_G`; role caps/guards ensure no role can absorb the entire flow in one epoch.

AFI Index component chain (implemented in `afi_econ_kit`): `AN_t` (active network), `EG_t` (economic growth), `Cov_t` (coverage) → `I_t` → `Ī_t` → AIM.

## 3. AIM activation criteria (readiness checklist — future CHAIN-GOV input)

All must hold before the closed loop is engaged:

1. **Data sufficiency & diversity** — ≥ K finalized evidence records spanning multiple venues/instruments (K set by governance; order tens of thousands); demonstrated multi-regime coverage (quiet / volatile / eventful, by volatility & volume quantiles).
2. **Measurement stability** — rolling 26–52-epoch drift of Index component weights < Δ_weights_max (e.g., 5–10%); out-of-sample error for attribution/efficiency components below E_oos_max on k-fold backtests; dispute/reversion rate < r_dispute_max (e.g., 1%) for N consecutive epochs.
3. **Integrity & observability** — attribution/watermarking coverage > p_tag_min; no unresolved governed-contract/schema migrations affecting Index inputs; open per-epoch CSVs publishing components, Ī_t, applied AIM, and parameter versions.
4. **Safety simulation** — re-run ≥30k Monte-Carlo with the proposed (κ, minMult, maxMult, λ) and confirm monthly minted-vs-baseline deviation ≤ B_max (e.g., 5%) and that rate-limit/circuit-breaker thresholds are never breached in stress paths.
5. **Governance & rollout** — pre-approve (κ, minMult, maxMult, λ, δ_max) and change windows; run a dry-run window publishing computed-but-unapplied AIM for M epochs; on activation publish test vectors and backtests; subsequent changes require notice and bounds.

**Timing recommendation:** enable coupling only after the 4-year bootstrap phase (~33⅓% minted), during the 33%→80% growth window — by then receipts span regimes, reducing over-reaction to sparse early data. Keep κ small, enforce floors/ceilings, cap per-epoch deltas.

## 4. Candidate parameters and Monte-Carlo safety evidence (research values — ungoverned)

Whitepaper simulation runs (cap 86e9, 52 epochs/yr, milestones y33=4 / y80=28 / y100=54):

- Open-loop multiplier: α=0.08, minMult=0.85, maxMult=1.5, afiScale=1.0.
- Closed-loop extras: ceBeta=0.15, ceKappa=0.2, ceMin=0.9, ceMax=1.3.
- Scenario families explored (Python model): conservative (α=0.08, k=0.90, mult∈[0.80,1.50]), nominal (α=0.10, k=0.90, mult∈[0.40,2.00]), aggressive (α=0.15, k=0.60, mult∈[0.50,2.50]).

30,000-scenario Monte-Carlo outcomes (milestone years, cumulative share):

| Milestone | p5 | p50 | p95 |
|---|---|---|---|
| 33⅓% | 4 | 4 | 5 |
| 80% | 27 | 28 | 29 |
| 100% | 49 | 54 | 54 |

Average multiplier across scenarios: mean 1.0132, p5 0.9994, p95 1.0451 — i.e., the bounded adaptive layer barely perturbs the milestone structure. This is the empirical safety basis a future AIM-parameter decision can cite or re-run.

## 5. Reputation → economics rule (eligibility vs realized share)

As stated in the whitepaper economic model, aligned with D-CONST-5 and the afi-core invariants:

> **PoI** (capability on pinned, deterministic suites) **governs eligibility**; **PoInsight** (live, receipt-verified contribution) **governs realized share**. Reputation decays without recent verified work. **Neither overrides UWR scoring or finality.**

All PoI/PoInsight formulas, weightings, and economic conversion remain reserved (CHAIN-GOV / future reputation decision); this records the designed *shape* of the linkage only.

## 6. Schedule-tail discrepancy requiring an eventual owner ruling

The research corpus and all whitepaper simulation runs target **100% of cap at year 54** (phases 4/24/26). The governed `afi-math` schedule pinned by BT-86b D1 reaches 100% at **~year 53** (phases 4/24/25). BT-86b records the pin as made "without amending whitepaper doctrine," and the one-year tail difference is documented nowhere else. Resolution (bless ~53 explicitly, or amend to 54) belongs to the eventual CHAIN-GOV schedule ratification; it has no effect on the cap, the milestones through year 28, or any current behavior.
