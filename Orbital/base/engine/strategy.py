from abc import ABC, abstractmethod
from base.engine.data_loader import DataLoader
from base.engine import events

class Strategy(ABC):
    '''
    Description
    An abstract class that every specific strategy takes in.
    It contains a dict, such that when strategy id is passed in,
    the correct specific strategy will be chosen.

    Features
    Check that strategy book passed in contains correct arguments TODO

    Note that the arguments passed into __new__ are passed into __init__ of the subclass
    '''
    # The new dunder method runs before init, the instance it
    # returns then runs the init of the subclass
    def __new__(cls, strategy_name: str, ticker: str, data_loader: DataLoader, **kwargs):
        # Each key corresponds to a class
        strategy_dictionary = {"Moving Average Crossover" : MovingAverageCrossover
                               }

        subclass = strategy_dictionary[strategy_name]
        instance = super().__new__(subclass)
        return instance

    # All subclasses should have this
    @abstractmethod
    def generate_signal(self, market_order: events.MarketOrder) -> events.SignalEvent:
        raise NotImplementedError("calculate_signals must be implemented")

class MovingAverageCrossover(Strategy):
    '''
    Descrpition
    This strategy determines whether to "LONG" or "EXIT" based on two metrics, a fast average 
    and slow average. Fast period is shorter than slow period.

    Features
    1. If data_loader has loaded less days than slow_period, return NONE 
    (no signal event, just increment next_day)
    2. If data_loader has loaded same days as slow_period, return NONE but note current state in
    a variable.
    3. If data_loader has loaded more days than slow period, return a signal or NONE based on the
    crossover

    '''
    def __init__(self, strategy_name: str, ticker:str, data_loader: DataLoader, **strategy_book):
        self.strategy_name = strategy_name
        self.ticker = ticker
        self.fast_period = strategy_book["fast_period"]
        self.slow_period = strategy_book["slow_period"]
        self.data_loader = data_loader
        self.previous_state = None
        self.fast_above_slow = None

    def generate_signal(self, market_order: events.MarketEvent) -> events.SignalEvent:
        '''
        This method needs refactoring, the len() should be a try block
        that utilizes the error handling of the past_bars method in DL
        '''
        # If timeline shorter than slow period => no signal
        if self.data_loader.current_index < self.slow_period:
            return None

        # if timeline == slow period => no signal, but update previous state
        if self.data_loader.current_index == self.slow_period - 1:
            self.previous_state = bool(self.fast_average() > self.slow_average())
            return None
        
        # When timeline > slow poeriod. First check current state and then check for crossover
        # print(f"{self.data_loader.current_index}")
        self.fast_above_slow = bool(self.fast_average() > self.slow_average())
        # print(f"{self.fast_above_slow}")

        # 2 possible crossovers
        # fast above slow and previous state was slow above fast
        if  self.fast_above_slow and not self.previous_state:
            self.previous_state = self.fast_above_slow
            return events.SignalEvent(ticker=self.ticker,
                                      strategy_id=self.strategy_name,
                                      datetime=self.data_loader.get_current_date(),
                                      signal_type="LONG",
                                      strength=1)
        # slow above fast and previous state was fast above slow
        if not self.fast_above_slow and self.previous_state:
            self.previous_state = self.fast_above_slow
            return events.SignalEvent(ticker=self.ticker,
                                      strategy_id=self.strategy_name,
                                      datetime=self.data_loader.get_current_date(),
                                      signal_type="EXIT",
                                      strength=1)
        # This occurs when there is no crossover.
        return None


    def fast_average(self)-> float:
        '''
        get fast average
        '''
        bars = self.data_loader.get_past_bars(self.ticker, self.fast_period) # list of bars
        bars = list(map(lambda single_bar: single_bar.close, bars)) # list of floats
        return sum(bars) / len(bars)

    def slow_average(self)-> float:
        '''
        get slow average
        '''
        bars = self.data_loader.get_past_bars(self.ticker, self.slow_period) # list of bars
        bars = list(map(lambda single_bar: single_bar.close, bars)) # list of floats
        return sum(bars) / len(bars)
