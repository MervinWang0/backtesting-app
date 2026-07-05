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
from functools import wraps
from time import time

from base.engine.execution import ExecutionLoader
from base.engine.portfolio import Portfolio
from base.engine.data_loader import DataLoader, DatabaseDataLoader
from base.engine.strategy import MovingAverageCross
import base.engine.graph as graph
from base.engine.backtest import Backtest
from base.engine.monte_carlo_simulation import MonteCarloSimulator
import base.engine.performance as p

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

if __name__ == "__main__":
    # Default initialization of backtest
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
            'strategy_name': 'moving_average_crossover'
            }

    data_loader = DatabaseDataLoader(Queue(), ["AAPL"], data["start_date"],
                    data["end_date"], "STOCK")

    backtest = Backtest(
                    events=data_loader.events,
                    data_loader=data_loader,
                    **data
                    )

    @timed
    def backtest_time():
        print("Executed Backtest")
        return backtest.run()
    result = backtest_time()
#     equity_record = result.get_equity_records()
#     print(equity_record)
#     print(f"This is the total return = {p.get_total_return(equity_record)}\n")
#     print(f"This is the daily returns = {p.get_daily_returns(equity_record)}\n")
#     print(f"This is the mean daily return = {p.get_mean_daily_returns(equity_record)}\n")
#     print(f"This is the cagr = {p.get_cagr(equity_record)}\n")
#     print(f"This is the annualised volatility = {p.get_volatility(equity_record)}\n")
#     print(f"This is the shapre ratio = {p.get_sharpe_ratio(equity_record, 0.02)}\n")
#     print(f"This is the max_drawdown = {p.get_max_drawdown(equity_record)}\n")
#     print(f"Result of get metrics = {p.get_metrics(equity_record, 0.02)}")


    # Testing of fill records to trade records function
    # Successfully creates table of records that look correct (at a glance)
    # fill_records = result.get_fill_records()
    # test = p.fill_to_trade_log(fill_records)
    # print(f"This is the closed trades \n{pd.DataFrame(test[1])}\n,"
    #       f"This is the open trades {test[0]}")
        
    # Further more detailed testing of trade records
    # Testing that equity change is preserved
    # Turn closed trades into a data frame and get the pnl of each trade
    
    trade_log = result.get_trade_log()
    closed_trades = pd.DataFrame(trade_log[1])
    open_trades = trade_log[0]
    # print(trade_log)
    closed_trades["pnl"] = (closed_trades['sell_price'] - closed_trades['buy_price']) * closed_trades['quantity']
    print(f"This is the pnl of closed trades\n {closed_trades}\n")
    realised_pnl = closed_trades['pnl'].sum()
    
    print(open_trades)
    # Adds the value of the holdings
    for record in open_trades["AAPL"]:
        multiplier = 0
        if record['direction'] == "BUY":
            multiplier = 1
        else:
            multiplier = -1

        realised_pnl += record['quantity'] * record['fill_price'] * multiplier
    
    print(f"This is the total change in equity {realised_pnl / data["initial_capital"]}")
    print(f"This is the metrics {result.get_metrics()}")
    # equity = realised_pnl 

    fill_records = pd.DataFrame(result.get_fill_records())
    equity_records = result.get_equity_records()
    print(f"This is the fill records \n{fill_records}")
    print(f"This is the equity records \n{equity_records}")

    
