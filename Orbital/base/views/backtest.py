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

def get_backtest(request) -> HttpResponse:
    '''
    Renders the webpage of the Backtest
    '''
    backtest = {}

    return render(request, "backtest.html", backtest)

def backtest_graph(request) -> HttpResponse:
    '''
    This function takes in a list of inputs, runs a backtest and 
    plots the equity curve of the backtest
    '''
    if request.method == "POST":
        print("Entered backtest_graph")
        data: dict[str: any] = json.loads(request.body)
        # Cleaning data
        # Extra conversion, during debugging short/long window being float causes
        # The backtest runs to fail
        int_params = ['short_window', 'long_window']
        # Dates have to be converted to datetime.date
        data["start_date"] = datetime.strptime(data["start_date"], "%Y-%m-%d")
        data["end_date"] = datetime.strptime(data["end_date"], "%Y-%m-%d")
        # Convert certain parameters to numeric and others ignore
        for key in data:
            try:
                if key in int_params:
                    data[key] = int(data[key])
                else:
                    data[key] = float(data[key])
            except Exception:
                pass
        print(data)
        # Checks if stock data exists for ticker in period otherwise download
        period = get_yf_period(data["start_date"], data["end_date"])
        if data["asset_type"] == "STOCK":
            for ticker in data["tickers"]:
                if not data_exists(ticker, data["start_date"], data["end_date"]):
                    call_command(
                        "load_stock_data",
                        symbol = ticker,
                        period = period,
                        interval = "1d",
                    )
        # elif data["asset_type"] == "FOREX": TODO
        
        
            

        # Use inputs to construct some necessary parameters
        events = Queue()
        data_loader = DatabaseDataLoader(events=events, tickers=data["tickers"],
                                         start_date=data["start_date"],
                                         end_date=data["end_date"],
                                         asset_type=data["asset_type"])
        print("Backtest not executed but params created")
        backtest = Backtest(
                            events=data_loader.events,
                            data_loader=data_loader,
                            **data
                            )
        # print(Backtest.__dict__)
        print("Backtest created")
        btr = backtest.run()
        print("Backtest executed")
        fig = btr.get_equity_graph()
        # fig.show()
        print("equity graph obtained")
        equity_graph_html = fig.to_html(full_html=False)
        print("equity graph converted to html")

        # Also pass in the performance metrics.
        metrics = btr.get_metrics()
        return JsonResponse({"equity_graph_html" : equity_graph_html,
                             "metrics" : metrics, "run_id" : backtest.get_backtest_run_id()})
    else:
        return JsonResponse(
            {"error": "This endpoint only supports POST requests."},
            status=405  # Method Not Allowed
        )
# TODO should run download of S&P 500 stock data at the start of each day instead of
# running it to check each run
# Functions for automatic downloading of data
def data_exists(symbol, start_date, end_date) -> bool:
    stock = Stock.objects.filter(ticker = symbol).first()

    if not stock:
        return False
    
    bars = StockPriceHistory.objects.filter(stock = stock, date__range = (start_date, end_date),)

    if not bars.exists():
        return False

    return True     

# Take in a list of ids and return a JsonResponse which has a dict of data
def get_quicktest_input(request) -> JsonResponse:
    ''' 
    This function is used to quickly set up a backtest and running it.
    
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

def get_yf_period(start_date, end_date):
    days = (end_date - start_date).days +1

    if days <= 31:
        return "1mo"
    elif days <= 93:
        return "3mo"
    elif days <= 186:
        return "6mo"
    elif days <= 365:
        return "1y"
    elif days <=730:
        return "2y"
    elif days <=1825:
        return "5y"
    elif days <= 3650:
        return "10y"
    else:
        return "max"