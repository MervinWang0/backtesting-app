import os
import sys
import django
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Orbital.settings")
django.setup()

from dataclasses import dataclass
from datetime import datetime
from queue import Queue
import plotly.express as px
import pandas as pd

from base.engine.execution import ExecutionLoader
from base.engine.portfolio import Portfolio
from base.engine.data_loader import DataLoader, DatabaseDataLoader
from base.engine.strategy import MovingAverageCross
import base.engine.graph as graph
from base.engine.backtest import Backtest
from base.engine.monte_carlo_simulation import MonteCarloSimulator
import base.engine.performance as p


if __name__ == "__main__":

    # start_date = datetime.fromisoformat("2021-05-24").date()
    # end_date = datetime.fromisoformat("2022-05-24").date()
    # data_loader = DatabaseDataLoader(Queue(), ["AAPL"], start_date,
    #                          end_date, "STOCK")
    # backtest = Backtest(
    #                     events=data_loader.events,
    #                     tickers=["AAPL"],
    #                     start_date=start_date,
    #                     end_date=end_date,
    #                     strategy_name="MovingAverageCross",
    #                     strategy_params={"short_window": 5,
    #                                     "long_window": 10},
    #                     data_loader=data_loader
    #                     )

    # backtest.run()
    # stock_data = backtest.data_loader.get_stock_data()
    # mcs = MonteCarloSimulator(backtest)
    # test = mcs.simulate(1, 0.05, 1, 0.01, 5)
    # test is lit of backtest results
    # print(f"This is the type of test = {type(test)}")
    # print(f"This is the test = {test}")
    # btr1 = test[0]
    # print(f"This is the fill records = {btr1.get_fill_records()}")
    # print(btr1.get_trade_records())
    # btr2 = test[1]
    # print(f"This is the closed trades = {btr1.get_trade_records()[0]}")
    # print(f"This is the open trades = {btr1.get_trade_records()[1]}")

    
    data = {'short_window': int(5.0),
            'long_window': int(10.0),
            'asset_type': 'STOCK',
            'strength': 1.0,
            'slippage': 0.0,
            'initial_capital': 100000.0,
            'commission': 0.0,
            'start_date': datetime.fromisoformat("2024-01-01").date(),
            'end_date': datetime.fromisoformat("2025-01-01").date(),
            'tickers': ['AAPL'],
            'strategy_name': 'moving_average_crossover'}

    data_loader = DatabaseDataLoader(Queue(), ["AAPL"], data["start_date"],
                             data["end_date"], "STOCK")
    backtest = Backtest(
                            events=data_loader.events,
                            data_loader=data_loader,
                            **data
                            )
    result = backtest.run()
    equity_record = result.get_equity_records()
    print(equity_record)
    print(f"This is the total return = {p.get_total_return(equity_record)}\n")
    print(f"This is the daily returns = {p.get_daily_returns(equity_record)}\n")
    print(f"This is the mean daily return = {p.get_mean_daily_returns(equity_record)}\n")
    print(f"This is the cagr = {p.get_cagr(equity_record)}\n")
    print(f"This is the annualised volatility = {p.get_volatility(equity_record)}\n")
    print(f"This is the shapre ratio = {p.get_sharpe_ratio(equity_record, 0.02)}\n")
    print(f"This is the max_drawdown = {p.get_max_drawdown(equity_record)}\n")
    print(f"Result of get metrics = {p.get_metrics(equity_record, 0.02)}")
