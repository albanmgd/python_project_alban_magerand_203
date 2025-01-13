from pybacktestchain.broker import RebalanceFlag
import pandas as pd
from datetime import datetime
# Used to define variables in one place
rtns_estimates_options = ['Simple Average', 'EWMA']
opt_fcts = {'Sharpe Ratio': 'sharpe', 'Utility': 'utility'}
rebalancing_flag_options = ['Daily', 'Weekly', 'Monthly']
risk_models = ['None', 'StopLoss']

# Better options would be to get compositions of indexes (SP500, ...) but getting it PiT is tricky
universe_options = {
    "United States": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "BRK.B", "JNJ", "V", "WMT", "JPM"],
    "Canada": ["RY.TO", "TD.TO", "BNS.TO", "ENB.TO", "BMO.TO", "SHOP.TO", "CNQ.TO", "BCE.TO", "TRP.TO", "CNR.TO"],
    "United Kingdom": ["HSBA.L", "BP.L", "RDSA.L", "GSK.L", "DGE.L", "ULVR.L", "AZN.L", "RIO.L", "BATS.L", "VOD.L"],
    "Germany": ["SAP.DE", "SIE.DE", "ALV.DE", "BAS.DE", "BAYN.DE", "BMW.DE", "VOW3.DE", "DAI.DE", "DBK.DE", "DTE.DE"],
    "France": ["OR.PA", "SAN.PA", "AIR.PA", "MC.PA", "BNP.PA", "DG.PA", "EN.PA", "FP.PA", "SGO.PA", "VIE.PA"],
    "Japan": ["7203.T", "6758.T", "9432.T", "9984.T", "8306.T", "7267.T", "4502.T", "8058.T", "8411.T", "8031.T"],
    "Australia": ["CBA.AX", "BHP.AX", "WBC.AX", "ANZ.AX", "NAB.AX", "WES.AX", "CSL.AX", "TLS.AX", "WOW.AX", "RIO.AX"],
    "China": ["BABA", "TCEHY", "JD", "BIDU", "PDD", "NIO", "XPEV", "LI", "BILI", "NTES"],
    "India": ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "HINDUNILVR.NS", "ICICIBANK.NS", "KOTAKBANK.NS", "SBIN.NS", "BAJFINANCE.NS", "BHARTIARTL.NS"],
    "Brazil": ["PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "ABEV3.SA", "BBAS3.SA", "B3SA3.SA", "WEGE3.SA", "RENT3.SA", "SUZB3.SA"]
}
universe_options["All"] = sorted([stock for stocks in universe_options.values() for stock in stocks])

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