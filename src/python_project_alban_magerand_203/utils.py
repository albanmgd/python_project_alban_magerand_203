from pybacktestchain.broker import RebalanceFlag
import pandas as pd
from datetime import datetime
# Used to define variables in one place
ptf_construction_options = ['Option 1', 'Option 2', 'Option 3']
rebalancing_flag_options = ['Daily', 'Weekly', 'Monthly']
risk_models = ['None', 'StopLoss']

# Better options would be to get compositions of indexes (SP500, ...) but getting it PiT is tricky
universe_options = sorted(
    [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'INTC', 'CSCO', 'NFLX',
    ]
)
perf_metrics = [
    "Total Return", "Annualized Return", "Annualized Volatility", "Sharpe Ratio", "Sortino Ratio",
    "Maximum Drawdown", "Calmar Ratio"
]

class EndOfWeek(RebalanceFlag):
    def time_to_rebalance(self, t: datetime):
        # Convert to pandas Timestamp for convenience
        pd_date = pd.Timestamp(t)
        # Check if the given date is a Friday (end of the business week)
        return pd_date.weekday() == 4  # 4 corresponds to Friday


class EndOfDay(RebalanceFlag):
    def time_to_rebalance(self, t: datetime):
        return True