from django.http import HttpResponse
from django.shortcuts import render
import json
from queue import Queue
from datetime import datetime
from django.http import JsonResponse
from base.engine.data_loader import DatabaseDataLoader
from base.engine.backtest import Backtest
from base.engine.monte_carlo_simulation import MonteCarloSimulator

def monte_carlo_simulation(request) -> HttpResponse:
    return render(request, "monte_carlo_simulation.html")