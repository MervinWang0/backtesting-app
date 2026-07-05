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
from base.engine.monte_carlo_simulation import (MonteCarloSimulator,
                GBMPriceSimulator, JumpComponent, RegimeComponent,
                TComponent)
from scipy import stats

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
    # mcs = MonteCarloSimulator(backtest)
    # test = mcs.simulate(num_sims=10,
    #              mu=0,
    #              dt=1,
    #              sigma=0,
    #              df=5,
    #              exp_jumps=2,)
    # graph.get_monte_graph(test).show()

# ----------------------------------------------------------------------------------------------- #
    # Testing Refactored MCS -> Checking self.params is 2d numpy array
# ----------------------------------------------------------------------------------------------- #
    # prices = list(map(lambda bar: bar.open, stock_data["AAPL"]))
    # price_simulator = GBMPriceSimulator(prices=prices)
    # print("This should be a 2D array of parameters, "
    #       "Where each row represents a day, and each column the mu, sigma, "
    #       "and so on of that day")
    # # Converting to pandas for readability
    # df = pd.DataFrame(price_simulator.params, columns=["mu", "sigma", 'epsilon',
    #                                                    'jump contribution'])
    # print(df)
# ----------------------------------------------------------------------------------------------- #
    # Testing Refactored MCS -> Graphical display of gbm prices
# ----------------------------------------------------------------------------------------------- #
    # prices = list(map(lambda bar: bar.open, stock_data["AAPL"]))
    # price_simulator = GBMPriceSimulator(prices=prices)
    # print("Generating a random price graph")
    # results = []
    # for _ in range(100):
    #     results.append(price_simulator.randomize_price())
    # fig = graph.show_price_graphs(results)
    # fig.show()
    # print(results)
# ----------------------------------------------------------------------------------------------- #
    # Testing Refactored MCS -> Analytical test of GBM
    # Terminal Price check. log of terminal prices should be normal Success
    # Note that p value higher does not automatically mean more correct 0.99 would indicate
    # lack of randomness
# ----------------------------------------------------------------------------------------------- #
    # prices = list(map(lambda bar: bar.open, stock_data["AAPL"]))
    # price_simulator = GBMPriceSimulator(prices=prices)
    # result = []
    # for _ in range(100):
    #     result.append(price_simulator.randomize_price())

    # terminal_prices = np.array([price_path[-1] for price_path in result])
    # log_terminal = np.log(terminal_prices / price_simulator.prices[0])

    # # Should be approximately normal
    # stat, p_value = stats.shapiro(log_terminal)  # or stats.normaltest
    # print(f"p-value: {p_value}")  # want p > 0.05 to NOT reject normality
# ----------------------------------------------------------------------------------------------- #
    # Testing Refactored MCS -> Analytical test of GBM
    # Test that mu and sigma converge to expected values Success
# ----------------------------------------------------------------------------------------------- #
    # prices = list(map(lambda bar: bar.open, stock_data["AAPL"]))
    # price_simulator = GBMPriceSimulator(prices=prices)
    # result = []
    # for _ in range(10000):
    #     result.append(price_simulator.randomize_price())

    # mu_and_sigma = price_simulator.get_historical_mu_sigma()
    # mu = mu_and_sigma[0]
    # sigma = mu_and_sigma[1]

    # terminal_prices = np.array([price_path[-1] for price_path in result])
    # log_terminal = np.log(terminal_prices / price_simulator.prices[0])

    # expected_mean = mu * len(price_simulator.prices)
    # expected_var = sigma ** 2 * len(price_simulator.prices)

    # sample_mean = log_terminal.mean()
    # sample_var = log_terminal.var(ddof=1)

    # print(f"Expected mean: {expected_mean:.4f}, Sample mean: {sample_mean:.4f}")
    # print(f"Expected var: {expected_var:.4f}, Sample var: {sample_var:.4f}")
# ----------------------------------------------------------------------------------------------- # 
    # Testing Refactored MCS -> Analytical test of GBM
    # Tests if gbm performs as expected when sigma is 0.
    # GBM simulated price at day t, St, should be equivalent to S0 * exp(raw mu * t) Success
# ----------------------------------------------------------------------------------------------- #
    # prices = list(map(lambda bar: bar.open, stock_data["AAPL"]))
    # deterministic_price_simulator = GBMPriceSimulator(prices)

    # # Obtain theoretical results first
    # mu_and_sigma = deterministic_price_simulator.get_historical_mu_sigma()
    # mu = mu_and_sigma[0]
    # sigma = mu_and_sigma[1]
    # raw_mu = mu + 0.5 * (sigma**2)

    # # Set sigma to 0, and mu to raw mu
    # deterministic_price_simulator.randomize_price()
    # print(deterministic_price_simulator.params)
    # deterministic_price_simulator.params[:, 1] = np.full(len(prices), 0)
    # deterministic_price_simulator.params[:, 0] = np.full(len(prices), raw_mu)
    

    # theoretical_price = []
    # for t in range(len(prices)):
    #     # print("This should be change per day")
    #     # print(raw_mu * t)
    #     theoretical_price.append(prices[0] * np.exp(raw_mu * t))

    # result = []
    # for _ in range(1):
    #     random_logged_returns = deterministic_price_simulator.gbm()
    #     # print("std should be 0")
    #     # print(random_logged_returns.std())
    #     # print(f"This should match the changes per day {random_logged_returns.cumsum()}")
    #     random_prices = (deterministic_price_simulator.prices[0] *
    #                      np.exp(random_logged_returns.cumsum())).tolist()
    #     random_prices.insert(0, deterministic_price_simulator.prices[0])
    #     result.append(random_prices)

    # # print(f"This is the theoretical price {theoretical_price}\n")
    # # print(f"This is the simulated price {result}\n")
    # np.testing.assert_allclose(result, np.array(theoretical_price))

# ----------------------------------------------------------------------------------------------- # 
    # Jump Diffusion Testing -> Testing if expected number of jumps is achieved Success
# ----------------------------------------------------------------------------------------------- #
    # # Jump Diffusion Testing
    # # Checking if expected number of jumps is achieved
    # # Performs as expected, +/- 5% error at 100 sims
    # prices = list(map(lambda bar: bar.close, stock_data["AAPL"]))
    # jump_counts = []
    # price_simulator = GBMPriceSimulator(prices, JumpComponent=JumpComponent(exp_jumps=2))
    # for _ in range(1000):
    #     price_simulator.randomize_price()
    # print(f"Expected jump count = 2, Actual value = {price_simulator.jump_component.jump_count / 1000}")

# ----------------------------------------------------------------------------------------------- #
    # Testing to see list of states created by regime switching model
# ----------------------------------------------------------------------------------------------- #
    # prices = list(map(lambda bar: bar.close, stock_data["AAPL"]))
    # regime_component = RegimeComponent(prices)
    # # Model if sorted correctly, 1 should correspond to high and 0 to low vol regime
    # regime_component.apply(prices)
# ----------------------------------------------------------------------------------------------- #
    # Testing to see if the number of each state is correct -> Checks stationary distribution
    # Success
# ----------------------------------------------------------------------------------------------- # 
    # prices = list(map(lambda bar: bar.close, stock_data["AAPL"]))
    # regime_component = RegimeComponent(prices)
    # price_simulator = GBMPriceSimulator(prices, RegimeComponent=regime_component)
    # eigenvalues, eigenvectors = np.linalg.eig(regime_component.model.transmat_.T)
    # stationary = eigenvectors[:, np.isclose(eigenvalues, 1)]
    # stationary = (stationary / stationary.sum()).real.flatten()
    # # Eigenvalues give the theoretical time spent in high/low states, sample runs should converge
    # num_sims = 100
    # for _ in range(num_sims):
    #     price_simulator.randomize_price()
    #     actual_time = price_simulator.regime_component.high_time / num_sims
    # print(f"This is the expected time to spend in [low, high] states {stationary}")
    # print(f"This is the actual {actual_time}")
# ----------------------------------------------------------------------------------------------- #
    # Testing T distribution Check theoretical variance. Theoretical variance should be 1,
    # Since it is scaled. Success!
# ----------------------------------------------------------------------------------------------- # 
    # df = 5
    # t_component = TComponent(df)
    # draws = t_component.get_t_epsilon_lst(10000, df)
    # print(f"The theoretical variance is = 1\n"
    #       f"The actual variance is = {draws.var()}\n")
# ----------------------------------------------------------------------------------------------- #
    # Testing T distribution Check T dist should have higher kurtosis than normal dist,
    # Success!
# ----------------------------------------------------------------------------------------------- # 
    # prices = list(map(lambda bar: bar.close, stock_data["AAPL"]))
    # # Create an original price simulator to get normal epsilon list
    # price_simulator = GBMPriceSimulator(prices)
    # price_simulator.randomize_price()
    # normal_epsilon = price_simulator.params[:, 2].copy()
    # print(f"kurtosis of normal should be 0 = {stats.kurtosis(normal_epsilon)}"
    #       "Acceptable if ~0.1 as there is variance is lower samples")
    # t_component = TComponent(5)
    # params = t_component.apply(price_simulator.params, prices)
    # print(f"kurtosis of T dist should be higher = {stats.kurtosis(params[:, 2])}")
# ----------------------------------------------------------------------------------------------- #
    # Testing if randomize prices works when integrated with jump, t and reg
    #  Graphs the prices
# ----------------------------------------------------------------------------------------------- # 
    # prices = list(map(lambda bar: bar.close, stock_data["AAPL"]))
    # jump_component = JumpComponent(2, 0.05, 0.10)
    # regime_component = RegimeComponent(prices)
    # t_component = TComponent(df=5)
    # price_simulator = GBMPriceSimulator(prices, JumpComponent=jump_component,
    #                                     RegimeComponent=regime_component, TComponent=t_component)
    # result = []
    # num_sims = 30
    # for _ in range(num_sims):
    #     result.append(price_simulator.randomize_price())
    # graph.show_price_graphs(result).show()
    
# ----------------------------------------------------------------------------------------------- #
# ----------------------------------------------------------------------------------------------- #
    # Testing if Monte Carlo Simulator correctly generates random backtests
# ----------------------------------------------------------------------------------------------- # 
    mcs = MonteCarloSimulator(backtest=backtest)
    results = mcs.simulate(num_sims=10, df=5, exp_jumps=2,
                           mean_log_jump_size=0.05, std_log_jump_size=0.15,
                           is_t=True, is_regime_switching=True,
                           is_jump_diffusion=True)
    graph.get_monte_graph(results).show()
    
# ----------------------------------------------------------------------------------------------- #
    # Testing length of randomized prices should be equivalent to original price
    # Success!
# ----------------------------------------------------------------------------------------------- # 
    # prices = list(map(lambda bar: bar.close, stock_data["AAPL"]))
    # price_simulator = GBMPriceSimulator(prices)
    # result = price_simulator.randomize_price()
    # print(f"This is the length of original prices = {len(prices)}")
    # print(f"This is the length of randomized prices = {len(result)}")
# ----------------------------------------------------------------------------------------------- # 
    

    