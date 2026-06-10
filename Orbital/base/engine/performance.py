import os
import sys
import django
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Orbital.settings")
django.setup()

import plotly.express as px
from queue import Queue
from base.engine.monte_carlo_simulation import MonteCarloSimulatior
from datetime import datetime
from base.engine.data_loader import DatabaseDataLoader
import pandas as pd
from base.engine.distribution import Distribution
from base.engine.monte_carlo_simulation import MonteCarloSimulatior
from base.engine.backtest import Backtest
    


def fill_to_trade_log(fill_records: list[dict[str, any]], method="fifo") -> list[dict[str,any]]:
    '''
    Converts a list of records into a list of trades.
    There are three possible cases

    1. Flat to Long/Short
    2. Scale in, Long to long, short to short
    3. Short/Long to flat, or reversal
    '''
    def is_scale_in(quantity, direction):
        if quantity < 0:
            return direction == "SELL"
        return direction == "BUY"
    
    open_trades = {}
    closed_trades = []
    for record in fill_records:
        ticker = record["ticker"]
        # Create list to store open trades
        if not ticker in open_trades.keys():
            open_trades[ticker] = []

        # add the flat/long order to open trades
        if record["previous_quantity"] == 0:
            open_trades[ticker].append(record)
            break       
        
        # Scale in
        if is_scale_in(record["previous_quantity"], record["direction"]):
           open_trades[ticker].append(record)
           break

        # Handles partial close, full close, and reversal
        else:
            closed = fifo_close(open_trades[ticker], record["quantity"], end_date=record["date"],
                                commission=record["commission"], sell_price=record["fill_price"])
            closed_trades.extend(closed[0])
            open_trades["ticker"] = closed[1]
    return {"closed_trades" : closed_trades, "open_trades" : open_trades}

def fifo_close(stock_open_trades: list, quantity_close: float, end_date: datetime.date,
               commission: float, sell_price: float) -> tuple(list):
    '''
    This function should return a tuple with two lists, a list represents the closed trades
    and a list representing the open trades.
    '''
    trades = []
    while stock_open_trades and quantity_close > 0:
        record = stock_open_trades.pop(0)
        if quantity_close >= abs(record["quantity"]):
            # Part commission is necessary, consider there being multiple
            # open long orders, and one big close order closes them
            # The commission of the close is split across multiple trades
            part_commission = abs(record["quantity"]) / quantity_close
            part_commission = round(part_commission * commission, 2)
            quantity_close -= abs(record["quantity"])
            trades.append({"start_date" : record["date"],
                           "end_date" : end_date,
                           "buy_price" : record["fill_price"],
                           "sell_price" : sell_price,
                           "quantity" : abs(record["quantity"]),
                           "ticker" : record["ticker"],
                           "commission" : record[commission] + part_commission})
        else:
            # For a partial fill, close the partial trade and open a new partial order
            # Here the commission is only part of the whole as the entire trade is not completed
            part_commission = round(quantity_close * record["commission"], 2)
            quantity_close = 0
            trades.append({"start_date" : record["date"],
                           "end_date" : end_date,
                           "buy_price" : record["fill_price"],
                           "sell_price" : sell_price,
                           "quantity" : quantity_close,
                           "ticker" : record["ticker"],
                           "commission" : part_commission})

            # Open the partial order here
            record["quantity"] -= quantity_close
            stock_open_trades.insert(0,record)
    return (trades, stock_open_trades)


if __name__ == "__main__":

    start_date = datetime.fromisoformat("2021-05-24").date()
    end_date = datetime.fromisoformat("2022-06-07").date()
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
    stock_data = backtest.data_loader.get_past_bars("AAPL",
                len(backtest.data_loader.get_timeline()))
    mcs = MonteCarloSimulatior(backtest)
    test = mcs.simulate(1)
    for BTR in test:
        print(fill_to_trade_log(BTR.get_fill_records()))


# class MetricsCalculator():
    # '''
    # Description
    # This class contains methods to calculate various metrics to analyze
    # a trading strategy. It only requires an equity curve to be initialized.

    # Features
    
    # Methods
    # get_total_return(self) -> float. overall % gain/loss
    # get_CAGR(self) -> float. annualised return accounting for compounding
    # get_daily_returns_distribution -> distribution
    # get_monthly_returns_distribution -> distribution
    # get_yearly_returns_distribution -> distribution

    # Implementation Details
    # returns are stored in natural log form as it makes calculating of returns
    # over a preiod faster.

    # '''

