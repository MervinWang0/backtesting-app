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
from datetime import datetime
from base.engine.data_loader import DatabaseDataLoader
from base.engine.backtest import Backtest
import pandas as pd
import numpy as np

class Distribution():
    '''
    Description
    This class is used to represent data in the form of a probability
    distribution.

    Features
    1. Data is inserted at initialization and cannot be added to 
    2. Methods to analyse the data stored.
    3. Data is treated as an empirical distribution (each value is
    equally likely to occur)

    Attributes
    1. data: np.array, stores raw form of data

    Methods
    get_median
    get_mean
    get_std
    get_variance
    get_min
    get_max

    cdf(value) -> float. return probability outcome is <= value
    ppf(probability) -> float. Returns the value at a percentile


    '''

    def __init__(self, data: list[float]):
        self.data = np.sort(np.array(data))

    def get_median(self) -> float:
        return np.median(self.data)

    def get_mean(self) -> float:
        return np.mean(self.data)

    def get_std(self) -> float:
        return np.std(self.data)

    def get_variance(self) -> float:
        return np.var(self.data)

    def get_min(self) -> float:
        return np.min(self.data)

    def get_max(self) -> float:
        return np.max(self.data)

    def cdf(self, value: float) -> float:
        '''
        Takes in a number, checks the number of elements <= number
        and returns the probability aka num of elements / len(arr)
        '''
        return np.searchsorted(self.data, value, side='right') / len(self.data)

    def ppf(self, probability: float) -> float:
        '''
        Takes in prob, returns number at percentile. Because empirical
        distribution is discrete, the case where the prob does not correspond
        to number has to be considered. In this case, the design choice
        is to use the nearest value in the distribution. 
        '''
        return np.percentile(self.data, probability * 100, method="nearest")

    def distribution_graph(self) -> px.Figure:
        df = pd.DataFrame(self.data)
        return px.histogram(df)
if __name__ == "__main__":
    test = Distribution([1,2,3,4,5,6,7,8,9,10,])
    print(f"mean = {test.get_mean()}")
    print(f"CDF = {test.cdf(3)}")
    print(f"PPF = {test.ppf(0.75)}")
