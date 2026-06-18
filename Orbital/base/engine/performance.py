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
# from base.engine.data_loader import DatabaseDataLoader
# import pandas as pd
# from base.engine.distribution import Distribution
# from base.engine.backtest import Backtes
# from base.engine.monte_carlo_simulation import MonteCarloSimulator
from collections import deque


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
    total_closed_trades = []
    while len(fill_records) > 0:
        record = fill_records.popleft()
        count += 1
        print(f"This is each record\n{record}, of count {count}")
        ticker = record["ticker"]
        # Create list to store open trades
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
        closed_trades = fifo_close(open_trades, record, fill_records)
        total_closed_trades.extend(closed_trades)
    return (open_trades, total_closed_trades)

def fifo_close(open_trades: dict[str, list[dict[str, any]]],
               record: dict[str, any], fill_records: deque[dict[str, any]]) -> list[dict[str, any]]:
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
        closed_trades = handle_full_close(open_trades, record)
    # Partial case
    elif same_sign(record['previous_quantity'], record['new_quantity']):
        closed_trades = handle_partial_close(open_trades, record)
    # Reversal case
    else:
        closed_trades = []
        handle_reversal_close(open_trades, record, fill_records)
    return closed_trades

def handle_reversal_close(open_trades: dict[str, list[dict[str, any]]],
                      record: dict[str, any], fill_records: deque[dict[str, any]]) -> None:
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
    print(f"This is the closed quantity = {closed_quantity}")
    open_record = {}
    # Calculate commission
    closed_record_commission = abs(closed_quantity / record['quantity'])
    closed_record_commission = round(closed_record_commission * record["commission"]) 

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
    if record["direction"] == "BUY":
        open_record  = {
                        "date": record['date'],
                        "ticker": record['ticker'],
                        "quantity": record['quantity'] - closed_quantity,
                        "fill_price": record['fill_price'],
                        "direction": record['direction'],
                        "commission": record['commission'] - closed_record_commission,
                        "previous_quantity": 0,
                        "new_quantity": record['quantity'] - closed_quantity,
                        "realised_pnl_day": record['realised_pnl_day'],
                        }
    else:
        open_record  = {
                        "date": record['start_date'],
                        "ticker": record['ticker'],
                        "quantity": record['quantity'] - closed_quantity,
                        "fill_price": record['fill_price'],
                        "direction": record['direction'],
                        "commission": record['commission'] - closed_record_commission,
                        "previous_quantity": 0,
                        "new_quantity": -(record['quantity'] - closed_quantity),
                        "realised_pnl_day": record['realised_pnl_day'],
                        }
    print(f"This is the open record = {open_record}")
    print(f"This is the closed record = {closed_record}")
    fill_records.appendleft(open_record)
    fill_records.appendleft(closed_record)
    return None

def handle_partial_close(open_trades: dict[str, list[dict[str, any]]],
                      record: dict[str, any]) -> list[dict[str, any]]:
    '''
    This function only needs to return the closed trades and modify open trades
    '''
    closed_trades = []
    og_quantity_close = record['quantity']
    quantity_close = record['quantity']
    # While quantity to close is greater than the quantity of first trade
    while quantity_close > open_trades[record['ticker']][0]['quantity']:
        open_trade = open_trades[record['ticker']].pop(0)
        if open_trade['previous_quantity'] > 0:
            # Commission Calculation
            part_commission = abs(open_trade['quantity'] / quantity_close)
            part_commission = round(part_commission * record['commission'], 2) 
            closed_trades.append({  "start_date" : open_trade["date"],
                                    "end_date" : record['date'],
                                    "buy_price" : open_trade["fill_price"],
                                    "sell_price" : record["fill_price"],
                                    "quantity" : open_trade['quantity'],
                                    "ticker" : open_trade["ticker"],
                                    "commission" : open_trade['commission'] + part_commission
                                })
            quantity_close -= open_trade['quantity']
        elif open_trade['previous_quantity'] < 0:
            # Commission Calculation
            part_commission = abs(quantity_close / open_trade['quantity'])
            part_commission = round(part_commission * record['commission'], 2)
            closed_trades.append({  "start_date" : open_trade["date"],
                                    "end_date" : record['date'],
                                    "buy_price" : record["fill_price"],
                                    "sell_price" : open_trade["fill_price"],
                                    "quantity" : open_trade['quantity'],
                                    "ticker" : open_trade["ticker"],
                                    "commission" : open_trade['commission'] + part_commission
                                })
            quantity_close -= open_trade["quantity"]
        else:
            raise ValueError("This should not have happened. previous_quantity if 0 should not"
            "have reached the closing case")
    open_trade = open_trades[record['ticker']].pop(0)
    if record['previous_quantity'] > 0:
        # Commission Calculation
        close_commission = abs(quantity_close / og_quantity_close)
        close_commission = round(close_commission * record['commission'], 2) 

        open_commission = abs((open_trade['quantity'] - quantity_close) / open_trade['quantity'])
        open_commission = round(open_commission * open_trade['commission'], 2) 

        closed_trades.append({  "start_date" : open_trade["date"],
                                "end_date" : record['date'],
                                "buy_price" : open_trade["fill_price"],
                                "sell_price" : record["fill_price"],
                                "quantity" : quantity_close,
                                "ticker" : open_trade["ticker"],
                                "commission" : open_commission + close_commission
                            })
        new_record = {
                "date": open_trade['start_date'],
                "ticker": open_trade['ticker'],
                "quantity": open_trade['quantity'] - quantity_close,
                "fill_price": open_trade['fill_price'],
                "direction": open_trade['direction'],
                "commission": open_trade['commission'] - open_commission,
                "previous_quantity": open_trade['previous_quantity'] - quantity_close,
                "new_quantity": open_trade['new_quantity'],
                "realised_pnl_day": open_trade['realised_pnl_day'],
                }
        open_trades[record['ticker']].insert(0, new_record)
        quantity_close = 0
    elif record['previous_quantity'] < 0:
        # Commission Calculation
        close_commission = abs(quantity_close / og_quantity_close)
        close_commission = round(close_commission * record['commission'], 2) 

        open_commission = abs((open_trade['quantity'] - quantity_close) / open_trade['quantity'])
        open_commission = round(open_commission * open_trade['commission'], 2) 

        closed_trades.append({  "start_date" : open_trade["date"],
                                "end_date" : record['date'],
                                "buy_price" : record["fill_price"],
                                "sell_price" : open_trade["fill_price"],
                                "quantity" : quantity_close,
                                "ticker" : open_trade["ticker"],
                                "commission" : open_commission + close_commission
                            })
        new_record = {
                "date": open_trade['start_date'],
                "ticker": open_trade['ticker'],
                "quantity": open_trade['quantity'] - quantity_close,
                "fill_price": open_trade['fill_price'],
                "direction": open_trade['direction'],
                "commission": open_trade['commission'] - open_commission,
                "previous_quantity": open_trade['previous_quantity'] + quantity_close,
                "new_quantity": open_trade['new_quantity'],
                "realised_pnl_day": open_trade['realised_pnl_day'],
                }
        open_trades[record['ticker']].insert(0, new_record)
        quantity_close = 0
    else:
        raise ValueError("This should not have happened. previous_quantity if 0 should not"
        "have reached the closing case")
    return closed_trades

def handle_full_close(open_trades: dict[str, list[dict[str, any]]],
                      record: dict[str, any]) -> tuple[list[dict[str, any]], list[dict[str, any]]]:
    '''
    This function returns the closed trades and modifies the open trades
    '''
    print(f"This is the record to full close {record}")
    new_closed_trades = []
    quantity_close = record['quantity']
    while quantity_close > 0:
        print("This is the open trade at the point of full close" \
        f"{open_trades}")
        open_trade = open_trades[record['ticker']].pop(0)
        quantity_close -= open_trade["quantity"]

        # Commission Calculation
        part_commission = abs(open_trade['quantity'] / record['quantity'])
        part_commission = round(part_commission * record['commission'], 2)

        # If open trade is long/short position closed buy/sell price is different
        if record['previous_quantity'] > 0:
            new_closed_trades.append({  "start_date" : open_trade["date"],
                                        "end_date" : record['date'],
                                        "buy_price" : open_trade["fill_price"],
                                        "sell_price" : record["fill_price"],
                                        "quantity" : open_trade["quantity"],
                                        "ticker" : open_trade["ticker"],
                                        "commission" : open_trade['commission'] + part_commission
                                    })
        elif record['previous_quantity'] < 0:
            new_closed_trades.append({  "start_date" : open_trade["date"],
                                        "end_date" : record['date'],
                                        "buy_price" : record["fill_price"],
                                        "sell_price" : open_trade["fill_price"],
                                        "quantity" : open_trade["quantity"],
                                        "ticker" : open_trade["ticker"],
                                        "commission" : open_trade['commission'] + part_commission
                                    })
        else:
            raise ValueError("This should not have happened. previous_quantity if 0 should not"
            "have reached the closing case")
    return new_closed_trades

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
    
    # Check handle reversal
    # open_trades = {"AAPL" : [record1]}
    # fill_records = 
    # handle_reversal_close(open_trades, record2, fill_records)
    # print(fill_records)
    # print(f"This is the open trades, it should be empty {open_trades}")

    # Check handle full
    # open_trades = {"AAPL" : [record1]}
    # closed_trades = handle_full_close(open_trades, record)

    # Test the whole fn
    fill_records = [record1, record2]
    test = fill_to_trade_log(fill_records)
    print(f"This is the closed trades {test[0]}\n,"
          f"This is the open trades {test[1]}")


