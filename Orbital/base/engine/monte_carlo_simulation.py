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
    1. Price randomization makes use of GBM, student's t, jump diffusion, HMM

    Methods 
    1. simulate(number_sim, degree_freedom)
    2. randomize_price(price_lst: list[float]) -> list[float]
    3. GBM formula
    4. T distribution
    5 Jump diffusion
    6. HMM
    '''
    def __init__(self, backtest: Backtest):
        self.backtest = backtest

    def randomize_price(self, og_price: list[float], mu: float, dt: float, sigma: float,
                        df: float, exp_jumps: int = 0, mean_log_jump_size: float = 0.05,
                        std_log_jump_size: float = 0.01, is_t: bool = True,
                        is_reg_switch: bool = True) -> list[float]:
        '''
        Takes a price list and some parameters and returns a randomized price list
        '''
        if is_t:
            epsilon_lst = self.get_t_epsilon_lst(len(og_price) - 1, df)
        else:
            epsilon_lst = self.get_normal_epsilon_lst(len(og_price) - 1)

        if not is_reg_switch:
            return self.gbm(og_price, mu, dt, sigma, epsilon_lst, exp_jumps,
                            mean_log_jump_size, std_log_jump_size)
        
        # Jump params
        lambda_j = exp_jumps
        lambda_j = lambda_j / 252 # Make it daily
        mu_j = mean_log_jump_size
        sigma_j = std_log_jump_size
        expected_jump_size = math.exp(mu_j + sigma_j**2 / 2) - 1

        # Regime params
        regimes = ["LOW", "HIGH"]
        model = self.get_model(og_price)
        curr_regime = np.random.choice(a=regimes, p=model.startprob_)
        # Testing
        high_regime_count = 0
        low_regime_count = 0
        # Store result
        result = [og_price[0]]
        for _ in range(len(og_price) - 1):
            if curr_regime == "LOW":
                mu = model.means_[0][0]
                sigma = np.sqrt(model._covars_[0][0][0])
                curr_regime = np.random.choice(a=regimes, p=model.transmat_[0])
                # Testing
                low_regime_count += 1
                print(mu, sigma)
            elif curr_regime == "HIGH":
                mu = model.means_[1][0]
                sigma = np.sqrt(model._covars_[1][0][0])
                curr_regime = np.random.choice(a=regimes, p=model.transmat_[0])
                # Testing
                high_regime_count += 1
                print(mu, sigma)
            else:
                raise ValueError("Should be of LOW/HIGH vol reg")
            # Apply ito correction to mu
            ito_mu = mu - ((sigma ** 2) / 2)

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
        return result
        

    def get_normal_epsilon_lst(self, size: int) -> list[float]:
        '''
        Returns len epsilon draws of a normal dist
        '''
        return np.random.normal(size=size)
    
    def get_t_epsilon_lst(self, size: int, df: float) -> list[float]:
        '''
        Returns len epsilon draws of a t dist scaled
        '''
        if df <= 2:
            raise ValueError("df must be greater than 2")
        epsilon_lst_raw = student_t.rvs(df=df, size=size)
        return np.array(epsilon_lst_raw) / np.sqrt(df / (df - 2))

    def gbm(self, og_price: list[float], mu: float,
            dt: float, sigma: float, epsilon_lst: list[float],
            exp_jumps: int = 0,
            mean_log_jump_size: float = 0.05,
            std_log_jump_size: float = 0.01) -> list[float]:
        '''
        This function behaves like gbm if no jumps are specified.
        '''
        assert len(epsilon_lst) == len(og_price) - 1, (f"epsilon list must be equal to price list - 1")
        # Jump params
        lambda_j = exp_jumps
        lambda_j = lambda_j / 252 # Make it daily
        mu_j = mean_log_jump_size
        sigma_j = std_log_jump_size
        expected_jump_size = math.exp(mu_j + sigma_j**2 / 2) - 1

        jump_contribution_lst = []
        # Calculate jump contribution per day
        for _ in range(len(og_price) - 1):
            jumps = poisson.rvs(mu=lambda_j)
            jump_draws = np.random.normal(loc=mu_j, scale=sigma_j, size=jumps)
            jump_contribution_lst.append(jump_draws.sum())
        # Turn jump contribution list to np array for calculation
        jump_contribution_lst = np.array(jump_contribution_lst)

        # print(jump_contribution_lst)
        ito_mu = mu - ((sigma ** 2) / 2)
        jump_mu = ito_mu - lambda_j * expected_jump_size
        rand_log_ret_lst = jump_mu * dt + sigma * epsilon_lst * np.sqrt(dt) + jump_contribution_lst
        random_prices = (og_price[0] * np.exp(rand_log_ret_lst.cumsum())).tolist()
        random_prices.insert(0, og_price[0])
        return random_prices

    # THis is a working gbm that has been refactored a basic version 
    # commented out because advanced version with jump does all of basic features
    # def gbm(self, og_price: list[float], mu: float,
    #         dt: float, sigma: float, epsilon_lst: list[float]) -> list[float]:
    #     '''
    #     This is the most basic GBM.
    #     Generates a list of randomized prices based on parameters.

    #     Follows this formula
    #     S(t) = S(0) * e^X
    #     X = log_ret_d1 + log_ret_d2...
    #     '''
    #     ito_mu = mu - sigma ** 2 / 2
    #     rand_log_ret_lst = ito_mu * dt + sigma * epsilon_lst * np.sqrt(dt)
    #     random_prices = (og_price[0] * np.exp(rand_log_ret_lst.cumsum())).tolist()
    #     random_prices.insert(0, og_price[0])
    #     return random_prices



    # Old GBM Works but not refactored
    # def gbm_(self, stock_data: list[Bar], df:float) -> list[Bar]:
    #     '''
    #     Description 
    #     Function takes in a list of stock prices and returns a randomized list
    #     of stock prices using GBM. 

    #     Features
    #     1. Uses Ito Correction GBM Formula
    #     2. For each day's stock data, the only adjusted attributes are open and closed
    #     3. Brownian motion uses a t distribution instead of normal to describe 
    #     fatter tails (implemented but not tested)
    #     4. 
    #     '''
    #     # Stores randomized data
    #     random_data: list[Bar] = []

    #     # First obtain a list containing open prices and close prices
    #     open_prices = list(map(lambda bar: bar.open, stock_data))
    #     close_prices = list(map(lambda bar: bar.close, stock_data))

    #     # Use GBM to randomize their prices
        # random_open = self.gbm_prices(open_prices, df)
        # random_close = self.gbm_prices(close_prices, df)

        # # return a modified stock data in new list. i is index
        # for i, bar in enumerate(stock_data):
        #     new_bar = Bar(symbol=bar.symbol,
        #                   date=bar.date,
        #                   open=random_open[i],
        #                   high=bar.high,
        #                   low=bar.low,
        #                   close=random_close[i],
        #                   volume=bar.volume,
        #                   asset_type=bar.asset_type
        #                   )
        #     random_data.append(new_bar)
        # # For testing
        # # return random_open
        # return random_data

    def transform_daily_logged(self, prices: list[float]) -> np.array:
        '''
        Takes in a list of prices and returns a list of logged returns. 
        '''
        return np.diff(np.log(prices))

    # Old jump prices, works and allows for regime switching but not refactored
    # def jump_prices(self, prices: list[float], df: float,
    #                 exp_jumps: int, mean_log_jump_size: float,
    #                 std_log_jump_size: float) -> list[float]:
    #     '''
    #     This function is GBM prices with Jump diffusion
    #     log returns becomes r_t = (μ - λk̄ - σ²/2)·Δt + sigma·√Δt·Z + Σ log(Jᵢ)
    #     '''
    #     # This is done otherwise scaling will return NaN
    #     if df <= 2:
    #         raise ValueError("Degree of freedom must be greater than 2")
    #     lambda_j = exp_jumps
    #     lambda_j = lambda_j / 252 # Make it daily
    #     mu_j = mean_log_jump_size
    #     sigma_j = std_log_jump_size

        # # Explicitly state dt as 1
        # dt = 1

        # # random price is computed from previous price so initialize
        # # With initial price
        # result = [prices[0]]
        # logged_returns = self.transform_daily_logged(prices)

        # # Obtain sigma and mu
        # # ddof=1 for sample std, by default is 1, but make explicit
        # sigma = logged_returns.std(ddof=1)
        # mu = logged_returns.mean()

        # # Obtain k in formula
        # expected_jump_size = math.exp(mu_j + sigma_j**2 / 2) - 1

        # # Calculate current regime
        # regimes = ["LOW", "HIGH"]
        # model = self.create_model(prices)
        # transition_matrix = self.obtain_sorted_transmat(model)
        # prob = self.obtain_sorted_startp(model)
        # curr_regime = np.random.choice(a=regimes, p=prob)

        # # Testing
        # low_regime_count = 0
        # high_regime_count = 0
        # for _ in range(1, len(prices)):
        #     if curr_regime == "LOW":
        #         reg_mod_mu = 1
        #         reg_mod_sigma = 1
        #         curr_regime = np.random.choice(a=regimes, p=transition_matrix[0])
        #         # Testing
        #         low_regime_count += 1
        #     elif curr_regime == "HIGH":
        #         reg_mod_mu = 1
        #         reg_mod_sigma = 1
        #         curr_regime = np.random.choice(a=regimes, p=transition_matrix[1]) 
        #         # Testing
        #         high_regime_count += 1
            # else:
            #     raise ValueError("Should be of LOW/HIGH vol reg")
            # print(curr_regime)
            # # Calculate mu and sigma
            # mu *= reg_mod_mu
            # sigma *= reg_mod_sigma

            # # Apply ito correction to mu
            # ito_mu = mu - ((sigma ** 2) / 2)
            # # Apply jump correction to mu
            # jump_mu = ito_mu - lambda_j * expected_jump_size

            # # epsilon_raw has to be scaled as variance of t distribution is dependent on
            # # degree of freedom
            # epsilon_raw = student_t.rvs(df)
            # epsilon = epsilon_raw / np.sqrt(df / (df - 2))

            # # Calculate jump contribution
            # jump_contribution = 0
            # jumps = poisson.rvs(mu=lambda_j)
            # for _ in range(jumps):
            #     jump_draw = normal.rvs(loc=mu_j, scale=sigma_j)
            #     jump_contribution += jump_draw

        #     # Calculate price and append it
        #     log_return = jump_mu * dt + sigma * np.sqrt(dt) * epsilon + jump_contribution
        #     random_price = round(result[-1] * math.exp(log_return), 2)
        #     result.append(random_price)
        # print(f"Number of low regime days = {low_regime_count}")
        # print(f"Number of high regime days = {high_regime_count}")
        # # p prob stay in low, q prob stay in high
        # p = transition_matrix[0][0]
        # q = transition_matrix[1][1]
        # print(f"Transition matrix and days run = {transition_matrix, len(prices)- 1}")
        # print(f"Theoretical low days = {((1 - p) / (2 - p - q))}")
        # # print(f"Theoretical high days = {(1 - p)/ (2 - p - q)}")

        # return result

    def get_model(self, prices: list[float]) -> hmm.GaussianHMM:
        '''
        Takes in a list of prices and returns a sorted model from the prices
        '''
        return self.model_sort(self.create_model(prices))
    def create_model(self, prices: list[float]) -> hmm.GaussianHMM:
        '''
        Creates a model
        random_state is set such that all transition matrixes, on the same data are the same.
        '''
        model = hmm.GaussianHMM(n_components=2, covariance_type="full", n_iter=1000, random_state=1)
        # Turn the prices into a 2D array, each row representing day, and value
        # is log return
        data = np.array(self.transform_daily_logged(prices)).reshape(-1,1)
        model = model.fit(data)
        return model
    
    def model_sort(self, model: hmm.GaussianHMM) -> hmm.GaussianHMM:
        '''
        Sorts the model
        '''
        variances = [model.covars_[i][0][0] for i in range(len(model.covars_))]
        order = np.argsort(variances)

        # Testing
        # print(f" Before Sort = {model.covars_}")
        # Reorder rows
        model.means_ = model.means_[order]
        model.covars_ = model.covars_[order]
        model.startprob_ = model.startprob_[order]

        # Testing
        # print(f" After Sort = {model.covars_}")
        # Transition matrix needs both rows and columns reordered
        model.transmat_ = model.transmat_[np.ix_(order, order)]
        return model

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
        ito_mu = logged_returns.mean()
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

    prices = list(map(lambda bar: bar.open, stock_data["AAPL"]))
    mcs.randomize_price(prices)

