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


if __name__ == "__main__":

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
                        strategy_params={"short_window": 5,
                                        "long_window": 10},
                        data_loader=data_loader
                        )

    backtest.run()
    stock_data = backtest.data_loader.get_stock_data()
    mcs = MonteCarloSimulator(backtest)
    test = mcs.simulate(1, 0.05, 1, 0.01, 5)
    # test is lit of backtest results
    print(f"This is the type of test = {type(test)}")
    print(f"This is the test = {test}")
    btr1 = test[0]
    print(f"This is the fill records = {btr1.get_fill_records()}")
    print(btr1.get_trade_records())
    # btr2 = test[1]
    # print(f"This is the closed trades = {btr1.get_trade_records()[0]}")
    # print(f"This is the open trades = {btr1.get_trade_records()[1]}")