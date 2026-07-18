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
from functools import wraps
from time import time
from base.engine.backtest import (Backtest,
                                  BacktestResult)
from base.engine.strategy import(
                                RSIConfig,
                                BollingerConfig,
                                ZConfig,
)


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
# Moving Average Cross test
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
            'strategy_name': 'Moving Average Crossover'}
    # start_date = datetime.fromisoformat("2024-01-01").date()
    # end_date = datetime.fromisoformat("2025-01-01").date()
    data_loader = DatabaseDataLoader(Queue(), ["AAPL"], data['start_date'],
                             data['end_date'], "STOCK")
    backtest1 = Backtest(
                        events=data_loader.events,
                        data_loader=data_loader,
                        **data
                        )
    # print(backtest1)
    # print(backtest2)
    btr = backtest1.run()
    btr.get_equity_graph().show()
    
# Mean Reversion test
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
            'strategy_name': 'Moving Average Crossover'}
    # start_date = datetime.fromisoformat("2024-01-01").date()
    # end_date = datetime.fromisoformat("2025-01-01").date()
    data_loader = DatabaseDataLoader(Queue(), ["AAPL"], data['start_date'],
                             data['end_date'], "STOCK")
    backtest1 = Backtest(
                        events=data_loader.events,
                        data_loader=data_loader,
                        **data
                        )
    # print(backtest1)
    # print(backtest2)
    btr = backtest1.run()
    btr.get_equity_graph().show()