from pybacktestchain.data_module import DataModule, Information
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from scipy.optimize import minimize
import numpy as np
from typing_extensions import override


@dataclass
class PortfolioOptimizer(Information):
    def __post_init__(self):
        self.estimate_expected_rtn = None # but are being set in the backtest by default already
        self.optim_fct = None

    @override
    def compute_portfolio(self, t: datetime, information_set):
        try:
            mu = information_set['expected_return']
            Sigma = information_set['covariance_matrix']
            n = len(mu)
            if self.optim_fct == 'utility':
                gamma = 1  # risk aversion parameter
                obj = lambda x: -x.dot(mu) + gamma / 2 * x.dot(Sigma).dot(x)
            elif self.optim_fct == 'sharpe':
                obj = lambda x: -x.dot(mu)/ np.sqrt(x.dot(Sigma).dot(x))
            else: return {}
            # constraints
            cons = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
            # bounds, allow short selling, +- inf
            bounds = [(0.0, 1.0)] * n
            # initial guess, equal weights
            x0 = np.ones(n) / n
            # minimize
            res = minimize(obj, x0, constraints=cons, bounds=bounds)

            # prepare dictionary
            portfolio = {k: None for k in information_set['companies']}

            # if converged update
            if res.success:
                for i, company in enumerate(information_set['companies']):
                    portfolio[company] = res.x[i]
            else:
                raise Exception("Optimization did not converge")

            return portfolio
        except Exception as e:
            # if something goes wrong return an equal weight portfolio but let the user know
            logging.warning("Error computing portfolio, returning equal weight portfolio")
            logging.warning(e)
            return {k: 1 / len(information_set['companies']) for k in information_set['companies']}

    @override
    def compute_information(self, t: datetime):
        # Get the data module
        data = self.slice_data(t)
        # the information set will be a dictionary with the data
        information_set = {}

        # sort data by ticker and date
        data = data.sort_values(by=[self.company_column, self.time_column])

        # expected return per company
        data['return'] = data.groupby(self.company_column)[self.adj_close_column].pct_change()  # .mean()
        if self.estimate_expected_rtn == 'Simple Average':
            # expected return by company
            information_set['expected_return'] = data.groupby(self.company_column)['return'].mean().to_numpy()
        elif self.estimate_expected_rtn == 'EWMA':
            information_set['expected_return'] = (
                data.groupby(self.company_column)['return']
                .transform(lambda x: x.ewm(span=self.s.days, adjust=False).mean())
                .to_numpy()
            )
        else: return {}
        # covariance matrix

        # 1. pivot the data
        data = data.pivot(index=self.time_column, columns=self.company_column, values=self.adj_close_column)
        # drop missing values
        data = data.dropna(axis=0)
        # 2. compute the covariance matrix
        covariance_matrix = data.cov()
        # convert to numpy matrix
        covariance_matrix = covariance_matrix.to_numpy()
        # add to the information set
        information_set['covariance_matrix'] = covariance_matrix
        information_set['companies'] = data.columns.to_numpy()
        return information_set
