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
import plotly.graph_objects as go
# from scipy.stats import t as student_t
# from scipy.stats import kurtosis
import base.engine.graph as graph
# from base.engine.distribution import Distribution
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
    ito_mu = logged_returns.mean()
    for _ in range(1, len(prices)):
        # Calculate price and append it
        random_price = round(result[-1] * math.exp(ito_mu), 2)
        result.append(random_price)
    return result

def test_jump_prices(mcs :MonteCarloSimulator, prices: list[float], df: float,
                exp_jumps: int, mean_log_jump_size: float,
                std_log_jump_size: float) -> list[float]:
    '''
    Check if jump diffusion is working as expected
    '''
    return mcs.jump_prices(prices, df, exp_jumps,
                           mean_log_jump_size, std_log_jump_size)

# def test_logged_returns(mcs: MonteCarloSimulator, prices, sims):
#     test = []
#     for _ in range(sims):
#         sim_result = mcs.gbm_prices(prices, 100)
#         test.append(mcs.transform_daily_logged(sim_result))
#     return test

if __name__ == "__main__":
    # Test obtaining og list historical data
    start_date = datetime.fromisoformat("2021-05-24").date()
    end_date = datetime.fromisoformat("2022-05-24").date()
    data_loader = DatabaseDataLoader(Queue(), ["AAPL"], start_date,
                             end_date, "STOCK")
    backtest = Backtest(
                        events=data_loader.events,
                        tickers=["AAPL"],
                        start_date=start_date,
                        end_date=end_date,
                        strategy_name="MovingAverageCross",
                        asset_type="STOCK",
                        short_window=5,
                        long_window=10,
                        data_loader=data_loader)
    backtest.run()
    stock_data = backtest.data_loader.get_stock_data()
    mcs = MonteCarloSimulator(backtest)
    test = mcs.simulate(num_sims=10,
                 mu=0,
                 dt=1,
                 sigma=0,
                 df=5,
                 exp_jumps=2,)
    graph.get_monte_graph(test).show()
    # Graphical Test
    # GBM Price check
    # prices = list(map(lambda bar: bar.open, stock_data["AAPL"]))
    # sigma = mcs.transform_daily_logged(prices).std()
    # ito_mu = mcs.transform_daily_logged(prices).mean()
    # mu = ito_mu + (sigma ** 2 / 2)
    # test_prices = [prices]
    # for _ in range(100):
    #     test_prices.append(mcs.gbm(og_price=prices,mu=mu,dt=1,sigma=sigma,
    #                         epsilon_lst=mcs.get_normal_epsilon_lst(len(prices) - 1)))
    # fig = graph.show_price_graphs(test_prices)
    # fig.data[0].line.color = "black"
    # fig.show()

    # GBM Sanity Check
    # prices = list(map(lambda bar: bar.open, stock_data["AAPL"]))
    # sigma = mcs.transform_daily_logged(prices).std()
    # ito_mu = mcs.transform_daily_logged(prices).mean()
    # mu = ito_mu + (sigma ** 2 / 2)
    # test_prices = [np.log(theoretical_median(mcs, prices))]
    # for _ in range(100):
    #     test_prices.append(np.log(mcs.gbm(og_price=prices,mu=mu,dt=1,sigma=sigma,
    #                         epsilon_lst=mcs.get_normal_epsilon_lst(len(prices) - 1))))
    # fig = graph.show_price_graphs(test_prices)
    # fig.data[0].line.color = "black"
    # fig.show()

    # Analytical Tests
    # Check the mean of the simulated prices and std
    # prices = list(map(lambda bar: bar.close, stock_data["AAPL"]))
    # total_log_return = []
    # for _ in range(10000):
    #     sigma = mcs.transform_daily_logged(prices).std()
    #     ito_mu = mcs.transform_daily_logged(prices).mean()
    #     mu = ito_mu + ((sigma ** 2) / 2)
    #     rand_prices = mcs.gbm(og_price=prices, mu=mu, dt=1, sigma=sigma,
    #             epsilon_lst=mcs.get_normal_epsilon_lst(len(prices) - 1))
    #     # print(f"Initial price {rand_prices[0]}"
    #     #       f"Final price = {rand_prices[-1]}")
    #     total_log_return.append(mcs.transform_daily_logged([rand_prices[0], rand_prices[-1]]))
    # # print(total_log_return)
    # print(f"This is obtained mean = {np.mean(total_log_return)}."
    #       f"This is expected mean = {ito_mu * (len(prices) - 1)}")
    # print(f"This is obtained std = {np.std(total_log_return)}."
    #       f"This is expected std = {sigma * np.sqrt(len(prices) - 1)}")
        # assert np.isclose(np.mean(total_log_return), ito_mu * (len(prices) - 1), rtol=0.05)

    # Test jump_gbm
    # prices = list(map(lambda bar: bar.open, stock_data["AAPL"]))
    # test = [prices]
    # for _ in range(10):
    #     test.append(mcs.gbm(prices, 0.0003, 1, 0.01, mcs.get_t_epsilon_lst(len(prices) - 1, 5),
    #                              3))
    # fig = graph.show_price_graphs(test)
    # fig.data[0].line.color = "black"
    # fig.show()

    # Jump Diffusion Testing
    # Checking if expected number of jumps is achieved
    # Performs as expected, +/- 5% error at 100 sims
    # prices = list(map(lambda bar: bar.close, stock_data["AAPL"]))
    # jump_counts = []
    # for _ in range(100):
    #     sigma = mcs.transform_daily_logged(prices).std()
    #     ito_mu = mcs.transform_daily_logged(prices).mean()
    #     mu = ito_mu + ((sigma ** 2) / 2)
    #     jump_count = mcs.randomize_price(og_price=prices, mu=mu, dt=1, sigma=sigma,
    #                                      exp_jumps=2, df=5)
    #     jump_counts.append(jump_count)
    # print(np.mean(jump_counts))
        
    # Kurtosis testing
    # Note that kurtosis makes use of Fisher such that normal == 0
    # prices = list(map(lambda bar: bar.close, stock_data["AAPL"]))
    # jump_kurtosis = []
    # gbm_kurtosis = []
    # for _ in range(100):
    #     sigma = mcs.transform_daily_logged(prices).std()
    #     ito_mu = mcs.transform_daily_logged(prices).mean()
    #     mu = ito_mu + ((sigma ** 2) / 2)
    #     jump_price = mcs.randomize_price(og_price=prices, mu=mu, dt=1, sigma=sigma,
    #                                      exp_jumps=2, df=5, is_t=False,is_reg_switch=False)
    #     gbm_price = mcs.randomize_price(og_price=prices, mu=mu, dt=1, sigma=sigma,
    #                                      exp_jumps=0, df=5, is_t=False,is_reg_switch=False)     
    #     # assert kurtosis(jump_price) > kurtosis(gbm_price), "Jump prices should have fatter tails"
    #     jump_kurtosis.append(kurtosis(jump_price))
    #     gbm_kurtosis.append(kurtosis(gbm_price))
    # print(f"This is the jump kurtosis = {np.mean(jump_kurtosis)}")
    # print(f"This is the gbm kurtosis = {np.mean(gbm_kurtosis)}")
        




    # Graph check in log space
    # prices = list(map(lambda bar: bar.open, stock_data["AAPL"]))
    # test = [prices]
    # for _ in range(10):
    #     test.append(test_jump_prices(mcs, prices, 5, 1, 0.05, 0.01))
    # test = list(map(lambda prices: map(math.log, prices), test))
    # graph.show_price_graphs(test).show()

    # Creating comparison between GBM and Jump Diffusion
    # prices = list(map(lambda bar: bar.open, stock_data["AAPL"]))
    # test = [prices]
    # # Index 1 to 10 are GBM
    # for _ in range(1):
    #     test.append(mcs.gbm_prices(prices, 5))
    # # Index 11 to 20 are Jump Diffusion
    # for _ in range(1):
    #     test.append(test_jump_prices(mcs, prices, 5, 2, 0.5, 0.01))
    # fig = graph.show_price_graphs(test)
    # for i in range(3):
    #     if i == 0:
    #         fig.data[i].line.color = "black"

    #     elif i >= 1 and i <= 1:
    #         fig.data[i].line.color = "red"
    #     else:
    #         fig.data[i].line.color = "green"
    # fig.show()

    # Test Regime Switching 

    # Testing random price
    # prices = list(map(lambda bar: bar.open, stock_data["CRWD"]))
    # test = [prices]
    # for i in range(100):
    #     test.append(mcs.randomize_price(prices, 0.05, 1, 0.01, 5, 2))
    # fig = graph.show_price_graphs(test)
    # fig.data[0].line.color = "black"
    # fig.show()

    # Testing of model
    # prices = list(map(lambda bar: bar.open, stock_data["AAPL"]))
    # test = mcs.get_model(prices)
    # print(test)
    # print(f"This is the variances {test.covars_[1][0][0]}")
    # print(f"This is the means {test.means_}")
    # covars and mean has form [[[x]], [[y]]]
    # print(f"This is the shape of transmat{test.transmat_}")
    # Shape is [[x1, x2], [y1, y2]]

    # Test if simulate creates random stock prices
    # random_prices = mcs.simulate(num_sims=3,mu=0.01,dt=1,sigma=0.01,df=5)
    # graph.get_ohlv_graph(random_prices[0]["AAPL"]).show()
    # graph.get_ohlv_graph(random_prices[1]["AAPL"]).show()
    # graph.get_ohlv_graph(random_prices[2]["AAPL"]).show()

    # Check if equity graphs are created for each simulated result
    # simulations = mcs.simulate(num_sims=3,mu=0.01,dt=1,sigma=0.01,df=5)
    # fig_lst = []
    # for backtestresult in simulations:
    #     fig_lst.append(backtestresult.get_equity_graph())
    
    # overlay_fig = go.Figure()
    # for fig in fig_lst:
    #     for trace in fig.data:
    #         overlay_fig.add_trace(trace)
    # overlay_fig.show()

    # Some random testing
    # test = mcs.backtest.data_loader.get_past_bars("AAPL", 100)
    # print(test)



