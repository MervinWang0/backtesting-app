import os
import sys
import django
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Orbital.settings")
django.setup()

import plotly.express as px
# from queue import Queue
# from datetime import datetime
# from base.engine.data_loader import DatabaseDataLoader
# from base.engine.backtest import Backtest
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

    def __init__(self, data: list[float] | np.array):
        if isinstance(data, np.ndarray):
            self.data = data
        elif isinstance(data, list):
            self.data = np.sort(np.array(data))
        else:
            raise ValueError("Distribution can only be created with list/np.ndarray"
                             f" not the type passed, which is = {type(data)}")

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

    def ppf(self, percentile: float) -> float:
        '''
        Takes in prob, returns number at percentile. Because empirical
        distribution is discrete, the case where the prob does not correspond
        to number has to be considered. In this case, the design choice
        is to use the nearest value in the distribution. 
        '''
        return np.percentile(self.data, percentile, method="nearest")

    def get_imp_metrics(self) -> dict[str, float]:
        ''' 
        Returns useful metrics, like the basic stats and value at some percentiles
        '''
        result = {}
        result.update(Median=self.get_median())
        result.update(Mean=self.get_mean())
        result.update(Variance=self.get_variance())
        result.update(Minimum=self.get_min())
        result.update(Maximum=self.get_max())
        result.update({"10th Percentile" : self.ppf(10)})
        result.update({"25th Percentile" : self.ppf(25)})
        result.update({"50th Percentile" : self.ppf(50)})
        result.update({"75th Percentile" : self.ppf(75)})
        result.update({"90th Percentile" : self.ppf(90)})
        print(f"This is the {result}\n")
        return result

    def distribution_graph(self) -> px.Figure:
        df = pd.DataFrame(self.data)
        return px.histogram(df)
if __name__ == "__main__":
    test = Distribution([1,2,3,4,5,6,7,8,9,10,])
    print(f"mean = {test.get_mean()}")
    print(f"CDF = {test.cdf(3)}")
    print(f"PPF = {test.ppf(0.75)}")
