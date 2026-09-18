# Antigravity QuantEngine — Quantitative Research & Feature Engineering

## 1. Research Subsystem Principles

- **Dataset Isolation**: Certified historical research datasets are immutable. Real-time paper trading never mutates historical datasets. Synthetic test fixtures are strictly quarantined in `tests/fixtures/synthetic/` and never enter research or dashboards.
- **D3 Sealed Data Firewall**: Datasets marked `is_sealed = 1` enforce:
  `D3_READ = 0`, `D3_LOAD = 0`, `D3_HASH = 0`. Any unauthorized read attempt raises `SealedDatasetAccessViolation` and is logged to the audit engine.
- **Causal Feature Engineering**: All indicators (rolling means, standard deviations, volume deltas, regime classifications) are computed strictly from information available up to bar $t$.

## 2. Statistical Validation Methods

- **Bootstrap Confidence Intervals**: 95% bootstrap intervals for win rate and mean trade P&L (1,000 resamples).
- **Monte Carlo Reshuffling**: Permuting historical trade returns to assess path-dependent sequence risk, 95th percentile worst-case drawdown, and ruin probability.
- **Multiple Testing Corrections**:
  - `Bonferroni`: $\alpha_{adj} = \alpha / M$
  - `Holm-Bonferroni`: Step-down sequential FWER control.
  - `Benjamini-Hochberg`: False Discovery Rate (FDR) control.
