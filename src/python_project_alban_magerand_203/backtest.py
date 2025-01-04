import pandas as pd
import logging
import os
from pybacktestchain.broker import StopLoss
from pybacktestchain.data_module import FirstTwoMoments, get_stocks_data, DataModule, Information
from pybacktestchain.utils import generate_random_name
from pybacktestchain.broker import EndOfMonth, Broker
from datetime import datetime, timedelta
from dataclasses import dataclass
from glob import  glob
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


@dataclass
class Backtest:
    initial_date: datetime
    final_date: datetime
    universe = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'INTC', 'CSCO', 'NFLX']
    information_class: type = Information
    s: timedelta = timedelta(days=360)
    time_column: str = 'Date'
    company_column: str = 'ticker'
    adj_close_column: str = 'Adj Close'
    rebalance_flag: type = EndOfMonth
    risk_model: type = StopLoss
    initial_cash: int = 1000000  # Initial cash in the portfolio
    name_blockchain: str = 'backtest'
    verbose: bool = True
    broker = Broker(cash=initial_cash, verbose=verbose)

    def __post_init__(self):
        self.backtest_name = generate_random_name()
        self.broker.initialize_blockchain(self.name_blockchain)

    def run_backtest(self):
        logging.info(f"Running backtest from {self.initial_date} to {self.final_date}.")
        logging.info(f"Retrieving price data for universe")
        self.risk_model = self.risk_model(threshold=0.1)
        # self.initial_date to yyyy-mm-dd format
        init_ = self.initial_date.strftime('%Y-%m-%d')
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

        # Initializing the ptf value list
        rows_pnl = []
        # Run the backtest
        for t in pd.date_range(start=self.initial_date, end=self.final_date, freq='D'):

            if self.risk_model is not None:
                portfolio = info.compute_portfolio(t, info.compute_information(t))
                prices = info.get_prices(t)
                self.risk_model.trigger_stop_loss(t, portfolio, prices, self.broker)

            if self.rebalance_flag().time_to_rebalance(t):
                logging.info("-----------------------------------")
                logging.info(f"Rebalancing portfolio at {t}")
                information_set = info.compute_information(t)
                portfolio = info.compute_portfolio(t, information_set)
                prices = info.get_prices(t)
                self.broker.execute_portfolio(portfolio, prices, t)

            rows_pnl.append({'Date': t, 'ptf_value': self.broker.get_portfolio_value(info.get_prices(t))})
        logging.info(
            f"Backtest completed. Final portfolio value: {self.broker.get_portfolio_value(info.get_prices(self.final_date)) - self.initial_cash}")
        df_transaction_log = self.broker.get_transaction_log()
        df_ptf_value = pd.DataFrame(rows_pnl)
        # create transaction log folder if it does not exist
        if not os.path.exists('transaction_logs'):
            os.makedirs('transaction_logs')
        # create backtests folder if it does not exist
        if not os.path.exists('backtests'):
            os.makedirs('backtests')

        # save to parquet, use the backtest name
        df_transaction_log.to_parquet(f"backtests/{self.backtest_name}.parquet")
        df_ptf_value.to_parquet(f"backtests/{self.backtest_name}.parquet")

        # store the backtest in the blockchain
        self.broker.blockchain.add_block(self.backtest_name, df.to_string())





class BacktestAugmented(Backtest):
    def __init__(self, raw_backtest):
        super().__init__(
            initial_date=raw_backtest.initial_date,
            final_date=raw_backtest.final_date,
            information_class=raw_backtest.information_class,
            risk_model=raw_backtest.risk_model,
            name_blockchain=raw_backtest.name_blockchain,
            verbose=raw_backtest.verbose,
        )
        self.backtest_name = raw_backtest.backtest_name
        self.chosen_universe = raw_backtest.universe
        self.raw_backtest = raw_backtest

    def get_df_backtest(self):
        # Checks first if the backtest exists; otherwise creating it
        if len(glob(f"backtests/{self.backtest_name}.csv")) != 1:
            self.raw_backtest.run_backtest()


        df_backtest = pd.read_csv(f"backtests/{self.raw_backtest.backtest_name}.csv")
        return df_backtest

    def compute_backtest_metrics(self):
        df_backtest = self.get_df_backtest()


if __name__ == '__main__':
    backtest = Backtest(
        initial_date=datetime(2019, 1, 1),
        final_date=datetime(2020, 1, 1),
        information_class=FirstTwoMoments,
        risk_model=StopLoss,
        name_blockchain='backtest',
        verbose=True
    )
    backtest.run_backtest()
