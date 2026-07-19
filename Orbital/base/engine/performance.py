import os
import sys
import django
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Orbital.settings")
django.setup()

# import plotly.express as px
# from queue import Queue
# from datetime import datetime
import pandas as pd
import numpy as np
# from base.engine.distribution import Distribution
# from base.engine.monte_carlo_simulation import MonteCarloSimulator
from collections import deque
from functools import wraps
from time import time

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

def get_total_return(equity_record: pd.DataFrame) -> float:
    '''
    Returns the total return as a percentage. Uses equity to calculate.
    '''
    return (equity_record['equity'].iloc[-1] / equity_record['equity'].iloc[0]) - 1

def get_daily_returns(equity_record: pd.DataFrame) -> float:
    return equity_record['equity'].pct_change()

def get_mean_daily_returns(equity_record: pd.DataFrame) -> float:
    return np.mean(get_daily_returns(equity_record))

def get_cagr(equity_record: pd.DataFrame) -> float:
    num_days = equity_record['date'].iloc[-1] - equity_record['date'].iloc[0]
    years = num_days.days / 365.25
    return (equity_record['equity'].iloc[-1] / equity_record['equity'].iloc[0]) ** (1 / years) - 1

def get_volatility(equity_record: pd.DataFrame) -> float:
    daily_vol = get_daily_returns(equity_record).std()
    annualized_vol = daily_vol * np.sqrt(252)
    return annualized_vol

def get_sharpe_ratio(equity_record: pd.DataFrame, risk_free_rate: float) -> float:
    excess_daily_return = get_mean_daily_returns(equity_record) - (risk_free_rate / 252)
    sharpe_ratio = (excess_daily_return / get_daily_returns(equity_record).std()) * np.sqrt(252)
    return sharpe_ratio

def get_max_drawdown(equity_record: pd.DataFrame) -> float:
    equity_record['cumulative_max'] = equity_record['equity'].cummax()
    equity_record['drawdown'] = ((equity_record['equity'] - equity_record['cumulative_max'])
                                / equity_record['cumulative_max'])
    max_drawdown = equity_record['drawdown'].min()
    return max_drawdown

def get_win_rate(trade_log: pd.DataFrame) -> float:
    ''' 
    Returns the win rate of the backtest 0.50 corresponding to 50%
    win rate is considered trades with pnl > 0 over total trades
    '''
    win_count = (trade_log['pnl'] > 0).sum()
    return win_count / trade_log['pnl'].count()

@timed
def get_metrics(equity_record: pd.DataFrame, risk_free_rate: float,
                trade_log: pd.DataFrame) -> dict[str, float]:
    total_return = get_total_return(equity_record)
    mean_daily_return = get_mean_daily_returns(equity_record)
    cagr = get_cagr(equity_record)
    volatility = get_volatility(equity_record)
    sharpe_ratio = get_sharpe_ratio(equity_record, risk_free_rate)
    max_drawdown = get_max_drawdown(equity_record)
    win_rate = get_win_rate(trade_log)
    metrics = {
        "Total Return" : total_return,
        "Mean Daily Return" : mean_daily_return,
        "CAGR" : cagr,
        "Volatility" : volatility,
        "Sharpe Ratio" : sharpe_ratio,
        "Max Drawdown" : max_drawdown,
        "Win Rate" : win_rate,
    }
    return metrics

#  Examples of a records and a trade
# Record
# record = {
#         "date": fill.datetime,
#         "ticker": fill.ticker,
#         "quantity": fill.quantity,
#         "fill_price": fill.fill_cost,
#         "direction": fill.direction,
#         "commission": fill.commission,
#         "previous_quantity": prev_quantity,
#         "new_quantity": new_quantity,
#         "realised_pnl_day": realised_pnl_day,
#     }

# Trade
# trade = {   "start_date" : open_trade["date"],
#             "end_date" : record['date'],
#             "buy_price" : record["fill_price"],
#             "sell_price" : open_trade["fill_price"],
#             "quantity" : open_trade["quantity"],
#             "ticker" : open_trade["ticker"],
#             "commission" : open_trade['commission'] + part_commission
#         }
# @timed
def fill_to_trade_log(arg_fill_records: list[dict[str, any]]) -> tuple[list[dict[str, any]],
                                                                    dict[str, list[any]]]:
    '''
    Converts a list of records into a list of trades.
    There are three possible cases

    1. Flat to Long/Short
    2. Scale in, Long to long, short to short
    3. Short/Long to flat, or reversal
    '''
    fill_records = deque(arg_fill_records)
    count = 0
    def is_scale_in(prev_quantity, direction):
        if prev_quantity < 0:
            return direction == "SELL"
        return direction == "BUY"

    # any is a record
    open_trades: dict[str, list[any]] = {}
    closed_trades = []
    while len(fill_records) > 0:
        record = fill_records.popleft()
        count += 1
        # print(f"This is the {count} record {record}\n")
        ticker = record["ticker"]
        # Create list to store open trades for this ticker if it has not been stored before
        if not ticker in open_trades.keys():
            open_trades[ticker] = []

        # add the flat to long/shirt order to open trades
        if record["previous_quantity"] == 0:
            open_trades[ticker].append(record)
            continue

        # Scale in
        if is_scale_in(record["previous_quantity"], record["direction"]):
            open_trades[ticker].append(record)
            continue

        # Handles partial close, full close, and reversal
        part_closed_trades = fifo_close(open_trades, record)
        closed_trades.extend(part_closed_trades)
    return (open_trades, closed_trades)

def fifo_close(open_trades: dict[str, list[dict[str, any]]],
               record: dict[str, any]) -> list[dict[str, any]]:
    '''
    This function should return a list of closed trades and modify the open trades
    '''
    # print(f"This is the open trades at fifo close = {open_trades}")
    def same_sign(num1, num2) -> bool:
        '''just check if two numbers have same sign'''
        if num1 > 0 and num2 > 0:
            return True
        if num1 < 0 and num2 < 0:
            return True
        return False

    # There are three cases, partial close, full close, reversal
    # Close case
    if record['new_quantity'] == 0:
        # print("Carrying out a full close")
        closed_trades = handle_full_close(open_trades, record)
    # Partial case
    elif same_sign(record['previous_quantity'], record['new_quantity']):
        # print("Carrying out a partial close")
        closed_trades = handle_partial_close(open_trades, record)
    # Reversal case
    else:
        # print("Carrying out a reversal")
        closed_trades = handle_reversal_close(open_trades, record)
    return closed_trades

# @timed
def handle_reversal_close(open_trades: dict[str, list[dict[str, any]]],
                      record: dict[str, any]) -> list[dict[str, any]]:
    '''
    This function takes in the open trades, and the record that reverses them.
    It splits the record into two, one which fully closes the open trades, and
    the other which is a flat to long/short. Which it then inserts to the fill
    record 

    Splits records into two, uses one for a full close and places other in open orders
    '''
    # print("Handling a reversal," \
    # f"Open Trades = {open_trades}"
    # f"record = {record}")
    # print(f"This is the open trades = {open_trades}")
    # print(f"This is the open trades for the stock = {open_trades[record['ticker']]}")
    # Does not need to be accessed but needs to remove the first open trade
    # open_trade = open_trades[record['ticker']].pop(0)
    closed_quantity = sum(map(lambda record: record['quantity'], open_trades[record['ticker']]))
    # print(f"This is the closed quantity = {closed_quantity}")
    open_record = {}
    # Calculate commission
    closed_fraction_total = abs(closed_quantity / record['quantity'])
    closed_record_commission = round(closed_fraction_total * record["commission"]) 

    # Create the record to be full closed
    closed_record = {
                    "date": record['date'],
                    "ticker": record['ticker'],
                    "quantity": closed_quantity,
                    "fill_price": record['fill_price'],
                    "direction": record['direction'],
                    "commission": closed_record_commission,
                    "previous_quantity": record['previous_quantity'],
                    "new_quantity": 0,
                    "realised_pnl_day": record['realised_pnl_day'],
                    }

    # Create the record for flat to long/short
    # Multiplier is to determine if new quantity is +ve/-ve
    multiplier = 0
    if record["direction"] == "BUY":
        multiplier = 1
    else:
        multiplier = -1

    open_record  = {
                    "date": record['date'],
                    "ticker": record['ticker'],
                    "quantity": record['quantity'] - closed_quantity,
                    "fill_price": record['fill_price'],
                    "direction": record['direction'],
                    "commission": record['commission'] - closed_record_commission,
                    "previous_quantity": 0,
                    "new_quantity": (record['quantity'] - closed_quantity) * multiplier,
                    "realised_pnl_day": record['realised_pnl_day'],
                    }

    # Close the closed_record and add the open_records to open_trades
    closed_trades = handle_full_close(open_trades=open_trades,
                                      record=closed_record)
    
    # print(f"This is the open record = {open_record}")
    # print(f"This is the closed record = {closed_record}")
    #  TODO This might become very slow as open_trades increase in length perhaps use deque here?
    open_trades[record['ticker']].insert(0, open_record)
    return closed_trades

# @timed
def handle_partial_close(open_trades: dict[str, list[dict[str, any]]],
                      record: dict[str, any]) -> list[dict[str, any]]:
    '''
    This function only needs to return the closed trades and modify open trades
    '''
    closed_trades = []
    og_quantity_close = record['quantity']
    quantity_close = record['quantity']

    # While quantity to close is greater than the quantity of first trade. Aka fully close a trade
    while quantity_close > open_trades[record['ticker']][0]['quantity']:
        open_trade = open_trades[record['ticker']].pop(0)
        commission_fraction = abs(open_trade['quantity'] / og_quantity_close)
        part_commission = round(commission_fraction * record['commission'], 2)
        buy_price = 0
        sell_price = 0

        # if the previous trade is buy/sell the record closing it must be of opposite direction
        if open_trade['direction'] == "BUY":
            buy_price = open_trade['fill_price']
            sell_price = record['fill_price']
        else: 
            buy_price = record['fill_price']
            sell_price = open_trade['fill_price']


        # Add to closed trades list the list of trades fully closed
        closed_trades.append({
            "start_date" : open_trade["date"],
            "end_date" : record['date'],
            "buy_price" : buy_price,
            "sell_price" : sell_price,
            "quantity" : open_trade['quantity'],
            "ticker" : open_trade["ticker"],
            "commission" : open_trade['commission'] + part_commission 
                            })
        quantity_close -= open_trade["quantity"]

    # This refers to the trade that is partially closed
    open_trade = open_trades[record['ticker']].pop(0)
    print(f"This is the trade that is partially closed {open_trade}"
          f"The amount to close is {quantity_close}, and the record has"
          f" quantity {open_trade["quantity"]}")

    # Based on previous quantity, the buy/sell prices are determined
    # Additionally determines the new previous quantity of the open trade
    # It is the new previous quantity to the trade, as the previous trade is partially closed
    previous_quantity = 0
    # This means if the trade is going from long to flat
    if open_trade['direction'] == "BUY":
        buy_price = open_trade['fill_price']
        sell_price = record['fill_price']
        previous_quantity = open_trade['previous_quantity'] - quantity_close
    else:
        buy_price = record['fill_price']
        sell_price = open_trade['fill_price']
        previous_quantity = open_trade['previous_quantity'] + quantity_close


    # Commission Calculation
    close_fraction = abs(quantity_close / og_quantity_close)
    close_commission = round(close_fraction * record['commission'], 2)

    open_fraction = abs((open_trade['quantity'] - quantity_close) / open_trade['quantity'])
    open_commission = round(open_fraction * open_trade['commission'], 2)

    # This should be the final trade to add to closed_trades list
    closed_trades.append({
        "start_date" : open_trade["date"],
        "end_date" : record['date'],
        "buy_price" : buy_price,
        "sell_price" : sell_price,
        "quantity" : open_trade['quantity'],
        "ticker" : open_trade["ticker"],
        "commission" : open_trade['commission'] + close_commission 
                        })

    # Add the partially closed trade to open_trades (it was removed earlier)
    # print(f"This is the open trade {open_trade}")
    new_record = {
            "date": open_trade['date'],
            "ticker": open_trade['ticker'],
            "quantity": open_trade['quantity'] - quantity_close,
            "fill_price": open_trade['fill_price'],
            "direction": open_trade['direction'],
            "commission": open_trade['commission'] - open_commission,
            "previous_quantity": previous_quantity,
            "new_quantity": open_trade['new_quantity'],
            "realised_pnl_day": open_trade['realised_pnl_day'],
            }

    quantity_close -= open_trade["quantity"]
    print(f"The quantity to close should be 0, quantity close = {quantity_close}")
    open_trades[record['ticker']].insert(0, new_record)
    return closed_trades

# @timed
def handle_full_close(open_trades: dict[str, list[dict[str, any]]],
                      record: dict[str, any]) -> list[dict[str, any]]:
    '''
    This function returns the closed trades and modifies the open trades
    '''
    # print(f"These are the open trades {open_trades[record['ticker']]}")
    # print(f"Fully closing a record. record is {record}")
    closed_trades = []
    quantity_close = record['quantity']
    while quantity_close > 0:
        open_trade = open_trades[record['ticker']].pop(0)

        # Commission Calculation
        commission_fraction = abs(open_trade['quantity'] / record['quantity'])
        part_commission = round(commission_fraction * record['commission'], 2)

        # buy/sell price is dependent on if closing from long/short
        buy_price = 0
        sell_price = 0
        if open_trade['direction'] == "BUY":
            buy_price = open_trade['fill_price']
            sell_price = record['fill_price']
        elif open_trade['direction'] == "SELL":
            buy_price = record['fill_price']
            sell_price = open_trade['fill_price']

        # Add to closed trades list the list of trades fully closed
        closed_trades.append({
            "start_date" : open_trade["date"],
            "end_date" : record['date'],
            "buy_price" : buy_price,
            "sell_price" : sell_price,
            "quantity" : open_trade['quantity'],
            "ticker" : open_trade["ticker"],
            "commission" : open_trade['commission'] + part_commission 
                            })

        quantity_close -= open_trade["quantity"]
    return closed_trades

if __name__ == "__main__":
    record1  = {
                    "date": "2025-01-01",
                    "ticker": "AAPL",
                    "quantity": 5,
                    "fill_price": 100,
                    "direction": "SELL",
                    "commission": 0,
                    "previous_quantity": 0,
                    "new_quantity": -5,
                    "realised_pnl_day": 100,
                    }
    record2  = {
                    "date": "2025-01-02",
                    "ticker": "AAPL",
                    "quantity": 10,
                    "fill_price": 100,
                    "direction": "BUY",
                    "commission": 0,
                    "previous_quantity": -5,
                    "new_quantity": 5,
                    "realised_pnl_day": 100,
                    }

    record3 = {
                    "date": "2025-01-02",
                    "ticker": "AAPL",
                    "quantity": 5,
                    "fill_price": 110,
                    "direction": "BUY",
                    "commission": 0,
                    "previous_quantity": -5,
                    "new_quantity": 0,
                    "realised_pnl_day": 100,        
    }
    
    # Unit Testing
    # Check handle reversal
    # test_open_trades = {"AAPL" : [record1]}
    # test_closed_trades = handle_reversal_close(test_open_trades, record2)
    # print(f"This is the open trades {test_open_trades}")
    # print(f"These are the closed trades {test_closed_trades}")

    # Check handle full
    # test_open_trades = {"AAPL" : [record1]}
    # test_closed_trades = handle_full_close(test_open_trades, record3)
    # print(f"This is the open trades {test_open_trades}")
    # print(f"These are the closed trades {test_closed_trades}")

    # Test the whole fn
    # fill_records = [record1, record2]
    # test = fill_to_trade_log(fill_records)
    # print(f"This is the closed trades {test[1]}\n,"
    #       f"This is the open trades {test[0]}")
    
    
