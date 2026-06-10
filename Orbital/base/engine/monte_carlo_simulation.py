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
from scipy.stats import t as student_t
import base.engine.graph as graph

class MonteCarloSimulatior():
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
        return random_open
        # return random_data

    def transform_daily_logged(self, prices: list[float]) -> pd.Series[float]:
        '''
        Takes in a list of prices and returns a list of logged returns. 
        '''
        # First log price then obtains price diff (if log carried after may log a negative)
        logged = map(math.log, prices)
        return pd.Series(logged).diff().dropna()

    def gbm_prices(self, prices: list[float], df: float) -> list[float]:
        '''
        This function takes in a list of prices and returns a list of gbm 
        modified prices

        Implementation details
        Using GBM Formula
        X(t) = X(0) * exp((mu - (sigma^2 / 2)) * t + sigma * B(t))
        Uses mu, sigma, and t in terms of day
        '''

        result = []
        # Obtain X(0)
        initial_price = prices[0]
        logged_returns = self.transform_daily_logged(prices)

        # Obtain sigma and mu
        sigma = logged_returns.std()
        mu = logged_returns.mean()

        # Apply ito correction to mu
        ito_mu = mu - ((sigma**2) / 2)

        # Obtain t
        for t in range(1, len(prices) + 1):

            # Obtain B(t) in formula, using t distribution
            # variance has to be scaled as t distribution variance is dependent on df
            draw = student_t.rvs(df)
            brownian_t = draw / np.sqrt(df / (df - 2))

            # Calculate price and append it
            random_price = round(initial_price * math.exp(ito_mu * t + sigma * brownian_t), 2)
            result.append(random_price)
        # Testing alt gbm
        # result = self.alt_gbm(mu,len(prices),1,1,initial_price,sigma)

        return result

    def alt_gbm(self, mu: float, steps: int, time: int, sims: int,
                initial_price: float, volatility: float) -> list[float]:
        # Calculate each time step
        dt = time / steps

        # Simulation using numpy arrays
        St = np.exp(
            (mu - volatility**2/2) * dt
            + volatility * np.random.normal(0,np.sqrt(dt), size=(sims, steps)).T
        )

        # Include array of 1s
        St = np.vstack([np.ones(sims), St])

        # Multiply through by initial value
        St = initial_price * St.cumprod(axis=0)
        return St


    def simulate(self, num: int, df: float):
        '''
        Takes in a number of simulations and a degree of freedom,
        and returns the result of the simulations.
        '''
        # This is done otherwise scaling will return NaN
        if df <= 2:
            raise ValueError("Degree of freedom must be greater than 2")
        
        stock_data: dict[str, list[Bar]] = self.backtest.data_loader.get_stock_data()
        result = [] # Store BackTestResult of each simulation
        
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
    end_date = datetime.fromisoformat("2021-09-07").date()
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
    mcs = MonteCarloSimulatior(backtest)

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
    # for BackTestResult in MonteCarloSimulatior(backtest).simulate(4):
        # print(type(BackTestResult))
        # print(pd.DataFrame(BackTestResult.get_fill_records()))
        # print("test")

    # For testing of GBM
    # print("This is the original stock data")
    # for num in range(1, len(stock_data) + 1):
    #     print(f"Day{num}: {stock_data[num-1]}")

    # print("\nThis is the randomized stock data")
    # random_data = mcs.GBM(stock_data)
    # for num in range(1, len(random_data) + 1):
    #     print(f"Day{num}: {random_data[num-1]}")

    # Graphical testing of GBM
    # Create a list of price data, with original price data being index 0
    # and the other elemnents being randomized data, display on graph.
    test = [list(map(lambda bar: bar.open, stock_data["AAPL"]))]
    for _ in range(70):
        test.append(mcs.gbm(stock_data["AAPL"], 5))
    graph.show_price_graphs(test).show()

    # Test alternate gbm
    # prices = list(map(lambda bar: bar.open, stock_data["AAPL"]))
    # print(prices)
    # test = mcs.gbm_prices(prices, 5)

    # test = [list(map(lambda bar: bar.open, stock_data))]
    # for _ in range(5):
    #     test.append(mcs.gbm(stock_data, 3))
    # graph.show_price_graphs(test).show()