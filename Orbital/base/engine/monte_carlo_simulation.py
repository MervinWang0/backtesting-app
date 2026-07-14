import os
import sys
import django
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Orbital.settings")
django.setup()

from abc import ABC, abstractmethod
from queue import Queue
from datetime import datetime
from base.engine.data_loader import (DataLoader, Bar,
                                     DatabaseDataLoader,
                                     MCSDataLoader)
from base.engine.distribution import Distribution
from base.engine.backtest import Backtest, BacktestResult
import numpy as np
import math
from scipy.stats import t as student_t
from scipy.stats import poisson as poisson
from scipy.stats import norm as normal
from hmmlearn import hmm
from functools import wraps
from time import time
import pandas as pd

def timed(f):
    '''
    This function is used to time any function
    Usage syntax
    @timed
    def funct()
    '''

    @wraps(f)
    def wrapper(*args, **kwds):
        start = time()
        result = f(*args, **kwds)
        elapsed = time() - start
        print(f"function {f.__name__} took {elapsed}")
        return result
    return wrapper

def transform_daily_logged(prices: list[float]) -> np.array:
    '''
    Takes in a list of prices and returns a list of logged returns. 
    '''
    return np.diff(np.log(prices))

class MonteCarloSimulator():
    '''
    This class carries out simulated backtests and returns metrics computed from them.

    Features
    1. Price randomization making use of PriceSimulator
    2. Execution of backtest using DatabaseDataloader

    Methods 

    '''
    def __init__(self, backtest: Backtest):
        self.backtest = backtest

    
    @timed
    def simulate(self, num_sims: int, df: float = 5, exp_jumps: int = 0, mean_log_jump_size: float = 0.05,
                 std_log_jump_size: float = 0.01, is_t: bool = True,is_regime_switching: bool = True,
                 is_jump_diffusion: bool = True, **kwargs) -> list[BacktestResult]:
        '''
        Takes in various simulation metrics, returns two outputs, 
        1. A list of BacktestResults, len <= 101, representing first 100 simulated paths
        2. A 2d numpy array representing computed metrics
        '''
        # Stock data holds each ticker's stock info for backtest's tickers
        stock_data: dict[str, list[Bar]] = self.backtest.data_loader.get_stock_data()

        # Store BackTestResult of each simulation, 
        # graph_result stores first 100 btr for graphing
        # metric_result stores the get_metric of each btr
        btr = self.backtest.run()
        graph_result = [btr]
        fields = btr.get_metrics().keys()
        print(f"These are the metric fields of a backtest result {fields}")
        metric_result = {name : np.empty(num_sims) for name in fields}

        

        # Create price simulator
        # TODO Doesn't actually support multi stock MCS currently
        for ticker in stock_data:
            # Close price of current stock
            close_price = [bar.close for bar in stock_data[ticker]]

            # Initialize some default parameters used for randomizing prices
            jump_component = None
            regime_component = None
            t_component = None

            if is_jump_diffusion:
                jump_component = JumpComponent(exp_jumps=exp_jumps,
                                        mean_log_jump_size=mean_log_jump_size,
                                        std_log_jump_size=std_log_jump_size)
            if is_regime_switching:
                regime_component = RegimeComponent(prices=close_price)
            if is_t:
                t_component = TComponent(df=df)

            # Create a Price Simulator to randomize the close price
            price_simulator = GBMPriceSimulator(prices=close_price, JumpComponent=jump_component,
                                                RegimeComponent=regime_component,
                                                TComponent=t_component)

        # For each simulation
        for sim_count in range(num_sims):
            # random stock data holds randomized stock data of each simulation
            random_stock_data: dict[str, list[Bar]] = {}
            random_close = price_simulator.randomize_price()

            # Populate each ticker with random stock data
            for ticker in stock_data:
                # Create each bar. TODO Each ticker should have its own timeline
                timeline = self.backtest.data_loader.get_timeline()
                random_stock_data[ticker] = self.price_to_bar(stock_data[ticker],
                                                              random_close_prices=random_close,
                                                              timeline=timeline)

            # Once the random historical stock data is obtained, backtest using it
            # Stores first 100 BackTestResult for graphing, and the stores metrics for rest
            simulated_backtest = self.run_backtest(random_stock_data=random_stock_data)
            # Cap the total graphs stored for memory efficiency and because plotting a high
            # number of graphs is very slow.
            if len(graph_result) < 101:
                graph_result.append(simulated_backtest)
            simulated_metrics = simulated_backtest.get_metrics()
            # Iterate through fields and update metric result with simulated result
            for name in fields:
                metric_result[name][sim_count] = simulated_metrics[name]
        print("These are the metrics of the backtest")
        print(pd.DataFrame(metric_result))
        
        # Convert Obtain distribution results of simulation
        metric_lst: list[dict[str, float]] = []
        for name in fields:
            dist = Distribution(metric_result[name])
            dist_metrics = {"Field" : name}
            dist_metrics.update(dist.get_imp_metrics())
            metric_lst.append(dist_metrics)
        # print("These are the computed distributions")
        # print(pd.DataFrame(metric_lst))
        return (graph_result, metric_lst)

    def price_to_bar(self, og_data: list[Bar], random_close_prices: list[float],
                     timeline: list[datetime.date]) -> list[Bar]:
        ''' 
        Takes in the original stock data, and the randomized price. Returns 
        a list of new bars. 
        
        This function works by computing the relative difference between open-close,
        high-close, and so on. Then re-applying this difference to the randomize close prices.
        '''

        # Obtain relative difference between the various OHLC data
        close_price = np.array([bar.close for bar in og_data])
        price_calc = {}
        price_calc = {"open_diff" :
                np.array([bar.open for bar in og_data]) / close_price}
        price_calc.update({"high_diff" :
                np.array([bar.high for bar in og_data]) / close_price})
        price_calc.update({"low_diff" :
                np.array([bar.low for bar in og_data]) / close_price})

        # Re apply the relative differences
        np_random_open = price_calc["open_diff"] * random_close_prices
        np_random_high = price_calc["high_diff"] * random_close_prices
        np_random_low = price_calc["low_diff"] * random_close_prices 

        ticker = og_data[0].symbol
        asset_type = og_data[0].asset_type
        random_stock_data = [
                        Bar(symbol=ticker,
                            date=timeline[i],
                            open=np.round(np_random_open[i], 2),
                            high=np.round(np_random_high[i], 2),
                            low=np.round(np_random_low[i], 2),
                            volume=og_data[i].volume,
                            close=np.round(random_close_prices[i], 2),
                            asset_type=asset_type)
                            for i in range(len(og_data))]
        return random_stock_data
    
    @timed
    def run_backtest(self, random_stock_data: list[Bar]) -> any:
        ''' 
        This function is just to seperate the execution of the backtest with randomized
        data from simulate function
        '''
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
                                is_mcs=self.backtest.is_mcs,
                                **self.backtest.strategy_params)
        return mcs_backtest.run()

class Component(ABC):
    ''' 
    Components are classes that take in params, and have one method,
    apply
    
    apply takes in a 2D array of simulation params, and applied changes to them
    '''

    @abstractmethod
    def apply(self,params: np.array) -> np.array:
        ''' 
        Takes in a 2d param array, changes one or more of the columns
        '''

class PriceSimulator(ABC):
    '''
    This is a base class inherited by GBMPriceSimulator and other
    PriceSimulators Like HestonPriceSimulator.
    
    Note each instance can only simulate one price path, to simulate more,
    create other instances (This is done because RegimeSwitching has
    different mu and sigma params for each price path)
    '''

    @abstractmethod
    def randomize_price(self) -> np.array:
        ''' 
        Should take in T/F of various factors
        '''
    
class GBMPriceSimulator(PriceSimulator):
    ''' 
    This class randomizes price using a GBM method, affected by factors like
    Jump, Regime, T dist.
    '''

    def __init__(self, prices:list[float], JumpComponent=None, TComponent=None,
                 RegimeComponent=None,):
        self.prices = prices

        # Get mu and sigma from historical data, will be overriden by components if passed
        mu_and_sigma = self.get_historical_mu_sigma()
        self.mu = np.full(len(prices), mu_and_sigma[0])
        self.sigma = np.full(len(prices), mu_and_sigma[1])

        # Note that epsilon has to be created each time in randomize price, otherwise
        # It will not be a random draw each time
        self.epsilon = np.full(len(prices), 0)
        self.jump_contribution = np.full(len(prices), 0)

        # These objects are used to apply various changes to params
        self.jump_component = JumpComponent
        self.t_component = TComponent
        self.regime_component = RegimeComponent

        # Params is a 2d array containing mu, sigma, epsilon, jump_contribution.
        # The parameters necessary to create list of randomized log returns
        self.params = np.array([])

    # @timed
    def gbm(self, dt: float = 1) -> np.array:
        ''' 
        This function carries out the gbm process, I seperated it to make it modular 
        and easier to error check.
        '''
        # Reference the columns of the 2D array
        mu = self.params[:, 0]
        sigma = self.params[:, 1]
        epsilon = self.params[:, 2]
        jump_contribution = self.params[:, 3]
        # Carry out GBM Formula, note that jump_contribution does not work with non 1 dt currently
        return mu * dt + sigma * np.sqrt(dt) * epsilon + jump_contribution

    @timed
    def randomize_price(self) -> np.array:
        ''' 
        Takes in a list of prices. E.g. list of close prices.
        Generates a list of randomized close prices.
        '''
        # Epsilon is calculated here to ensure each randomzie price has a
        # different epsilon array
        self.epsilon = np.random.normal(size=len(self.prices))
        self.params = np.column_stack([self.mu, self.sigma, self.epsilon,
                                 self.jump_contribution])

        # Applies changes to params based on various factors
        if self.t_component:
            self.params = self.t_component.apply(self.params, self.prices)
        if self.regime_component:
            self.params = self.regime_component.apply(self.params, self.prices)
        # Jump component has to be added after regime switching as they both modify mu
        if self.jump_component:
            self.params = self.jump_component.apply(self.params, self.prices)

        # Testing
        # print(pd.DataFrame(self.params))
        # print(f"The jump contribution should not be 0 = {self.params[:, 3].sum()}")

        # Obtain randomzed daily change in prices (log form). Such that
        # The cum_sum represent logged change up to that day. Exponentiate to get actual change
        random_logged_returns = self.gbm()
        # print(f"This is the multiplier to initial price {np.exp(random_logged_returns.cumsum())}")
        random_prices = (self.prices[0] * np.exp(random_logged_returns.cumsum())).tolist()
        # print(random_prices)
        random_prices.insert(0, self.prices[0])

        # random_prices needs to have its last element be removed as index 0 = og unchanged
        # index [-1] should refer to n-1 day not n dath
        random_prices.pop()
        return random_prices

    def get_historical_mu_sigma(self) -> tuple[float, float]:
        ''' 
        Uses historical prices to calculate mu and sigma. These are static.

        Note the tuple is of form (mu, sigma)
        '''
        logged_returns = transform_daily_logged(self.prices)

        # Note that the mu here already has ito correction applied to it
        mu = logged_returns.mean()
        sigma = logged_returns.std()
 
        return (mu, sigma)

class JumpComponent():
    ''' 
    This class stores the jump params, and contains a method to apply the jump
    factors to the randomize prices params
    '''
    def __init__(self, exp_jumps: int = 0, mean_log_jump_size: float = 0.05,
                 std_log_jump_size: float = 0.01):
        self.exp_jumps = exp_jumps
        self.mean_log_jump_size = mean_log_jump_size
        self.std_log_jump_size = std_log_jump_size

        # Testing
        self.jump_count = 0

    def apply(self, param: np.array, prices: list[float]) -> np.array:
        ''' 
        The mu and jump contribution of params should be modified
        '''
        # Jump params
        lambda_j = self.exp_jumps
        lambda_j = lambda_j / 252 # Make it daily
        # print(f"Expected number of jumps yearly, {self.exp_jumps}"
        #       f"Expected number of jumps daily, {lambda_j}")
        expected_jump_size = math.exp(self.mean_log_jump_size + self.std_log_jump_size**2 / 2) - 1
        jump_contribution_lst = []

        # Apply correction to mu Equivalent to (μ − σ²/2 − λk) 
        # Where mu is arithmetic price drift, mu without ito correction
        param[:, 0] = param[:, 0] - lambda_j * expected_jump_size

        # Create jump contribution list
        for _ in range(len(prices)):
            jumps = poisson.rvs(mu=lambda_j)
            jump_draws = np.random.normal(loc=self.mean_log_jump_size,
                                          scale=self.std_log_jump_size, size=jumps)
            jump_contribution_lst.append(jump_draws.sum())

            # Testing
            # print(jumps)
            # print(f"This is the length of prices {len(prices)}\n")
            # print(f"This is the jump count so far {self.jump_count}")
            self.jump_count += jumps

        # print(f"This is the jump count so far {self.jump_count}")
        # Add jump_contribution column to param
        param[:, 3] = np.array(jump_contribution_lst)
        return param

class RegimeComponent():
    '''
    This class contains the params for regime switching and a method that
    applies the regime switching to the gbm params.
    '''
    def __init__(self, prices: list[float]):
        self.prices = prices
        self.regimes = ["LOW", "HIGH"]
        self.model = self.get_model()
        # self.high_time = 0
        # print("Model is created, should only occur once for each ticker")

    # Regime params
    def apply(self, params, prices: list[float]) -> np.array:
        ''' 
        This function changes the mu and sigma of the param
        '''
        # sample returns observations, states. Observations is not required
        _, regime_lst = self.model.sample(len(self.prices))
        # print(regime_lst)
        # print(f"This is the regime_lst = {regime_lst}")
        
        # Note that mu already has ito mu baked into it
        mu = np.array([self.model.means_[state] for state in regime_lst]).squeeze()
        
        # The variance has to be sqrted to get sigma
        sigma = np.array([np.sqrt(self.model.covars_[state]) for state in regime_lst]).squeeze()
        
        # Testing
        # print(f"This is the mu array {mu}")
        # print(f"This is the sigma array {sigma}")
        # self.high_time += sum(regime_lst) / len(regime_lst)
        # print(f"This is the time spent in high state {sum(regime_lst) / len(regime_lst)}")
        
        # Change params and return it
        params[:, 0] = mu
        params[:, 1] = sigma
        # print(f"This is the params\n{pd.DataFrame(params)}\n")
        return params


    def get_model(self) -> hmm.GaussianHMM:
        '''
        Takes in a list of prices and returns a sorted model from the prices
        '''
        return self.model_sort(self.create_model())

    def create_model(self) -> hmm.GaussianHMM:
        '''
        Creates a model
        random_state is set such that all transition matrixes, on the same data are the same.
        '''
        model = hmm.GaussianHMM(n_components=2, covariance_type="full", n_iter=1000)
        # Turn the prices into a 2D array, each row representing day, and column is log return
        data = np.array(transform_daily_logged(self.prices)).reshape(-1,1)
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

class TComponent():
    ''' 
    This class takes in one param, df, and changes epsilon in params
    '''
    def __init__(self, df: float = 5):
        '''
        Note that if df <= 2 There will be an error 
        '''
        if df <= 2:
            raise ValueError("Degree of Freedom must be greater than 2. This Occured in TComponent")
        self.df = df

    def apply(self, params: np.array, prices: list[float]) -> np.array:
        ''' 
        This function creates an epsilon list using t distribution and passes it to param
        '''
        params[:, 2] = self.get_t_epsilon_lst(size=len(prices), df=self.df)
        return params

    def get_t_epsilon_lst(self, size: int, df: float) -> np.array:
        '''
        Returns len epsilon draws of a t dist scaled
        '''
        if df <= 2:
            raise ValueError("df must be greater than 2")
        epsilon_lst_raw = student_t.rvs(df=df, size=size)
        return np.array(epsilon_lst_raw) / np.sqrt(df / (df - 2))
