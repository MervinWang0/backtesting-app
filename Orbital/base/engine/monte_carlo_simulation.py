import os
import sys
import django
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Orbital.settings")
django.setup()


from queue import Queue
from datetime import datetime
from base.engine.data_loader import (DataLoader, Bar,
                                     DatabaseDataLoader,
                                     MCSDataLoader)
from base.engine.backtest import Backtest, BacktestResult
import numpy as np
import pandas as pd
import math
from scipy.stats import t as student_t
from scipy.stats import poisson as poisson
from scipy.stats import norm as normal
import base.engine.graph as graph
from base.engine.distribution import Distribution
from hmmlearn import hmm

class MonteCarloSimulator():
    '''
    This class carries out simulated backtests and returns metrics computed from them.

    Features
    1. Uses GBM to randomize price.

    Methods 
    1. simulate(number_sim, degree_freedom)
    '''
    def __init__(self, backtest: Backtest):
        self.backtest = backtest

    def gbm(self, stock_data: list[Bar], df:float) -> list[Bar]:
        '''
        Description 
        Function takes in a list of stock prices and returns a randomized list
        of stock prices using GBM. 

        Features
        1. Uses Ito Correction GBM Formula
        2. For each day's stock data, the only adjusted attributes are open and closed
        3. Brownian motion uses a t distribution instead of normal to describe 
        fatter tails (implemented but not tested)
        4. 

        Implementation details
        It has the formula (before ito correction)
        X(t) = X(0) * nat_exp(mu * t + sigma * B(t))

        Variables explanation
        X(t) price of stock at day t
        X(0) initial price of stock
        mu => drift => annualized sample mean of logged daily returns 
        t => day => fraction of year, n/252, where n is the day of the stock (0 is first day)
        sigma => volatility => annualized std of logged daily returns
        B(t) => a random outcome of t distribution scaled to match volatility.

        GBS with Ito correction, (more accurate)
        X(t) = X(0) * nat_exp((mu - (sigma^2 / 2)) * t + sigma * B(t))
        The difference is that mu has a subtraction of sigma squared divided by 2
        '''
        random_data: list[Bar] = [] # Stores randomized data

        # First obtain a list containing open prices and close prices
        open_prices = list(map(lambda bar: bar.open, stock_data))
        close_prices = list(map(lambda bar: bar.close, stock_data))

        # Use GBM to randomize their prices
        random_open = self.gbm_prices(open_prices, df)
        random_close = self.gbm_prices(close_prices, df)

        # return a modified stock data in new list. i is index
        for i, bar in enumerate(stock_data):
            new_bar = Bar(symbol=bar.symbol,
                          date=bar.date,
                          open=random_open[i],
                          high=bar.high,
                          low=bar.low,
                          close=random_close[i],
                          volume=bar.volume,
                          asset_type=bar.asset_type
                          )
            random_data.append(new_bar)
        # For testing
        # return random_open
        return random_data

    def transform_daily_logged(self, prices: list[float]) -> pd.Series[float]:
        '''
        Takes in a list of prices and returns a list of logged returns. 
        '''
        # First log price then obtains price diff (if log carried after may log a negative)
        logged = map(math.log, prices)
        return pd.Series(logged).diff().dropna()

    def jump_prices(self, prices: list[float], df: float,
                    exp_jumps: int, mean_log_jump_size: float,
                    std_log_jump_size: float) -> list[float]:
        '''
        This function is GBM prices with Jump diffusion
        log returns becomes r_t = (μ - λk̄ - σ²/2)·Δt + sigma·√Δt·Z + Σ log(Jᵢ)
        '''
        # This is done otherwise scaling will return NaN
        if df <= 2:
            raise ValueError("Degree of freedom must be greater than 2")
        lambda_j = exp_jumps
        lambda_j = lambda_j / 252 # Make it daily
        mu_j = mean_log_jump_size
        sigma_j = std_log_jump_size

        # Explicitly state dt as 1
        dt = 1

        # random price is computed from previous price so initialize
        # With initial price
        result = [prices[0]]
        logged_returns = self.transform_daily_logged(prices)

        # Obtain sigma and mu
        # ddof=1 for sample std, by default is 1, but make explicit
        sigma = logged_returns.std(ddof=1)
        mu = logged_returns.mean()

        # Obtain k in formula
        expected_jump_size = math.exp(mu_j + sigma_j**2 / 2) - 1

        # Calculate current regime
        regimes = ["LOW", "HIGH"]
        model = self.create_model(prices)
        transition_matrix = self.obtain_sorted_transmat(model)
        prob = self.obtain_sorted_startp(model)
        curr_regime = np.random.choice(a=regimes, p=prob)

        # Testing
        low_regime_count = 0
        high_regime_count = 0
        for _ in range(1, len(prices)):
            if curr_regime == "LOW":
                reg_mod_mu = 1
                reg_mod_sigma = 1
                curr_regime = np.random.choice(a=regimes, p=transition_matrix[0])
                # Testing
                low_regime_count += 1
            elif curr_regime == "HIGH":
                reg_mod_mu = 1
                reg_mod_sigma = 1
                curr_regime = np.random.choice(a=regimes, p=transition_matrix[1])
                # Testing
                high_regime_count += 1
            else:
                raise ValueError("Should be of LOW/HIGH vol reg")
            print(curr_regime)
            # Calculate mu and sigma
            mu *= reg_mod_mu
            sigma *= reg_mod_sigma

            # Apply ito correction to mu
            ito_mu = mu - ((sigma**2) / 2)
            # Apply jump correction to mu
            jump_mu = ito_mu - lambda_j * expected_jump_size

            # epsilon_raw has to be scaled as variance of t distribution is dependent on
            # degree of freedom
            epsilon_raw = student_t.rvs(df)
            epsilon = epsilon_raw / np.sqrt(df / (df - 2))

            # Calculate jump contribution
            jump_contribution = 0
            jumps = poisson.rvs(mu=lambda_j)
            for _ in range(jumps):
                jump_draw = normal.rvs(loc=mu_j, scale=sigma_j)
                jump_contribution += jump_draw

            # Calculate price and append it
            log_return = jump_mu * dt + sigma * np.sqrt(dt) * epsilon + jump_contribution
            random_price = round(result[-1] * math.exp(log_return), 2)
            result.append(random_price)
        print(f"Number of low regime days = {low_regime_count}")
        print(f"Number of high regime days = {high_regime_count}")
        # p prob stay in low, q prob stay in high
        p = transition_matrix[0][0]
        q = transition_matrix[1][1]
        print(f"Transition matrix and days run = {transition_matrix, len(prices)- 1}")
        print(f"Theoretical low days = {((1 - p) / (2 - p - q))}")
        # print(f"Theoretical high days = {(1 - p)/ (2 - p - q)}")

        return result

    def create_model(self, prices: list[float]) -> hmm.GaussianHMM:
        '''
        Creates a model
        random_state is set such that all transition matrixes, on the same data are the same.
        '''
        model = hmm.GaussianHMM(n_components=2, covariance_type="diag", n_iter=1000, random_state=1)
        # Turn the prices into a 2D array, each row representing day, and value
        # is log return
        data = np.array(self.transform_daily_logged(prices)).reshape(-1,1)
        model = model.fit(data)
        return model

    def obtain_sorted_transmat(self, model:hmm.GaussianHMM) -> list[list[float]]:
        '''
        Returns a transition matrix
        '''
        variances = [model.covars_[i][0][0] for i in range(len(model.covars_))]
        # print(f"This is the variance {variances}")
        # print(f"This is the covars, {model.covars_}")
        low_reg  = np.argmin(variances)
        high_reg = np.argmax(variances)

        # Reorder rows and columns so row 0 = low vol, row 1 = high vol
        order = [low_reg, high_reg]
        sorted_transmat = model.transmat_[np.ix_(order, order)]
        return sorted_transmat

    def obtain_sorted_startp(self, model:hmm.GaussianHMM) -> list[float]:
        '''
        Returns the sorted starting probabilities
        '''
        variances = [model.covars_[i][0][0] for i in range(len(model.covars_))]
        low_reg  = np.argmin(variances)
        high_reg = np.argmax(variances)

        # Reorder rows and columns so row 0 = low vol, row 1 = high vol
        order = [low_reg, high_reg]
        return model.startprob_[order]

    def gbm_prices(self, prices: list[float], df: float) -> list[float]:
        '''
        This function takes in a list of prices and returns a list of gbm 
        modified prices

        Implementation details
        Using GBM Formula
        X(t) = X(t-1) * exp(ito_mu * dt + sigma * root(dt) * epsilon)
        X(t), is the t-th randomized price
        ito_mu = drift
        dt = size time step (1 for daily)
        epsilon = shock
        root(dt) = multiplier for shock
        Uses mu, sigma, and dt in terms of day
        '''
        dt = 1
        # This is done otherwise scaling will return NaN
        if df <= 2:
            raise ValueError("Degree of freedom must be greater than 2")

        result = [prices[0]]
        logged_returns = self.transform_daily_logged(prices)

        # Obtain sigma and mu
        # ddof=1 for sample std, by default is 1, but make explicit
        sigma = logged_returns.std(ddof=1)
        mu = logged_returns.mean()

        # Apply ito correction to mu
        ito_mu = mu - ((sigma**2) / 2)
        for _ in range(1, len(prices)):

            # epsilon_raw has to be scaled as variance of t distribution is dependent on
            # degree of freedom
            epsilon_raw = student_t.rvs(df)
            epsilon = epsilon_raw / np.sqrt(df / (df - 2))

            # Calculate price and append it
            random_price = round(result[-1] * math.exp(ito_mu * dt +
                                                       sigma * math.sqrt(dt) * epsilon), 2)
            result.append(random_price)
        return result

    def simulate(self, num: int, df: float):
        '''
        Takes in a number of simulations and a degree of freedom,
        and returns the result of the simulations.
        '''
        stock_data: dict[str, list[Bar]] = self.backtest.data_loader.get_stock_data()
        result = [self.backtest.run()] # Store BackTestResult of each simulation
        
        # For each simulation
        for _ in range(num):
            # random stock data holds randomized stock data of each simulation
            random_stock_data: dict[str, list[Bar]] = {}

            # Populate the random data
            for ticker in self.backtest.tickers:
                random_stock_data[ticker] = self.gbm(stock_data[ticker], df)

            # Once the random historical stock data is obtained, backtest using it
            mcs_data_loader = MCSDataLoader(events=Queue(),
                                            tickers=self.backtest.tickers,
                                            start_date=self.backtest.start_date,
                                            end_date=self.backtest.end_date,
                                            asset_type="STOCK",
                                            data=random_stock_data)

            mcs_backtest = Backtest(events=mcs_data_loader.events,
                                    tickers=self.backtest.tickers,
                                    start_date=self.backtest.start_date,
                                    end_date=self.backtest.end_date,
                                    strategy_name=self.backtest.strategy_name,
                                    data_loader=mcs_data_loader)


            # Stores BackTestResult instances in results
            result.append(mcs_backtest.run())

        return result
if __name__ == "__main__":
    # Test obtaining og list historical data
    start_date = datetime.fromisoformat("2021-05-24").date()
    end_date = datetime.fromisoformat("2022-05-24").date()
    data_loader = DatabaseDataLoader(Queue(), ["AAPL"], start_date,
                             end_date, "STOCK")
    backtest = Backtest(
                        events=Queue(),
                        tickers=["AAPL"],
                        start_date=start_date,
                        end_date=end_date,
                        strategy_name="MovingAverageCross",
                        strategy_params={"short_window": 5,
                                        "long_window": 10},
                        data_loader=DatabaseDataLoader(events=Queue(),
                                                    tickers=["AAPL"],
                                                    start_date=start_date,
                                                    end_date=end_date,
                                                    asset_type="STOCK"))
    backtest.run()
    stock_data = backtest.data_loader.get_stock_data()
    mcs = MonteCarloSimulator(backtest)
    # Testing the hmm model creation function
    prices = list(map(lambda bar: bar.open, stock_data["AAPL"]))
    test = mcs.create_model(prices)

    # Test sort prob

    # Test sorted transmat
    t_m = mcs.obtain_sorted_transmat(test)
    # print(test.startprob_[[1,0]])
    # print(t_m)

