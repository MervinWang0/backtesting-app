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

# Used in quicktest
def get_rand(case: str) -> int|float|datetime.date:
    ''' 
    Matches each id and returns a random value suitable for that id
    '''
    if "short_window" == case:
        return random.randint(1, 10)
    if "long_window" == case:
        return random.randint(11, 30)
    if "asset_type" == case:
        return "STOCK"
    if "ticker" == case:
        rand_int = random.randint(1,500)
        print(f"This should be dict of ticker: name "
              f"{Stock.objects.values('ticker').get(id=rand_int)}")
        return Stock.objects.values('ticker').get(id=rand_int)['ticker']
    if "strength" == case:
        return random.randint(1,10)
    if "slippage" == case:
        return random.uniform(0, 0.05)
    if "initial_capital" == case:
        return random.uniform(50000, 250000)
    if "rolling_window" == case:
        return random.randint(11, 30)
    if "start_date" == case:
        start_date = datetime(2023, 1, 1)
        return (start_date + timedelta(days=random.randint(1,364))).date()
    if "end_date" == case:
        end_date = datetime(2024, 1, 1)
        return (end_date + timedelta(days=random.randint(1,365))).date()
    if "commission" == case:
        return random.uniform(0.001, 0.01)
    if "num_sims" == case:
        return random.randint(50, 500)
    if "df" == case:
        return random.randint(3,8)
    if "exp_jumps" == case:
        return random.randint(1,3)
    if "mean_log_jump_size" == case:
        return random.uniform(0.03, 0.06)
    if "std_log_jump_size" == case:
        return random.uniform(0.08, 0.12)

