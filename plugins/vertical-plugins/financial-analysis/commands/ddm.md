---
description: Build a DDM (Dividend Discount Model) valuation for high-dividend financial stocks
argument-hint: "[company name or ticker]"
---

# DDM Valuation Command

Build an institutional-quality DDM (Dividend Discount Model) for high-dividend financial stocks
(banks, insurance, financial leasing, brokerages).

## Workflow

### Step 1: Gather Company Information

If a company name or ticker is provided, use it. Otherwise ask:
- "What company or ticker would you like to value with DDM?"
- "What sector? (Bank / Insurance / Financial Leasing / Brokerage)"

### Step 2: Load DDM Model Skill

Use `skill: "ddm-model"` to construct the valuation:

1. **Fetch data** — historical DPS, EPS, ROE, payout ratio, current price, beta, 10Y treasury yield
2. **Historical analysis** — 5-year DPS CAGR, payout ratio stability, ROE trends, dividend yield
3. **CAPM cost of equity** — Rf + Beta × ERP, calibrated for China A-share market
4. **Multi-stage DPS forecast** — 5-year explicit DPS projections + GGM terminal value
5. **Discount & aggregate** — Σ PV(DPS₁₋₅) + PV(Terminal Value) → intrinsic value per share
6. **Sensitivity analysis** — r vs g, EPS growth vs payout, Beta vs Rf (3 tables × 25 cells)

### Step 3: Deliver Output

Provide:
1. **DDM model** (.xlsx) with:
   - Bear/Base/Bull three-scenario analysis
   - 3 sensitivity tables at the bottom
   - CAPM sheet with g < r validation
   - Blue = inputs, Black = formulas, Green = sheet links
2. **Summary** explaining:
   - Historical dividend analysis and key trends
   - Scenario assumptions and rationale
   - Implied upside/downside vs current price
   - Key risks and sensitivities

## Sector Parameter Ranges

| Sector | Payout Ratio | Typical r | Typical Beta |
|--------|-------------|-----------|--------------|
| Large State-Owned Banks | 25-35% | 7-9% | 0.5-0.8 |
| Joint-Stock / City Comm. Banks | 25-35% | 9-11% | 0.7-1.0 |
| Insurance | 25-40% | 9-12% | 0.8-1.2 |
| Financial Leasing | 30-50% | 9-13% | 0.8-1.1 |
| Brokerages | 25-45% | 10-13% | 1.0-1.3 |

## Quality Checklist

Before delivery:
- [ ] `recalc.py` run until status "success" (zero formula errors)
- [ ] All hardcoded inputs have cell comments with source, date, reference
- [ ] DPS growth ≤ EPS growth in all forecast years
- [ ] g_terminal < r validated on CAPM sheet
- [ ] Terminal value 50-75% of equity value
- [ ] Payout ratio within 20-70% (financial sector reasonable range)
- [ ] Implied P/B within ±30% of industry average
- [ ] All 75 sensitivity formulas populated (not placeholders)
- [ ] File named: `[Ticker]_DDM_Model_[Date].xlsx`