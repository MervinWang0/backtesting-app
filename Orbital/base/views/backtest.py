from django.http import HttpResponse
from django.shortcuts import render
import json
from queue import Queue
from base.engine.data_loader import DatabaseDataLoader
from base.engine.backtest import Backtest

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
        data: dict[str: any] = json.loads(request.body)
        print(data)
        # Use inputs to construct some necessary parameters
        events = Queue()
        data_loader = DatabaseDataLoader(events=events, tickers=data["tickers"],
                                         start_date=data["start_date"],
                                         end_date=data["end_date"],
                                         asset_type=data["asset_type"])
        backtest_result = Backtest( 
                            events=events,
                            data_loader=data_loader,
                            **data
                            )
        btr = backtest_result.run()
        fig = btr.get_equity_graph()
        fig.to
        