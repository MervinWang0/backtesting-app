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
from base.engine.data_loader import DataLoader, Bar
from base.engine.backtest import Backtest
import numpy as np
import pandas as pd

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
    
    def simulate(self, num):
        '''
        Runs num simulations where num >= 1
        '''
        # Calculate parameters for price noise
        og_stock_data = self.backtest.data_loader.get_past_bars("AAPL",
                        len(self.backtest.data_loader.get_timeline()))
        returns_std = self.get_returns_std(og_stock_data)
        rng = np.random.default_rng()

        # For each simulation
        for _ in range(num):
            # Create list to store random stock data 
            random_stock_data = []
            # For each record
            for bar in og_stock_data:
                # Each day is affected by a different price noise
                price_noise = rng.normal(0, returns_std * self.volatility)
                # Only Close and Open are modified
                random_stock_data.append(Bar(symbol=bar.symbol,
                                             date=bar.date,
                                             open=(bar.open) * (1 + price_noise),
                                             high=bar.high,
                                             low=bar.low,
                                             close=(bar.close) * (1 + price_noise),
                                             volume=bar.volume,
                                             asset_type=bar.asset_type))
                



    
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

        # Get std of prices
        prices = pd.Series(prices)
        # Drops the first element as it can't be calculated
        prices = prices.pct_change().dropna()
        return np.std(prices)
    
if __name__ == "__main__":
    # Test obtaining og list historical data
    start_date = datetime.fromisoformat("2021-05-24").date()
    end_date = datetime.fromisoformat("2021-06-07").date()
    data_loader = DataLoader(Queue(), ["AAPL"], start_date,
                             end_date, "STOCK")
    backtest = Backtest(
    events=Queue(),
    tickers=["AAPL"],
    start_date=start_date,
    end_date=end_date,
    strategy_name="MovingAverageCross",
    strength=1.0,
    slippage=0.0,
    initial_capital=100000.0,
    strategy_params={
        "short_window": 20,
        "long_window": 100,
    },
    commission=0.0)
    backtest.run()
    # Tests if the list of bars can be obtained via backtester
    # n = 1
    # for bar in MonteCarloSimulatior(backtest,1).simulate(1):
    #     print(f"This is the bar on Day {n} = {bar}\n")
    #     n += 1
    # Successfully tested that historical returns list is obtained
    print(f"This is the historical returns {MonteCarloSimulatior(backtest,1).simulate(1)}")
    
    # Testing to see if returns std works
    # print(f"This is the returns std = {MonteCarloSimulatior(backtest,1).simulate(1)}")

