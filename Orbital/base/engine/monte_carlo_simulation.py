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
from base.engine.backtest import Backtest
import numpy as np
import math
from scipy.stats import t as student_t
from scipy.stats import poisson as poisson
from scipy.stats import norm as normal
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
        # high_regime_count = 0
        # low_regime_count = 0
        # jump_count = 0
        # Store result
        result = [og_price[0]]
        for _ in range(len(og_price) - 1):
            # print(curr_regime)
            if curr_regime == "LOW":
                mu = model.means_[0][0]
                sigma = np.sqrt(model._covars_[0][0][0])
                curr_regime = np.random.choice(a=regimes, p=model.transmat_[0])
                # Testing
                # low_regime_count += 1
                # print(mu, sigma)
            elif curr_regime == "HIGH":
                mu = model.means_[1][0]
                sigma = np.sqrt(model._covars_[1][0][0])
                curr_regime = np.random.choice(a=regimes, p=model.transmat_[0])
                # Testing
                # high_regime_count += 1
                # print(mu, sigma)
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
            # print(f"This is the number of jumps per day {jumps}")
            # Test if number of jumps is correct
            # jump_count += jumps
            for _ in range(jumps):
                jump_draw = normal.rvs(loc=mu_j, scale=sigma_j)
                jump_contribution += jump_draw

            # Calculate price and append it
            log_return = jump_mu * dt + sigma * np.sqrt(dt) * epsilon + jump_contribution
            random_price = round(result[-1] * math.exp(log_return), 2)
            result.append(random_price)
        return result
        # return jump_count


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

    def transform_daily_logged(self, prices: list[float]) -> np.array:
        '''
        Takes in a list of prices and returns a list of logged returns. 
        '''
        return np.diff(np.log(prices))

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
    
    def simulate(self, num_sims: int, mu: float = 0, dt: float = 1, sigma: float = 0,
                 df: float = 5, exp_jumps: int = 0, mean_log_jump_size: float = 0.05,
                 std_log_jump_size: float = 0.01, is_t: bool = True, is_regime_switching: bool = True,
                 is_jump_diffusion: bool = True, **kwargs):
        '''
        Takes in a number of simulations and a degree of freedom,
        and returns the result of the simulations.
        '''
        if not is_jump_diffusion:
            exp_jumps = 0
        
        # Stock data holds each ticker's stock info for backtest's tickers
        stock_data: dict[str, list[Bar]] = self.backtest.data_loader.get_stock_data()
        
        # Store BackTestResult of each simulation
        result = [self.backtest.run()]

        # For each stock, create arrays to compute OHL prices
        price_calc: dict[str, dict[str, np.array]] = {}

        for ticker in stock_data:
            close_price = np.array([bar.close for bar in stock_data[ticker]])
            price_calc[ticker] = {"open_diff" : np.array([bar.open for bar in stock_data[ticker]]) -
                                  close_price}
            price_calc[ticker].update({"high_diff" : np.array([bar.high for bar in stock_data[ticker]]) -
                                  close_price})
            price_calc[ticker].update({"low_diff" : np.array([bar.low for bar in stock_data[ticker]]) -
                                  close_price})

        # For each simulation
        for _ in range(num_sims):
            # random stock data holds randomized stock data of each simulation
            random_stock_data: dict[str, list[Bar]] = {}

            # Populate each ticker with random stock data
            for ticker in stock_data:
                random_close = self.randomize_price(og_price=list(map(lambda bar:
                                                                    bar.close, stock_data[ticker])),
                                                    mu=mu,
                                                    dt=dt,
                                                    sigma=sigma,
                                                    df=df,
                                                    exp_jumps=exp_jumps,
                                                    mean_log_jump_size=mean_log_jump_size,
                                                    std_log_jump_size=std_log_jump_size,
                                                    is_t=is_t,
                                                    is_reg_switch=is_regime_switching)
                np_random_close = np.array(random_close)
                np_random_open = price_calc[ticker]["open_diff"] + np_random_close
                np_random_high = price_calc[ticker]["high_diff"] + np_random_close
                np_random_low = price_calc[ticker]["low_diff"] + np_random_close
                random_stock_data[ticker] = []

                # Create each bar. TODO Each ticker should have its own timeline
                timeline = self.backtest.data_loader.get_timeline()
                for i in range(len(stock_data[ticker])):
                    random_stock_data[ticker].append(Bar(symbol=ticker,
                                                         date=timeline[i],
                                                         open=np.round(np_random_open[i], 2),
                                                         high=np.round(np_random_high[i], 2),
                                                         low=np.round(np_random_low[i], 2),
                                                         volume=stock_data[ticker][i].volume,
                                                         close=np.round(np_random_close[i], 2),
                                                         asset_type=stock_data[ticker][0].asset_type))
            # Testing
            # test_random_stock_data.append(random_stock_data)
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
                                    data_loader=mcs_data_loader,
                                    asset_type=self.backtest.asset_type,
                                    strength=self.backtest.strength,
                                    slippage=self.backtest.slippage,
                                    initial_capital=self.backtest.initial_capital,
                                    commission=self.backtest.commission,
                                    risk_free_rate=self.backtest.risk_free_rate,
                                    **self.backtest.strategy_params)
            # Stores BackTestResult instances in results
            result.append(mcs_backtest.run())
        # Testing
        # return test_random_stock_data
        return result


