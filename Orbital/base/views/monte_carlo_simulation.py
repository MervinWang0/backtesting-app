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

def mcs_graph(request) -> JsonResponse:
    # Cleaning Params
    if request.method == "POST":
        data: dict[str: any] = json.loads(request.body)
        int_params = ["num_sims", "run_id"]
        checkbox_params = ["is_regime_switching", "is_jump_diffusion", "is_t"]
        # The checkboxes have to converted from "on" to True
        for param_id in data:
            if param_id in checkbox_params and data[param_id] == "on":
                data[param_id] = True
            elif param_id in checkbox_params:
                data[param_id] = False
        print(data)
        try:
            for param_id in data:
                if param_id in int_params and param_id not in checkbox_params:
                    data[param_id] = int(data[param_id])
                elif param_id not in checkbox_params:
                    data[param_id] = float(data[param_id])
        except (ValueError, TypeError) as e:
            raise ValueError("The input should have been convertible to float/int") from e
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
    mcs = MonteCarloSimulator(backtest)

    # print(f"This is the data passed into mcs.simulate \n{data}")
    results = mcs.simulate(**data)
    fig = graph.get_monte_graph(results[0])
    mcs_html = fig.to_html(full_html=False)
    print("This is metrics before being passed to JS")
    
    # Obtain the html of the graph for a simplified version
    # total_return_dist = Distribution(results[0])
    
    # simplified_graph = [results[1]]
    # moderate_graph =
    print(pd.DataFrame(results[1]))

    return JsonResponse({"mcs_graph_html" : mcs_html, "mcs_metrics" : results[1]})

def monte_carlo_simulation(request) -> HttpResponse:
    return render(request, "monte_carlo_simulation.html")