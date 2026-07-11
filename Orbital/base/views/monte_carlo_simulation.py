from django.http import HttpResponse
from django.shortcuts import render
import json
from queue import Queue
from datetime import datetime
from django.http import JsonResponse
from base.engine.data_loader import DatabaseDataLoader
from base.engine.backtest import Backtest
from base.engine.monte_carlo_simulation import MonteCarloSimulator
from base.models import BacktestRun
import base.engine.graph as graph

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
    # print(f"This is the type of numbers in database = {type(backtest_run_instance.initial_capital)}")
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
    # print(f"This is the backtest created {backtest}")
    mcs = MonteCarloSimulator(backtest)
    
    results = mcs.simulate(**data)
    fig = graph.get_monte_graph(results)
    mcs_html = fig.to_html(full_html=False)
    return JsonResponse({"mcs_graph_html" : mcs_html})

def monte_carlo_simulation(request) -> HttpResponse:
    return render(request, "monte_carlo_simulation.html")

# def backtest_graph(request) -> HttpResponse:
#     '''
#     This function takes in a list of inputs, runs a backtest and 
#     plots the equity curve of the backtest
#     '''
#     if request.method == "POST":
#         data: dict[str: any] = json.loads(request.body)
#         # Cleaning data
#         # Extra conversion, during debugging short/long window being float causes
#         # The backtest runs to fail
#         int_params = ['short_window', 'long_window']
#         # Dates have to be converted to datetime.date
#         data["start_date"] = datetime.strptime(data["start_date"], "%Y-%m-%d")
#         data["end_date"] = datetime.strptime(data["end_date"], "%Y-%m-%d")
#         # Convert certain parameters to numeric and others ignore
#         for key in data:
#             try:
#                 if key in int_params:
#                     data[key] = int(data[key])
#                 else:
#                     data[key] = float(data[key])
#             except Exception:
#                 pass
#         # print(data)
#         # Use inputs to construct some necessary parameters
#         events = Queue()
#         data_loader = DatabaseDataLoader(events=events, tickers=data["tickers"],
#                                          start_date=data["start_date"],
#                                          end_date=data["end_date"],
#                                          asset_type=data["asset_type"])
#         print("Backtest not executed but params created")
#         backtest = Backtest(
#                             events=data_loader.events,
#                             data_loader=data_loader,
#                             **data
#                             )
#         # print(Backtest.__dict__)
#         print("Backtest created")
#         btr = backtest.run()
#         print("Backtest executed")
#         fig = btr.get_equity_graph()
#         # fig.show()
#         print("equity graph obtained")
#         equity_graph_html = fig.to_html(full_html=False)
#         print("equity graph converted to html")

#         # Also pass in the performance metrics.
#         metrics = btr.get_metrics()
#         return JsonResponse({"equity_graph_html" : equity_graph_html,
#                              "metrics" : metrics, "run_id" : backtest.get_backtest_run_id()})