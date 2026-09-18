from core.research.statistical_validation import StatisticalValidator
from core.research.backtest import BacktestTrade


def test_multiple_testing_adjustments():
    # 5 test p-values: some significant, some not
    p_values = [0.001, 0.012, 0.035, 0.08, 0.45]

    # 1. Bonferroni
    bonf = StatisticalValidator.adjust_multiple_testing(p_values, method="BONFERRONI", alpha=0.05)
    assert bonf.num_hypotheses == 5
    # First p-value adjusted: 0.001 * 5 = 0.005 < 0.05 -> significant
    assert bonf.adjusted_p_values[0] == 0.005
    assert bonf.significant_hypotheses_count >= 1

    # 2. Benjamini-Hochberg FDR
    bh = StatisticalValidator.adjust_multiple_testing(p_values, method="BENJAMINI_HOCHBERG", alpha=0.05)
    assert bh.significant_hypotheses_count >= bonf.significant_hypotheses_count


def test_monte_carlo_reshuffle():
    trades = [
        BacktestTrade(trade_id="t1", symbol="BTC-USD", side="LONG", entry_bar=0, entry_time="0", entry_price=100, exit_bar=1, exit_time="1", exit_price=105, quantity=1, gross_pnl=50, fees=1, slippage=0, net_pnl=49, exit_reason="TP"),
        BacktestTrade(trade_id="t2", symbol="BTC-USD", side="LONG", entry_bar=2, entry_time="2", entry_price=105, exit_bar=3, exit_time="3", exit_price=102, quantity=1, gross_pnl=-30, fees=1, slippage=0, net_pnl=-31, exit_reason="SL"),
        BacktestTrade(trade_id="t3", symbol="BTC-USD", side="LONG", entry_bar=4, entry_time="4", entry_price=102, exit_bar=5, exit_time="5", exit_price=110, quantity=1, gross_pnl=80, fees=1, slippage=0, net_pnl=79, exit_reason="TP"),
    ]

    mc = StatisticalValidator.run_monte_carlo_reshuffle(trades, initial_capital=10000.0, num_simulations=100, seed=42)
    assert mc.input_trades_count == 3
    assert mc.num_simulations == 100
    assert mc.expected_final_pnl_median > 0
