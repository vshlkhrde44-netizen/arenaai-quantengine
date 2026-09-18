# Antigravity QuantEngine — Walk-Forward Out-Of-Sample Validation

## 1. Purged & Embargoed Cross-Validation

Walk-forward validation prevents lookahead leakage through explicit boundary segmentation:

```text
[      TRAIN WINDOW      ] [ PURGE ] [ TEST WINDOW (OOS) ] [ EMBARGO ]
|------------------------|---------|---------------------|-----------|
0                       500       510                   660         670
```

- **Train Window**: In-sample training/optimization slice.
- **Purge Buffer**: Discards samples immediately following the train window to prevent overlapping label leakage.
- **Test Window**: Strictly out-of-sample evaluation slice.
- **Embargo Buffer**: Post-test buffer preventing test-set information from bleeding into subsequent training folds.

## 2. Walk-Forward Metrics

- **OOS P&L**: Cumulative performance exclusively evaluated on out-of-sample test windows.
- **Degradation Ratio**: $\text{Sharpe}_{test} / \text{Sharpe}_{train}$. Values near 1.0 indicate high out-of-sample stability; values $< 0.4$ indicate overfitting.
