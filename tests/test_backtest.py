import pytest
import pandas as pd
from datetime import datetime
from python_project_alban_magerand_203.backtest import Backtest
from pybacktestchain.broker import StopLoss

def test_get_daily_pnl():
    """
    Testing for a theoretically viable backtest
    """
    backtest = Backtest(
        initial_date=datetime(2018, 1, 1),
        final_date=datetime(2020, 1, 1),
        universe=['AAPL', 'NFLX', 'TSLA'],
        risk_model=StopLoss(threshold=0.1)
    )
    df = backtest.get_df_backtest()
    assert df is not None

def test_null_strategy():
    """
    Testing if universe is empty
    """
    backtest = Backtest(
        initial_date=datetime(2018, 1, 1),
        final_date=datetime(2020, 1, 1),
        universe=[],
        risk_model=StopLoss(threshold=0.1)
    )
    df = backtest.get_df_backtest()
    assert (backtest.get_backtest_metrics(df).empty)