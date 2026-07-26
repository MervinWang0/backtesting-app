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
from base.engine.data_loader import DatabaseDataLoader

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
    # data = {'mac_short_window': int(5.0),
    #         'mac_long_window': int(10.0),
    #         'asset_type': 'STOCK',
    #         'strength': 1.0,
    #         'slippage': 0.0,
    #         'initial_capital': 100000.0,
    #         'commission': 0.0,
    #         'start_date': datetime.fromisoformat("2024-01-01").date(),
    #         'end_date': datetime.fromisoformat("2025-01-01").date(),
    #         'tickers': ['AAPL'],
    #         'strategy_name': 'Moving Average Crossover'}
    # # start_date = datetime.fromisoformat("2024-01-01").date()
    # # end_date = datetime.fromisoformat("2025-01-01").date()
    # data_loader = DatabaseDataLoader(Queue(), ["AAPL"], data['start_date'],
    #                          data['end_date'], "STOCK")
    # backtest1 = Backtest(
    #                     events=data_loader.events,
    #                     data_loader=data_loader,
    #                     **data
    #                     )
    # # print(backtest1)
    # # print(backtest2)
    # btr = backtest1.run()
    # btr.get_equity_graph().show()
    
# Moving Average Cross Divergence test
    # data = {
    #         'asset_type': 'STOCK',
    #         'strength': 1.0,
    #         'slippage': 0.0,
    #         'initial_capital': 100000.0,
    #         'commission': 0.0,
    #         'start_date': datetime.fromisoformat("2024-01-01").date(),
    #         'end_date': datetime.fromisoformat("2025-01-01").date(),
    #         'tickers': ['AAPL'],
    #         'strategy_name': 'MACD'}
    # # start_date = datetime.fromisoformat("2024-01-01").date()
    # # end_date = datetime.fromisoformat("2025-01-01").date()
    # data_loader = DatabaseDataLoader(Queue(), ["AAPL"], data['start_date'],
    #                          data['end_date'], "STOCK")
    # backtest1 = Backtest(
    #                     events=data_loader.events,
    #                     data_loader=data_loader,
    #                     **data
    #                     )
    # # print(backtest1)
    # # print(backtest2)
    # btr = backtest1.run()
    # btr.get_equity_graph().show()
# Mean Reversion test

    # data = {
    #         'rsi_window' : 14,
    #         'rsi_oversold' : 30,
    #         'bollinger_window' : 20,
    #         'z_window' : 20,
    #         'asset_type': 'STOCK',
    #         'strength': 1.0,
    #         'slippage': 0.0,
    #         'initial_capital': 100000.0,
    #         'commission': 0.0,
    #         'start_date': datetime.fromisoformat("2025-01-01").date(),
    #         'end_date': datetime.fromisoformat("2025-05-01").date(),
    #         'tickers': ['AAPL'],
    #         'strategy_name': 'Mean Reversion'}
    # data_loader = DatabaseDataLoader(Queue(), data['tickers'], data['start_date'],
    #                          data['end_date'], data['asset_type'])
    # backtest1 = Backtest(
    #                     events=data_loader.events,
    #                     data_loader=data_loader,
    #                     adjustment_method="BACK_ADJUSTED",
    #                     **data
    #                     )
    # btr = backtest1.run()
    # btr.get_equity_graph().show()
    # prices = [bar.close for bar in data_loader.latest_stock_data['TSLA']]
    # print(f"This is the rsi {backtest1.strategy.rsi['TSLA']}")
    # print(f"these are the prices {prices}")
    
# EMA Test

    # data = {
    #         'asset_type': 'STOCK',
    #         'strength': 1.0,
    #         'slippage': 0.0,
    #         'initial_capital': 100000.0,
    #         'commission': 0.0,
    #         'start_date': datetime.fromisoformat("2025-01-01").date(),
    #         'end_date': datetime.fromisoformat("2026-01-01").date(),
    #         'tickers': ['TSLA'],
    #         'strategy_name': 'MACD'}
    # data_loader = DatabaseDataLoader(Queue(), data['tickers'], data['start_date'],
    #                          data['end_date'], "STOCK")
    # backtest1 = Backtest(
    #                     events=data_loader.events,
    #                     data_loader=data_loader,
    #                     **data
    #                     )
    # btr = backtest1.run()
    # btr.get_equity_graph().show()

# Breakout Testing
    data = {
            'asset_type': 'STOCK',
            'strength': 1.0,
            'slippage': 0.0,
            'initial_capital': 100000.0,
            'commission': 0.0,
            'start_date': datetime.fromisoformat("2025-01-01").date(),
            'end_date': datetime.fromisoformat("2026-01-01").date(),
            'tickers': ['TSLA'],
            'strategy_name': 'Breakout'}

    data_loader = DatabaseDataLoader(Queue(), data['tickers'], data['start_date'],
                             data['end_date'], "STOCK")

    backtest1 = Backtest(
                        events=data_loader.events,
                        data_loader=data_loader,
                        **data
                        )

    btr = backtest1.run()
    # btr.get_equity_graph().show()

# Momentum Triple testing
    # data = {
    #         'asset_type': 'STOCK',
    #         'strength': 1.0,
    #         'slippage': 0.0,
    #         'initial_capital': 100000.0,
    #         'commission': 0.0,
    #         'start_date': datetime.fromisoformat("2025-01-01").date(),
    #         'end_date': datetime.fromisoformat("2026-01-01").date(),
    #         'tickers': ['JPM'],
    #         'strategy_name': 'Momentum'}

    # data_loader = DatabaseDataLoader(Queue(), data['tickers'], data['start_date'],
    #                          data['end_date'], "STOCK")

    # backtest1 = Backtest(
    #                     events=data_loader.events,
    #                     data_loader=data_loader,
    #                     **data
    #                     )

    # btr = backtest1.run()
    # btr.get_equity_graph().show()

# Rate of Change Strategy

    # data = {
    #         'asset_type': 'STOCK',
    #         'strength': 1.0,
    #         'slippage': 0.0,
    #         'initial_capital': 100000.0,
    #         'commission': 0.0,
    #         'start_date': datetime.fromisoformat("2025-01-01").date(),
    #         'end_date': datetime.fromisoformat("2026-01-01").date(),
    #         'tickers': ['TSLA'],
    #         'strategy_name': 'Rate Of Change'}

    # data_loader = DatabaseDataLoader(Queue(), data['tickers'], data['start_date'],
    #                          data['end_date'], "STOCK")

    # backtest1 = Backtest(
    #                     events=data_loader.events,
    #                     data_loader=data_loader,
    #                     **data
    #                     )

    # btr = backtest1.run()
    # btr.get_equity_graph().show()

# Stochastic Oscillator Strategy

    # data = {
    #         'asset_type': 'STOCK',
    #         'strength': 1.0,
    #         'slippage': 0.0,
    #         'initial_capital': 100000.0,
    #         'commission': 0.0,
    #         'start_date': datetime.fromisoformat("2025-01-01").date(),
    #         'end_date': datetime.fromisoformat("2026-01-01").date(),
    #         'tickers': ['TSLA'],
    #         'strategy_name': 'Stochastic Oscillator'}

    # data_loader = DatabaseDataLoader(Queue(), data['tickers'], data['start_date'],
    #                          data['end_date'], "STOCK")

    # backtest1 = Backtest(
    #                     events=data_loader.events,
    #                     data_loader=data_loader,
    #                     **data
    #                     )

    # btr = backtest1.run()
    # btr.get_equity_graph().show()


























