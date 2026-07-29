# AFI Alpha-Source Candidates Harvest v0.1

**Register:** NON-CANONICAL research input (per `afi-governance/decisions/math-authority-v0.1` §3 register discipline). This document **decides nothing**: no source is selected, onboarded, licensed, or governed by appearing here; source selection and provider onboarding are undecided future work. Preserved 2026-07-28, restated in current-architecture terms from the pre-alpha "GoldDigger" source-mining manifest (Sept 2025, owner-authored research), so the original artifact could be deleted forward-only.

**Purpose (owner-stated):** an initial base of external signal sources AFI could mine early — for pipeline testing and as bootstrap alpha inputs. The natural consumers are the **AFI Participant Gateway v0.1** mission (provider onboarding + ingestion testing) and Factory strategy work.

**How candidates map to current architecture:** an external source enters AFI either as an **origin provider** (webhook → CPJ, per the merged TradingView/MarkitTick precedent) or as **lane-relevant enrichment input** under the governed five-lane provider registry (aiMl, news, pattern, sentiment, technical) / USS lens families (incl. onchain, macro). The "lane affinity" column below is best-effort research guidance, not a binding mapping.

**Staleness warning:** access modes, free tiers, rate limits, and license terms are **as-of Sept 2025** and must be re-verified against each vendor at onboarding time. Quality proxies in the original were rough estimates (most win-rates null); treat all of them as unvalidated.

## Candidate roster (24)

| # | Source | Category | Lane/lens affinity | Semantics | Access (Sept-2025) | License posture | Dup-risk | Status | Ingestion sketch |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Token Metrics AI Signals | AI signals platform | aiMl | buy/sell, bullish/bearish | API, key optional | commercial OK, attribution | low | ready | Poll trading-signals hourly/daily; map bullish→buy |
| 2 | Trading Economics Calendar | Macro events | news/macro | event alerts | API, key | commercial OK, attribution | low | ready | Trigger on surprise vs consensus; map to affected markets |
| 3 | DexScreener New Pairs | On-chain DEX listings | onchain lens | new-listing alerts | API, no auth | public API | low | ready | Watch new pairs per chain; filter by liquidity/volume |
| 4 | Whale Alert | On-chain whale transfers | onchain lens | whale txn alerts | API, key (free ≥$500k txns) | commercial OK, attribution | low | ready | Only act on known exchange inflow/outflow addresses |
| 5 | Alternative.me Fear & Greed | Sentiment index | sentiment | contrarian buy/sell | API, no auth | CC0 | low | ready | <20 → contrarian buy; >80 → contrarian sell |
| 6 | Finnhub Technical Signals | TA aggregate | technical | buy/sell/neutral | API, key (60/min free) | commercial OK, attribution | medium | ready | Use aggregate signal per symbol/timeframe + price filter |
| 7 | Intelligent Trading Bot (asavinov) | ML bot (crypto) | aiMl | buy/sell/exit | self-host (MIT) | MIT | low | requires_work | Run in simulation; watch model drift |
| 8 | TradingView Open Strategies | Community TA strategies | technical | long/short/exit | webhook (alerts) | MPL-2.0 scripts | **high** | requires_work | Pick ~10 top strategies; alerts→webhook (fits existing TV origin) |
| 9 | Freqtrade Community Strategies | OSS bot strategies | technical | buy/sell | self-host | MIT/GPL mixed | medium | requires_work | Webhook callback on signal generation |
| 10 | ElizaOS Spartan Agent | AI DeFi agent (Solana) | aiMl | buy/sell/yield | self-host (MIT) | MIT | low | requires_work | External tool only (ElizaOS is retired as AFI architecture); treat planned trades as signals |
| 11 | CryptoSignal CLI | TA rules multi-coin | technical | indicator alerts | self-host | MIT | medium | requires_work | Configure distinct indicators to avoid overlap |
| 12 | OctoBot Strategies | OSS bot | technical | buy/sell | self-host | GPL-3.0 (internal OK) | medium | requires_work | Ensure non-duplicate vs Freqtrade set |
| 13 | LunarCrush AltRank/GalaxyScore | Social momentum | sentiment | bull/bear scores | API, key (free tier tight) | attribution ("powered by") | low | ready | Galaxy ≥75 → buy; extreme+declining → sell |
| 14 | CoinMarketCal Events | Crypto events calendar | news | event buy/alert | API, no auth | free with mention | low | ready | e.g. tech upgrade → buy 7d prior |
| 15 | Myfxbook Community Outlook | Retail FX sentiment | sentiment | contrarian | API/scrape, key | aggregated user data | medium | requires_work | Fade >75% crowd positioning, require persistence |
| 16 | Tickeron AI Signals | AI pattern alerts | aiMl/pattern | buy/sell/pattern | paid API | **proprietary — permission needed** | low | requires_work | Supplemental only due to license |
| 17 | CFTC Commitment of Traders | Institutional positioning | macro | positioning extremes | weekly file, no auth | US-gov public domain | low | ready | Net-position percentiles; fade spec extremes |
| 18 | IG Client Sentiment | Retail sentiment | sentiment | contrarian | scrape/feed | public info | medium | requires_work | Fade >80% extremes; dedupe vs Myfxbook by asset coverage |
| 19 | FRED Macro Indicators | Economic series | macro | regime risk-on/off | API, key (120/min) | public domain | low | ready | Rules on T10Y2Y, VIX, PMI → regime signals |
| 20 | AAII Investor Sentiment | Investor survey | sentiment | contrarian extremes | scrape (weekly Thu) | free public | low | ready | Bull−Bear spread >+30 → sell; <−30 → buy |
| 21 | Google Trends | Search interest | sentiment | hype top / panic bottom | unofficial API | limited reuse — internal only | medium | requires_work | 5y-high "Bitcoin" query → contrarian sell |
| 22 | Santiment (free tier) | On-chain + social analytics | onchain/sentiment | composite divergences | GraphQL, key (tight limits) | attribution | low | ready | e.g. price↓ + devActivity↑ → buy |
| 23 | CoinGecko Trending | Retail trending coins | sentiment | momentum/overhype | API, no auth | attribution in app | low | ready | New trending → short-term buy; multi-day extreme → sell |
| 24 | OpenInsider (SEC filings) | Insider trades | news | insider buy/sell | scrape | public domain | low | requires_work | Large exec purchases (>$100k) → buy w/ note |
| — | CME FedWatch | Rate expectations | macro | cut/hike probabilities | scrape/derive | derived market data | low | requires_work | >50% cut prob → long bonds; distribution shifts → vol signal |

*(25 rows: the original manifest held 24 entries plus FedWatch listed without a number.)*

## Research notes carried forward

- **Duplication control was a design concern**: community TA sources (TradingView scripts, Freqtrade, CryptoSignal, OctoBot, Finnhub) overlap heavily — the manifest deliberately flags dup-risk and instructs choosing distinct indicators/strategies per source.
- **License diligence is half the value**: per-source commercial-reuse and attribution flags were researched up front; two entries are restricted (Tickeron proprietary; Google Trends internal-only).
- **Contrarian-extreme rules recur** (F&G, AAII, Myfxbook, IG, Trends): the same fade-the-crowd template with per-source thresholds — a natural early Factory playbook family.
- The original file was concatenated JSON records (not a valid JSON document) with LLM citation artifacts; content is fully restated here.
