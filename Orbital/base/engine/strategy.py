from base.engine.events import SignalEvent
from base.engine.data_loader import DataLoader, Bar
from base.engine.execution import ExecutionLoader
from queue import Queue
from abc import ABC,abstractmethod
from functools import wraps
from time import time

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

class Strategy(ABC):
    @abstractmethod
    def generate_signal() -> SignalEvent:
        ''' 
        Takes in ? and generates a SignalEvent
        '''

class MeanReversion(ABC):
    ''' 
    This class carries out a mean reverting trading strategy
    '''
    def __init__(self):
        super().__init__()
        
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
            strength= self.strength
        )
        