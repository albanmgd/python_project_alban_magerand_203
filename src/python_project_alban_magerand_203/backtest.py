import pandas as pd
import numpy as np
import logging
import os
from pybacktestchain.broker import StopLoss
from pybacktestchain.data_module import FirstTwoMoments, get_stocks_data, DataModule, Information
from pybacktestchain.utils import generate_random_name
from pybacktestchain.broker import EndOfMonth, Broker
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from glob import  glob
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


@dataclass
class Backtest:
    initial_date: datetime
    final_date: datetime
    universe: list = field(default_factory=lambda:  ['AAPL', 'NFLX'])
    information_class: type = Information
    s: timedelta = timedelta(days=360)
    rtn_estimates: str = 'Raw'
    obj_fct: str = 'Utility'
    time_column: str = 'Date'
    company_column: str = 'ticker'
    adj_close_column: str = 'Adj Close'
    rebalance_flag: type = EndOfMonth
    risk_model: type = StopLoss
    initial_cash: int = 1000000  # Initial cash in the portfolio
    name_blockchain: str = 'backtest'
    verbose: bool = True
    broker: Broker = field(default_factory=lambda: Broker(cash=1000000, verbose=True)) # has to be not-mutable


    def __post_init__(self):
        self.backtest_name = generate_random_name()
        self.broker.initialize_blockchain(self.name_blockchain)

    def run_backtest(self):
        if (self.initial_date <= self.final_date) and (len(self.universe) > 0):
            logging.info(f"Running backtest from {self.initial_date} to {self.final_date}.")
            logging.info(f"Retrieving price data for universe")

            # self.initial_date to yyyy-mm-dd format
            init_ = (self.initial_date -self.s).strftime('%Y-%m-%d') # - s days to get enough data to compute rtns
            # self.final_date to yyyy-mm-dd format
            final_ = self.final_date.strftime('%Y-%m-%d')
            df = get_stocks_data(self.universe, init_, final_)

            # Initialize the DataModule
            data_module = DataModule(df)

            # Create the Information object
            info = self.information_class(s=self.s,
                                          data_module=data_module,
                                          time_column=self.time_column,
                                          company_column=self.company_column,
                                          adj_close_column=self.adj_close_column)
            info.estimate_expected_rtn = self.rtn_estimates
            info.optim_fct = self.obj_fct
            # Initializing the ptf value list
            rows_pnl= []
            # Run the backtest
            for t in pd.bdate_range(start=self.initial_date, end=self.final_date, freq='D'):

                if self.risk_model is not None:
                    portfolio = info.compute_portfolio(t, info.compute_information(t)) or {}
                    prices = info.get_prices(t)
                    self.risk_model.trigger_stop_loss(t, portfolio, prices, self.broker)

                if self.rebalance_flag().time_to_rebalance(t):
                    logging.info("-----------------------------------")
                    logging.info(f"Rebalancing portfolio at {t}")
                    information_set = info.compute_information(t)
                    portfolio = info.compute_portfolio(t, information_set) or {}
                    prices = info.get_prices(t)
                    self.broker.execute_portfolio(portfolio, prices, t)

                rows_pnl.append({'date': t, 'ptf_value': self.broker.get_portfolio_value(info.get_prices(t))})
            logging.info(
                f"Backtest completed. Final portfolio value: {self.broker.get_portfolio_value(info.get_prices(self.final_date))}")
            df_transaction_log = self.broker.get_transaction_log()
            # Computing the daily PnL from daily portfolio value
            df_ptf_value = pd.DataFrame(rows_pnl)
            df_ptf_value['daily_pnl'] = df_ptf_value['ptf_value'].diff()
            df_ptf_value['daily_pnl'].fillna(0, inplace=True)

            # create transaction log folder if it does not exist
            if not os.path.exists('transaction_logs'):
                os.makedirs('transaction_logs')
            # create backtests folder if it does not exist
            if not os.path.exists('backtests'):
                os.makedirs('backtests')

            # save to parquet, use the backtest name
            df_transaction_log.to_parquet(f"transaction_logs/{self.backtest_name}.parquet")
            df_ptf_value.to_parquet(f"backtests/{self.backtest_name}.parquet")

            # store the backtest in the blockchain
            self.broker.blockchain.add_block(self.backtest_name, df.to_string())

    def get_df_backtest(self):
        # Checks first if the backtest exists; otherwise creating it
        files = glob(f"backtests/{self.backtest_name}.parquet")
        if len(files) != 1: # if file doesn't exist, generate it
            self.run_backtest()
        df_backtest = pd.DataFrame()
        try:
            df_backtest = pd.read_parquet(glob(f"backtests/{self.backtest_name}.parquet"))
        except Exception as e:
            logging.log(e)
        return df_backtest

    def get_backtest_metrics(self, df, risk_free_rate=0.0):
        if ('date' in df.columns) and ('ptf_value' in df.columns) and (~df.empty):
            # Compute daily return directly from portfolio value
            df['daily_return'] = df['ptf_value'].pct_change()
            df['daily_return'] = df['daily_return'].fillna(0) # Handle NaN on first row

            # Compute cumulative returns
            df['cum_pnl'] = df['ptf_value'] - df['ptf_value'].iloc[0]  # PnL relative to initial value

            # Key statistics
            total_return = df['ptf_value'].iloc[-1] / df['ptf_value'].iloc[0] - 1  # As a decimal
            num_bdays = len(df) # no duplicates so only counting the nb of business dates
            # Corrected annualized return
            annualized_return = (1 + total_return) ** (252 / num_bdays) - 1  # As a decimal

            # Convert to percentage for display
            annualized_return *= 100

            # Annualized volatility
            daily_volatility = df['daily_return'].std() * (252 ** 0.5)  # Scale by sqrt(252)
            annualized_volatility = daily_volatility * np.sqrt(252)

            # Sharpe ratio
            excess_return = annualized_return - risk_free_rate
            sharpe_ratio = np.sqrt(252) * (df['daily_return'] - risk_free_rate / 252).mean() / df['daily_return'].std()

            # Maximum Drawdown (MDD)
            df['peak'] = df['cum_pnl'].cummax()
            df['drawdown'] = df['cum_pnl'] - df['peak']
            max_drawdown = df['drawdown'].min()

            # Sortino Ratio (using downside deviation)
            downside_returns = df[df['daily_return'] < 0]['daily_return']
            downside_volatility = downside_returns.std() * np.sqrt(252)
            sortino_ratio = excess_return / downside_volatility if downside_volatility > 0 else np.nan

            return pd.DataFrame.from_dict(
            {
                    "Total Return (%)": 100 * total_return,
                    "Annualized Return (%)": annualized_return,
                    "Annualized Volatility (%)": annualized_volatility,
                    "Sharpe Ratio": sharpe_ratio,
                    "Sortino Ratio": sortino_ratio,
                    "Maximum Drawdown ($)": max_drawdown,
                },
                orient='index',  # Keys become row indices
                columns=['Value']  # Single column name
            ).round(2).reset_index(names=['Metric'])
        else:
            return pd.DataFrame()

if __name__ == '__main__':
    backtest = Backtest(
        initial_date=datetime(2019, 1, 1),
        final_date=datetime(2020, 1, 1),
        information_class=FirstTwoMoments,
        risk_model=StopLoss,
        name_blockchain='backtest',
        verbose=True
    )
    df = backtest.get_df_backtest()
    backtest.get_backtest_metrics(df)

