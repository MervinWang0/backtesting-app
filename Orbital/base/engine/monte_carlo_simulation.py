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
import pandas as pd
import math

class MonteCarloSimulatior():
    '''
    Low
    Medium
    High
    Extreme 
    beta metric 
    Monte Carlo Simulation should be a subclass of Backtest

    Using a Market Noise Simulation Approach
    Adding noise to price
    1. Modify historical data
    2. Run Backtest
    3. Obtain metrics
    4. Repeat 1-3

    The noise added to price should not be a fixed percentage but
    calibrated from historical data of stock. 
    1. Obtain list of historical returns
    2. Obtain returns.std() => represents how much price of stock changes
    day to day
    3. Multiple std by volatility and rng. Use this to modify each day's price

    Which is then multiplied by a rng and volatility scaling

current return = (close price today - close price yesterday) / close price yesterday.
    '''
    def __init__(self, backtest: Backtest, volatility_regime):
        self.backtest = backtest
        self.volatility = self.get_volatility(volatility_regime)

    def GBM(self, stock_data: list[Bar]) -> list[Bar]:
        '''
        Description 
        Function takes in a list of stock prices and returns a randomized list
        of stock prices

        Implementation details
        Geometric Brownian Motion is a method of generating random stock prices.
        Note that for GBM, drift and volatility are constant throughout the period.

        It has the formula (before ito correction)
        X(t) = X(0) * nat_exp(mu * t + sigma * B(t))

        Variables explanation
        X(t) price of stock at day t
        X(0) initial price of stock
        mu => drift => annualized sample mean of logged daily returns 
        t => day => fraction of year, n/252, where n is the day of the stock (0 is first day)
        sigma => volatility => annualized std of logged daily returns
        B(t) => Brownian motion evaluated at t => equivalent to N(0, t)

        GBS with Ito correction, (more accurate)
        X(t) = X(0) * nat_exp((mu - (sigma^2 / 2)) * t + sigma * B(t))
        The difference is that mu has a subtraction of sigma squared divided by 2

        Function takes in a list of og stock prices and returns a randomized list
        of stock prices
        '''
        # There are two attributes important in a bar, open and close.
        # Both are to be modified
        random_data: list[Bar] = [] # Stores randomized data

        # First obtain a list containing open prices and close prices
        open_log = list(map(lambda bar: bar.open, stock_data))
        close_log = list(map(lambda bar: bar.close, stock_data))

        # important to note that these logged returns have 1 less element than the
        # original list.
        open_logged_returns = self.transform_daily_logged(open_log)
        close_logged_returns = self.transform_daily_logged(close_log)

        # Obtain X(0)
        open_initial = stock_data[0].open
        close_initial = stock_data[0].close

        # random number generator used to calculate brownian motion
        rng = np.random.default_rng()

        # This loop applies the GBM change to each day's stock data
        for day, bar in enumerate(stock_data): # day = [0, len(stock_data) - 1]
            # Obtain t in formula
            t = day / 252

            # Obtain B(t) in formula
            # The second argument to normal is standard deviation while t is variance
            # thus sqrt. Note std and var is for brownian motion not GBM
            brownian_t = rng.normal(0, math.sqrt(t))

            # Obtain sigma annualized
            open_sigma = open_logged_returns.std() * 252
            close_sigma = close_logged_returns.std() * 252

            # Obtain mu annualized
            # With iso correction, note mean is annualized first before correction
            # is applied using annualized sigma
            open_mu = (open_logged_returns.mean() * 252) - (open_sigma ** 2) / 2
            close_mu = (close_logged_returns.mean() * 252) - (close_sigma ** 2) / 2

            # Add a random bar for each day in the og stock data in results list
            random_open_price = open_initial * math.exp(open_mu * t + open_sigma * brownian_t)
            random_close_price = close_initial * math.exp(close_mu * t + close_sigma * brownian_t)
            random_data.append(Bar(symbol=bar.symbol,
                                   date=bar.date,
                                   open=round(random_open_price, 2),
                                   high=bar.high,
                                   low=bar.low,
                                   close=round(random_close_price, 2),
                                   volume=bar.volume,
                                   asset_type=bar.asset_type
                                   ))
        return random_data




    def transform_daily_logged(self, values: list[float]) -> pd.Series[float]:
        '''
        Takes in a list of values, representing prices and returns a list
        of the daily returns logged by the natural log
        '''
        # First log price then obtains price diff (if log carried after may log a negative)
        logged = map(math.log, values)
        return pd.Series(logged).pct_change().dropna()


    def simulate(self, num):
        '''
        Runs num simulations where num >= 1
        '''
        # Need to implement a method to get all bars of all stocks
        # of the data loader
        stock_data: dict[str, list[Bar]] = {"AAPL" : self.backtest.data_loader.get_past_bars("AAPL",
            len(self.backtest.data_loader.get_timeline()))}

        # results is a list storing the equity records of each run
        results = []

        # For each simulation
        for _ in range(num):
            # random stock data holds randomized stock data of each simulation
            random_stock_data: dict[str, list[Bar]] = {}
            # This creates the random data using GBM method
            for ticker in self.backtest.tickers:
                random_stock_data[ticker] = self.GBM(stock_data["AAPL"])

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
            results.append(mcs_backtest.run())
        return results


    def get_volatility(self, volatility_regime: str) -> float:
        '''
        Takes in a string representing a volatility regime and returns the scaling factor
        '''
        if volatility_regime == "LOW":
            return 0.5
        if volatility_regime == "MEDIUM":
            return 1
        if volatility_regime == "HIGH":
            return 2
        if volatility_regime == "CRISIS":
            return 4
        raise ValueError("Volatility regime should be of LOW/MEDIUM/HIGH/CRISIS")

    def get_returns_std(self, stock_data: list[Bar]) -> list[float]:
        '''
        Descrpition
        Helper method that transforms a list of historical stock data (bars)
        Into a list of floats, representing the percentage change for each day
        and then into a single float, representing std of the list.
        '''
        # store a list of returns in prices
        prices = []
        for bar_ in stock_data:
            prices.append(bar_.close)

        prices = pd.Series(prices)
        # Gets returns. Drops the first element as it can't be calculated
        prices = prices.pct_change().dropna()
        return np.std(prices)

if __name__ == "__main__":
    # Test obtaining og list historical data
    start_date = datetime.fromisoformat("2021-05-24").date()
    end_date = datetime.fromisoformat("2022-06-07").date()
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
    stock_data = backtest.data_loader.get_past_bars("AAPL",
                len(backtest.data_loader.get_timeline()))
    mcs = MonteCarloSimulatior(backtest, "LOW")

    # Tests if the list of bars can be obtained via backtester
    # n = 1
    # for bar in MonteCarloSimulatior(backtest,1).simulate(1):
    #     print(f"This is the bar on Day {n} = {bar}\n")
    #     n += 1
    # Successfully tested that historical returns list is obtained
    # print(f"This is the historical returns {MonteCarloSimulatior(backtest,"LOW").simulate(1)}")

    # Testing to see if returns std works
    # print(f"This is the returns std = {MonteCarloSimulatior(backtest,1).simulate(1)}")

    # Testing to see if monte carlo simulation successfully runs the backtests
    # print(f"This is the random stock data = {MonteCarloSimulatior(backtest,"LOW").simulate(3)}")

    # Attempt to make the list of equity records into a more readable format
    for equity_record in MonteCarloSimulatior(backtest,"LOW").simulate(3):
        print(pd.DataFrame(equity_record))

    # For testing of GBM
    # print("This is the original stock data")
    # for num in range(1, len(stock_data) + 1):
    #     print(f"Day{num}: {stock_data[num-1]}")

    # print("\nThis is the randomized stock data")
    # random_data = mcs.GBM(stock_data)
    # for num in range(1, len(random_data) + 1):
    #     print(f"Day{num}: {random_data[num-1]}")


