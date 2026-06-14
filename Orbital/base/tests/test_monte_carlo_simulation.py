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
import base.engine.graph as graph
from base.engine.distribution import Distribution
from base.engine.monte_carlo_simulation import MonteCarloSimulator

def test_gbm_prices(mcs, prices: list[float], df, tests) -> list[list[float]]:
    '''
    Used to check if the gbm produces the expected result.
    That the logged return of the prices scatter around
    the theoretical mean.
    '''
    test = [theoretical_median(mcs, prices)]
    for _ in range(tests):
        test.append(mcs.gbm_prices(prices, df))
    test_logged = list(map(lambda price: list(np.log(price)), test))
    return test_logged

def theoretical_median(mcs, prices: list[float]) -> list[float]:

    '''
    Takes in a list of prices and produces the theoretical median prices
    generated. Which is equivalent to using GBM but without epsilon.
    Note this median refers to log space.
    '''
    result = [prices[0]]
    logged_returns = mcs.transform_daily_logged(prices)

    # Obtain sigma and mu
    sigma = logged_returns.std()
    mu = logged_returns.mean()

    # Apply ito correction to mu
    ito_mu = mu - ((sigma**2) / 2)
    for _ in range(1, len(prices)):
        # Calculate price and append it
        random_price = round(result[-1] * math.exp(ito_mu), 2)
        result.append(random_price)
    return result


if __name__ == "__main__":
    # Test obtaining og list historical data
    start_date = datetime.fromisoformat("2021-05-24").date()
    end_date = datetime.fromisoformat("2021-07-07").date()
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
    # Sanity check, graph check
    prices = list(map(lambda bar: bar.open, stock_data["AAPL"]))
    test_prices = test_gbm_prices(mcs, prices, 5, 100)
    graph.show_price_graphs(test_prices).show()