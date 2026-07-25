from django.http import HttpResponse
from django.shortcuts import render
import json
from queue import Queue
from datetime import datetime
from django.http import JsonResponse
from base.engine.data_loader import DatabaseDataLoader
from base.engine.backtest import Backtest
from base.engine.distribution import Distribution
from base.engine.monte_carlo_simulation import MonteCarloSimulator
from base.models import BacktestRun
import base.engine.graph as graph
import numpy as np
import pandas as pd
import re

def mcs_graph(request) -> JsonResponse:
    # Cleaning Params
    if request.method == "POST":
        data: dict[str: any] = json.loads(request.body)
        # print(f"This is the data before cleaning = {data}")
        int_pattern = re.compile(r'^[+-]?\d+$')
        float_pattern = re.compile(r'^[+-]?(\d+\.\d*|\.\d+)([eE][+-]?\d+)?$')
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
        # print(f"Data has been cleaned and loaded successfully {data}")
        backtest_run_instance = BacktestRun.objects.get(id=data["run_id"])
        # print(backtest_run_instance.tickers)
        data_loader = DatabaseDataLoader(events=Queue(),
                                        tickers=backtest_run_instance.tickers,
                                        start_date=backtest_run_instance.start_date,
                                        end_date=backtest_run_instance.end_date,
                                        asset_type=backtest_run_instance.asset_type)
        print(f"This is what the model instance looks like {backtest_run_instance}"
            " in the mcs_graph")
        print(f"Strategy Params: {backtest_run_instance.strategy_params}")
        backtest = Backtest(events=data_loader.events,
                            tickers=backtest_run_instance.tickers,
                            start_date=backtest_run_instance.start_date,
                            end_date=backtest_run_instance.end_date,
                            strategy_name=backtest_run_instance.strategy_name,
                            data_loader=data_loader,
                            asset_type=backtest_run_instance.asset_type,
                            strength=float(backtest_run_instance.strength),
                            slippage=float(backtest_run_instance.slippage),
                            initial_capital=float(backtest_run_instance.initial_capital),
                            commission=float(backtest_run_instance.commission),
                            risk_free_rate=float(backtest_run_instance.risk_free_rate),
                            is_mcs=True,
                            **backtest_run_instance.strategy_params)
        print("Testing if backtest can run"
              f"{backtest.run().get_metrics()}"
              "Backtest ran successfully for mcs views")
        print("Printing attributes of backtest object in mcs to check if matches"
              f"{backtest.__dict__}")
        mcs = MonteCarloSimulator(backtest)

        # print(f"This is the data passed into mcs.simulate \n{data}")
        results = mcs.simulate(**data)
        fig = graph.get_monte_graph(results[0])
        mcs_html = fig.to_html(full_html=False)
        # print("This is metrics before being passed to JS")
        
        # Obtain the html of the graph for a simplified version
        # total_return_dist = Distribution(results[0])
        
        # simplified_graph = [results[1]]
        # moderate_graph =
        print(pd.DataFrame(results[1]))

        return JsonResponse({"mcs_graph_html" : mcs_html, "mcs_metrics" : results[1]})

def monte_carlo_simulation(request) -> HttpResponse:
    return render(request, "monte_carlo_simulation.html")