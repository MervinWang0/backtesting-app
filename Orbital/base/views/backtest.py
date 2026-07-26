from django.http import HttpResponse
from django.shortcuts import render
import json
from queue import Queue
import random
from datetime import datetime, timedelta
from django.http import JsonResponse
from base.engine.data_loader import DatabaseDataLoader
from base.engine.backtest import Backtest
from base.engine.execution import ExecutionLoader
from base.models import (StockPriceHistory, Stock,
ContinuousFuturesSeries, FuturesContract, ForexPair,
BenchmarkRecord, PortfolioEquityRecord)
from django.core.management import call_command
import re 
import pandas as pd

def get_backtest(request) -> HttpResponse:
    '''
    Renders the webpage of the Backtest
    '''
    backtest = {}

    return render(request, "backtest.html", backtest)

def backtest_graph(request) -> JsonResponse:
    '''
    This function takes in a list of inputs, runs a backtest and 
    plots the equity curve of the backtest
    '''
    if request.method == "POST":
        print("Entered backtest_graph")
        data: dict[str: any] = json.loads(request.body)
        # Cleaning data
        # data has to be converted to int/float before running backtest
        # This is done using regex to seach the string for extensionability
        int_pattern = re.compile(r'^[+-]?\d+$')
        float_pattern = re.compile(r'^[+-]?(\d+\.\d*|\.\d+)([eE][+-]?\d+)?$')
        # Dates have to be converted to datetime.date
        data["start_date"] = datetime.strptime(data["start_date"], "%Y-%m-%d").date()
        data["end_date"] = datetime.strptime(data["end_date"], "%Y-%m-%d").date()
        # Convert certain parameters to numeric and others ignore
        for key in data:
            value = data[key]
            # If the data is not in string, it does not need to be converted
            if not isinstance(value, str):
                continue
            if int_pattern.match(value):
                data[key] = int(value)
            elif float_pattern.match(value):
                data[key] = float(value)
            else:
                print(f"The value is neither matches int nor float,"
                      f" but is a string value = {value}")
            
        print("This is the data to be used in backtest"
              f" = {data}")
        # Checks if data exists, and if it does not, download it.
        # period = get_yf_period(data["start_date"], data["end_date"])
        # if data["asset_type"] == "STOCK":
        #     command = "load_stock_data"
        # elif data["asset_type"] == "FUTURES":
        #     command = "load_futures_data"
        # elif data["asset_type"] == "FOREX":
        #     command = "load_forex_data"
        # else:
        #     raise ValueError(f"Asset type is of unexpected type = {data["asset_type"]}")
        # for ticker in data["tickers"]:
        #     # data_exists does not work for all assets only stock currently
        #     if not data_exists(ticker, data["start_date"], data["end_date"]):
        #         call_command(
        #             command,
        #             symbol = ticker,
        #             period = period,
        #             interval = "1d",
        #         )
        #         print(f"Downloaded data for {ticker}")
        # For Futures, there is a step of stiching the contracts before the
        # This can be done in backtest itself not here
        # backtest can be run.
        # TODO Move this to backtest
        if data["asset_type"] == "FUTURES":
            # print("backtest_graph of backtest.py")
            # print("Building futures series")
            data["roll_days"] = 5
            data["continuous_contract_index"] = 1
            data["adjustment_method"] = "NONE"
            for i, ticker in enumerate(data['tickers']):
                create_series_configuration(ticker=data['tickers'][i],
                                            start_date=data['start_date'],
                                            end_date=data['end_date'])
                build_continuous_futures_series(ticker=data['tickers'][i],
                                                start_date=data['start_date'],
                                                end_date=data['end_date'])
                check_continuous_series(ticker=data['tickers'][i],
                                                start_date=data['start_date'],
                                                end_date=data['end_date'])
                test_rollover_event_queue(ticker=data['tickers'][i],
                                                start_date=data['start_date'],
                                                end_date=data['end_date'])

        # elif data["asset_type"] == "FOREX": TODO
        
        
            

        # Use inputs to construct some necessary parameters
        events = Queue()
        data_loader = DatabaseDataLoader(events=events, tickers=data["tickers"],
                                         start_date=data["start_date"],
                                         end_date=data["end_date"],
                                         asset_type=data["asset_type"])
        # print("Backtest not executed but params created")
        backtest = Backtest(
                            events=data_loader.events,
                            data_loader=data_loader,
                            **data
                            )
        # print("These are the attributes of the backtest obj"
        #       "In the original backtest webpage")
        # print(backtest.__dict__)
        # print(f"This is the number of days of data needed")
        # print("Backtest created")
        btr = backtest.run()
        # print("Backtest executed")
        fig = btr.get_equity_graph()
        # fig.show()
        # print("equity graph obtained")
        equity_graph_html = fig.to_html(full_html=False)
        # print("equity graph converted to html")

        # Also pass in the performance metrics.
        run_model = backtest.run_model
        run_id = backtest.get_backtest_run_id()
        metrics = btr.get_metrics()
        benchmark_record = BenchmarkRecord.objects.filter(backtest_run=run_model).values('market_value')
        market_value = list(benchmark_record)[-1]['market_value']
        print(f"This is the market value retrieved from the model {market_value}")
        portfolio_metrics = PortfolioEquityRecord.objects.filter(backtest_run_id=run_id).values(
    'total_commission', 'gross_exposure', 'net_exposure', 'gross_exposure_leverage')
        # print(pd.DataFrame(list(portfolio_metrics)).to_string())
        portfolio_metrics = list(portfolio_metrics)[-1]
        portfolio_metrics.pop("net_exposure")

        # portfolio_metrics = pd.DataFrame(list(portfolio_metrics))
        # print(f"This is the portfolio metrics retrieved from the model {portfolio_metrics}")
        # print(f"This should be the latest row of portfolio metrics {portfolio_metrics[-1]}")

        return JsonResponse({"equity_graph_html" : equity_graph_html,
                             "metrics" : metrics,
                             "run_id" : backtest.get_backtest_run_id(),
                             "portfolio_metrics" : portfolio_metrics,
                             "market_value" : market_value,
                             })
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


# Functions for obtaining S&P 500 ticker list
def get_SP500(request) -> JsonResponse:
    ''' 
    This is used in backtest.js to get a list of SP500 tickers from the db
    '''
    tickers = list(Stock.objects.values_list('ticker', flat=True))
    # print("These are the SP 500 tickers to be passed to JS")
    # print(f"\n{tickers}")
    # print(f"\nThis is the length of the tickers {len(tickers)}")
    return JsonResponse({"tickers" : tickers})

def get_futures_tickers(request) -> JsonResponse:
    ''' 
    This is used in backtest.js to get a list of futures tickers from the db
    '''
    tickers = list(set(FuturesContract.objects.values_list('root_symbol', flat=True)))
    # print("These are the futures tickers to be passed to JS")
    # print(f"\n{tickers}")
    # print(f"\nThis is the length of the tickers {len(tickers)}")
    return JsonResponse({"tickers" : tickers})

def get_forex_tickers(request) -> JsonResponse:
    ''' 
    This is used in backtest.js to get a list of forex tickers from the db
    '''
    tickers = list(set(ForexPair.objects.values_list('ticker', flat=True)))
    # print("These are the forex tickers to be passed to JS")
    # print(f"\n{tickers}")
    # print(f"\nThis is the length of the tickers {len(tickers)}")
    return JsonResponse({"tickers" : tickers})

# Functions for handling Futures backtest
def create_series_configuration(ticker: str,
                                start_date : datetime.date,
                                end_date : datetime.date,
                                # The other parameters could be adjusted in the future
                                roll_days: int = 5,
                                rollover_rule: str = "DAYS_BEFORE_EXPIRY",
                                contract_index: int = 1,
                                adjustment_method: str = "NONE") -> ContinuousFuturesSeries:
    """
    Ensures the continuous-futures configuration exists before running
    the management command.
    """
    ROOT_SYMBOL = ticker

    START_DATE = start_date
    END_DATE = end_date

    ROLL_DAYS = roll_days
    CONTRACT_INDEX = contract_index
    ADJUSTMENT_METHOD = adjustment_method
    ROLLOVER_RULE = rollover_rule

    series, created = ContinuousFuturesSeries.objects.get_or_create(
        contract_symbol=ROOT_SYMBOL,
        roll_days=ROLL_DAYS,
        rollover_rule=ROLLOVER_RULE,
        contract_index=CONTRACT_INDEX,
        adjustment_method=ADJUSTMENT_METHOD,
    )

    if created:
        print(f"Created continuous-series configuration for {ROOT_SYMBOL}.")
    else:
        print(f"Using existing continuous-series configuration for {ROOT_SYMBOL}.")

    return series

def build_continuous_futures_series(ticker: str,
                                start_date : datetime.date,
                                end_date : datetime.date,
                                # The other parameters could be adjusted in the future
                                roll_days: int = 5,) -> None:
    """
    Runs:

        python manage.py build_continuous_series

    This version assumes your command reads the saved
    ContinuousFuturesSeries configurations from the database.
    """
    ROOT_SYMBOL = ticker

    START_DATE = start_date
    END_DATE = end_date

    ROLL_DAYS = roll_days
    print("\n--- BUILDING CONTINUOUS SERIES ---")
    print(f"Root symbol: {ROOT_SYMBOL}")
    print(f"Date range: {START_DATE} to {END_DATE}")

    call_command(
        "build_continuous_futures",
        root_symbol = ROOT_SYMBOL,
        roll_days = ROLL_DAYS,
        start=START_DATE.isoformat(),
        end=END_DATE.isoformat(),
    )

    print("Continuous-series command completed.")

def check_continuous_series(ticker: str,
                                start_date : datetime.date,
                                end_date : datetime.date,
                                # The other parameters could be adjusted in the future
                                roll_days: int = 5,
                                rollover_rule: str = "DAYS_BEFORE_EXPIRY",
                                contract_index: int = 1,
                                adjustment_method: str = "NONE") -> ContinuousFuturesSeries:
    print("\n--- CONTINUOUS SERIES CHECK ---")
    ROOT_SYMBOL = ticker

    START_DATE = start_date
    END_DATE = end_date

    ROLL_DAYS = roll_days
    CONTRACT_INDEX = contract_index
    ADJUSTMENT_METHOD = adjustment_method
    ROLLOVER_RULE = rollover_rule
    try:
        series = ContinuousFuturesSeries.objects.get(
            contract_symbol=ROOT_SYMBOL,
            roll_days=ROLL_DAYS,
            rollover_rule="DAYS_BEFORE_EXPIRY",
            contract_index=CONTRACT_INDEX,
            adjustment_method=ADJUSTMENT_METHOD,
        )
    except ContinuousFuturesSeries.DoesNotExist as exc:
        raise RuntimeError(
            f"No ContinuousFuturesSeries was found for {ROOT_SYMBOL}."
        ) from exc

    print(f"Series ID: {series.pk}")
    print(f"Contract symbol: {series.contract_symbol}")
    print(f"Roll days: {series.roll_days}")
    print(f"Contract index: {series.contract_index}")
    print(f"Adjustment method: {series.adjustment_method}")

    return series

def test_rollover_event_queue(ticker: str,
                                start_date : datetime.date,
                                end_date : datetime.date,) -> None:
    """
    Tests execute_rollover independently of the full backtest.

    A long position of 5 contracts should create:

        SELL 5 old contracts
        BUY 5 new contracts
    """
    print("\n--- ROLLOVER EVENT QUEUE TEST ---")
    ROOT_SYMBOL = ticker

    START_DATE = start_date
    END_DATE = end_date
    events = Queue()

    # execute_rollover does not use DataLoader if rollover prices are
    # supplied directly, so None is sufficient for this isolated test.
    execution = ExecutionLoader(
        events=events,
        data_loader=None,
        commission=0.0,
        slippage=0.0,
    )

    execution.execute_futures_roll(
        ticker=ROOT_SYMBOL,
        datetime=START_DATE,
        from_contract="ESH25",
        to_contract="ESM25",
        from_price=6000.00,
        to_price=6005.00,
        quantity=5,
        multiplier=50.0,
    )

    if events.qsize() != 2:
        raise AssertionError(
            f"Expected 2 rollover fills, but found {events.qsize()}."
        )

    close_fill = events.get()
    open_fill = events.get()

    print("Close fill:")
    print(
        f"  {close_fill.direction} "
        f"{close_fill.quantity} "
        f"at {close_fill.fill_cost}"
    )

    print("Open fill:")
    print(
        f"  {open_fill.direction} "
        f"{open_fill.quantity} "
        f"at {open_fill.fill_cost}"
    )

    assert close_fill.type == "FILL"
    assert close_fill.direction == "SELL"
    assert close_fill.quantity == 5
    #assert close_fill.fill_cost == 6000.00

    assert open_fill.type == "FILL"
    assert open_fill.direction == "BUY"
    assert open_fill.quantity == 5
    #assert open_fill.fill_cost == 6005.00

    print("Rollover event queue test passed.")





























