from django.http import HttpResponse
from django.shortcuts import render
import json
from queue import Queue
import random
from datetime import datetime, timedelta
from django.http import JsonResponse
from base.engine.data_loader import DatabaseDataLoader
from base.engine.backtest import Backtest
from base.models import StockPriceHistory, Stock
from django.core.management import call_command

# Take in a list of ids and return a JsonResponse which has a dict of data
def get_quicktest_input(request) -> JsonResponse:
    ''' 
    This function is used to quickly set up a backtest/mcs
    
    1. It takes in a list of parameter ids, used to identify which params are used by the strategy
    2. For each id, it creates a dict entry of id: random value
    3. return dict as data in JsonResponse
    '''
    if request.method == "POST":
        param_ids: dict[str: any] = json.loads(request.body)
        # print(f"This is the type of params_ids {type(param_ids)}")
        # print(f"This is the type of params_id {type(param_ids[0])}")
        random_parameters = {id_string : get_rand(id_string) for id_string in param_ids}
        # print(f"This is the randomized input {random_parameters}")
        return JsonResponse(data=random_parameters)
    else:
        return JsonResponse(
            {"error": "This endpoint only supports POST requests."},
            status=405  # Method Not Allowed
        )

def get_random_ticker():
    ''' 
    Makes a db call and gets a random ticker from S&P500
    '''
    rand_int = random.randint(1, 500)
    ticker = Stock.objects.values('ticker').get(id=rand_int)['ticker']
    print(f"This is the randomized ticker = {ticker}")
    return ticker

PARAM_RANGES = {
    "asset_type": lambda: "STOCK",
    "strength": lambda: random.uniform(0, 1),
    "slippage": lambda: random.uniform(0, 0.05),
    "initial_capital": lambda: random.uniform(50000, 250000),
    "start_date": lambda: (datetime(2023, 1, 1) + timedelta(days=random.randint(1, 364))).date(),
    "end_date": lambda: (datetime(2024, 1, 1) + timedelta(days=random.randint(1, 365))).date(),
    "commission": lambda: random.uniform(0.001, 0.01),
    "num_sims": lambda: random.randint(50, 500),
    "df": lambda: random.randint(3, 8),
    "exp_jumps": lambda: random.randint(1, 3),
    "mean_log_jump_size": lambda: random.uniform(0.03, 0.06),
    "std_log_jump_size": lambda: random.uniform(0.08, 0.12),

    # Moving average crossover
    "mac_short_window": lambda: random.randint(5, 10),
    "mac_long_window": lambda: random.randint(11, 30),

    # Mean reversion
    "rsi_window": lambda: random.randint(7, 21),
    "bollinger_window": lambda: random.randint(10, 50),
    "z_window": lambda: random.randint(10, 60),
    "rsi_overbought": lambda: random.randint(60, 80),
    "rsi_oversold": lambda: random.randint(20, 40),
    "z_upper": lambda: random.randint(2, 3),
    "z_lower": lambda: -random.randint(2, 3),
    "mean_reversion_logic": lambda: random.choice(["AND", "MAJORITY"]),

    # MACD
    "macd_short": lambda: random.randint(5, 15),
    "macd_medium": lambda: random.randint(20, 35),
    "macd_long": lambda: random.randint(35, 50),

    # Donchian breakout
    "donchian_window": lambda: random.randint(10, 55),

    # Rate Of Change
    "roc_window": lambda: random.randint(10, 20),
    
    # Stochastic
    "stoc_window": lambda: random.randint(10, 21),
}

def get_rand(case: str):
    '''
    Matches each id and returns a random value suitable for that id
    '''
    # For multiple tickers if ticker in ticker1, ticker2...
    if "ticker" in case:
        return get_random_ticker()

    # Check if case is in the randomizable params
    print(f"This is the case to be randomized = {case}")
    if case not in PARAM_RANGES:
        raise ValueError(f"Unknown parameter: {case}")

    # When case is found return it
    return PARAM_RANGES[case]()
