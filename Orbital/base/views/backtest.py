from django.http import HttpResponse
from django.shortcuts import render
import json
from queue import Queue
from datetime import datetime
from django.http import JsonResponse
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
        # print(data)
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
                             "metrics" : metrics})
        