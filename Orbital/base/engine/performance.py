import os
import sys
import django
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Orbital.settings")
django.setup()

import plotly.express as px
from queue import Queue
from base.engine.monte_carlo_simulation import MonteCarloSimulatior
from datetime import datetime
from base.engine.data_loader import DatabaseDataLoader
from base.engine.backtest import Backtest
import pandas as pd
from base.engine.distribution import Distribution

class MetricsCalculator():
    '''
    Description
    This class contains methods to calculate various metrics to analyze
    a trading strategy. It only requires an equity curve to be initialized.

    Features
    
    Methods
    get_total_return(self) -> float. overall % gain/loss
    get_CAGR(self) -> float. annualised return accounting for compounding
    get_daily_returns_distribution -> distribution
    get_monthly_returns_distribution -> distribution
    get_yearly_returns_distribution -> distribution

    Implementation Details
    returns are stored in natural log form as it makes calculating of returns
    over a preiod faster.

    '''
    def __init__(self, equity_record):
        self.returns_distribution = Distribution(list(map(lambda record: record.)))

