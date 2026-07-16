from base.engine.events import SignalEvent
from base.engine.data_loader import DataLoader, Bar
from base.engine.execution import ExecutionLoader
from queue import Queue
from abc import ABC,abstractmethod
from functools import wraps
from time import time
import numpy as np
import pandas as pd
from dataclasses import dataclass
def timed(f):
    '''
    This function is used to time any function
    Usage syntax
    @timed
    def funct()
    '''

    @wraps(f)
    def wrapper(*args, **kwds):
        start = time()
        result = f(*args, **kwds)
        elapsed = time() - start
        print(f"function {f.__name__} took {elapsed}")
        return result
    return wrapper

# Config classes to reduce the number of args passed into
# functions at once
@dataclass
class RSIConfig:
    window: int
    ticker: str
    prev_AG: float = None
    prev_AL: float = None
    oversold: int = 30
    overbought: int = 70

@dataclass
class BollingerConfig:
    window: int
    ticker: str

@dataclass
class ZConfig:
    window: int
    ticker: str
    lower: float = -2
    upper: float = 2

class Strategy(ABC):
    def __init__(self, data_loader: DataLoader):
        ''' 
        Some attributes are common to all trading strategies.
        1. data_loader

        Methods
        Generally methods to calculate metrics return None if 
        They cannot be calculated based on various conditions
        '''
        self.data_loader = data_loader
        self.tickers: list[str] = data_loader.get_tickers()




    @abstractmethod
    def generate_signal(self) -> SignalEvent:
        ''' 
        Takes in nothing and generates a SignalEvent
        '''

    # These methods are used to calculate metrics
    def get_rolling_z_score(self, window: int, ticker: str) -> float:
        '''
        Calculate and return the Z score over the pass window days.
        
        Formula: (Today's Close - Rolling Mean) / Rolling Std
        '''
        if window == 1:
            raise ValueError("Z score is undefined for 1 day window, as std = 0,"
                             "Causing a divide by 0 error")
        today_close = self.data_loader.get_current_bar_value(ticker=ticker, value_type="close")
        rolling_std = self.get_rolling_std(ticker=ticker, window=window)
        rolling_mean = self.get_rolling_mean(ticker=ticker, window=window)
        return (today_close - rolling_mean) / rolling_std

    def get_window_bars(self, ticker: str, window: int) -> list[Bar]:
        ''' 
        Obtain a list of past bars based on a window
        '''
        # print("generating signal for ticker", ticker)
        try:
            window_bars = self.data_loader.get_past_bars(ticker, window)
        except ValueError:
            # print(f"Not enough bars yet for {ticker}. Need {window}.")
            window_bars = None
        return window_bars

    def get_rsi(self, window: int, ticker: str, prev_AG: float = None,
                prev_AL: float = None) -> tuple[int, float, float]:
        ''' 
        Calculate the RSI of a ticker based on a window. Requires previous average to
        determine new average.

        prev_AG and prev_AL are None when the days loaded is less than the window

        output is (RSI, new_AG, new_AL)
        '''
        window_bars = self.get_window_bars(ticker, window)
        if window_bars == None:
            return window_bars
        closes = [bar.close for bar in window_bars]
        # Consider the case when window first matches days loaded, first AG AL calculated
        if window == self.data_loader.get_days_loaded():
            # Testing
            # print("This is the original prices \n")
            # print(closes)
            # print("This is the difference in prices \n")
            # print(pd.DataFrame(closes).diff().dpona())

            # Note that this has one less element
            price_change = pd.Series(closes).diff().dropna()

            # Basically obtaining mean, but dividing by n + 1 
            new_ag = abs(price_change[price_change > 0].sum() / window)
            new_al = abs(price_change[price_change < 0].sum() / window)
            rs = new_ag / new_al
            rsi = 100 - (100/ (1 + rs))
            return (int(rsi), float(new_ag), float(new_al))

        # print(self.data_loader.get_current_change(ticker))
        # old avg * n-1 + new_change / n
        current_change = self.data_loader.get_current_change(ticker)
        new_ag = abs((prev_AG * (window - 1)) + (current_change / window))
        new_al = abs((prev_AL * (window - 1)) + (current_change / window))
        rs = new_ag / new_al
        rsi = 100 - (100/ (1 + rs))
        return (int(rsi), float(new_ag), float(new_al))

    def get_bollinger_bands(self, window: int, ticker: str) -> tuple[float, float, float]:
        ''' 
        Returns a tuple of (low band, middle band, high band) prices for the day
        '''
        middle_band = self.get_rolling_mean(window, ticker)
        sigma = self.get_rolling_std(window, ticker)
        print(f"this is the sigma for the day {sigma}")
        if middle_band is None or sigma is None:
            return None
        return (middle_band - 2 * sigma, middle_band,
                middle_band + 2 * sigma)

    def get_rolling_mean(self, window: int, ticker: str ) -> float:
        ''' 
        Return the historical mean calculated for the past window days.
        Uses the close price. Returns None if days traded < window.
        '''
        window_bars = self.get_window_bars(ticker, window)
        if window_bars is None:
            return None
        closes = [bar.close for bar in window_bars]
        return sum(closes) / len(closes)

    def get_rolling_std(self, window: int, ticker: str ) -> float:
        ''' 
        Return the historical std calculated for the past window days.
        Uses the close price. Returns None if days traded < window.
        '''
        window_bars = self.get_window_bars(ticker, window)
        if window_bars is None:
            return None
        closes = [bar.close for bar in window_bars]
        return np.std(closes)

    # These methods obtain some sort of indicator from the metrics
    def get_rsi_signal(self, config: RSIConfig) -> str:
        ''' 
        Based on some parameters, determine if market condition is
        overbought or oversold
        '''
        rsi_value = self.get_rsi(window=config.window, prev_AG=config.prev_AG,
                            prev_AL=config.prev_AL, ticker=config.ticker)
        if rsi_value < config.oversold:
            return "oversold"
        elif rsi_value > config.overbought:
            return "overbought"
        return "neutral"

    def get_bollinger_signal(self, config: BollingerConfig):
        ''' 
        Based on some parameters, determine if market condition is
        overbought or oversold
        '''
        bands = self.get_bollinger_bands(window=config.window,
                                         ticker=config.ticker)
        lower_band = bands[0]
        upper_band = bands[2]
        curr_price = self.data_loader.get_current_bar_value(
            ticker=config.ticker, value_type='close')
        if curr_price < lower_band:
            return "oversold"
        elif curr_price > upper_band:
            return "overbought"
        return "neutral"

    def get_z_score_signal(self, config: ZConfig) -> str:
        ''' 
        Based on some parameters, determine if market condition is
        overbought or oversold
        '''
        z = self.get_rolling_z_score(window=config.window,
                                     ticker=config.ticker)
        if z < config.lower:
            return "oversold"
        elif z > config.upper:
            return "overbought"
        return "neutral"

    def obtain_market_condition(self, logic: str, rsi_config: RSIConfig,
                                bollinger_config: BollingerConfig,
                                z_config: ZConfig):
        ''' 
        logic is used to combine signals to buy/sell

        and => buy/sell when market conditions are same
        majority => buy/sell based on majority
        '''
        condition = None
        if logic == "and":
            condition = 3
        elif logic == "majority":
            condition = 2
        else:
            raise ValueError("The logic is not correctly specified"
                             " for obtaining market condition")
        # Result stores the buy/sell dict stores extra args
        result : tuple[str, dict] = ()

        # market conditions stores the condition of the market
        # as determined by different indicators
        market_conditions: list[str] = []

        market_conditions.append(self.get_rsi_signal(rsi_config))
        market_conditions.append(
            self.get_bollinger_signal(bollinger_config))
        market_conditions.append(self.get_z_score_signal(z_config))

        count = 0
        for market in market_conditions:
            if market == 'overbought':
                count += 1
            elif market == 'oversold':
                count += 1
        
        

class MeanReversion(Strategy):
    ''' 
    This class carries out a mean reverting trading strategy
    '''
    def __init__(self, data_loader: DataLoader, rsi_config):
        super().__init__(data_loader)

    def generate_signal(self):
        return super().generate_signal()
        
class MovingAverageCross:
    def __init__(self, data_loader: DataLoader, events: Queue,
                 tickers: list[str], short_window, long_window, strength: float = 1.0):
        self.data_loader = data_loader
        self.events = events
        self.tickers = tickers
        self.short_window = short_window
        self.long_window = long_window
        self.strength = strength

        self.previous_signal = {ticker: None for ticker in tickers}

    def calculate_SMA(self, bars: list[Bar]) -> float:
        closes = [bar.close for bar in bars]
        return sum(closes) / len(closes)

    # @timed
    def generate_signal(self, ticker: str) -> SignalEvent:
        #print("generating signal for ticker", ticker)
        try:
            long_window_bars = self.data_loader.get_past_bars(ticker, self.long_window)
        except ValueError:
            #print(f"Not enough bars yet for {ticker}. Need {self.long_window}.")
            return None
        short_window_bars = long_window_bars[-self.short_window:]
        long_SMA = self.calculate_SMA(long_window_bars)
        short_SMA = self.calculate_SMA(short_window_bars)

        current_datetime = self.data_loader.get_current_datetime()
        if short_SMA > long_SMA:
            current_signal = "LONG"
        elif short_SMA < long_SMA:
            current_signal = "SHORT"
        else:
            current_signal = None
        
        prev_signal = self.previous_signal.get(ticker)

        if current_signal == prev_signal:
            return None
        self.previous_signal[ticker] = current_signal
        if current_signal is None:
            return None

        return SignalEvent(
            ticker = ticker,
            datetime= current_datetime,
            signal_type= current_signal,
            strength= self.strength,
            asset_type=self.data_loader.asset_type
        )
        