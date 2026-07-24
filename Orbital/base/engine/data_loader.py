import os
import sys
import django
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Orbital.settings")
django.setup()

from base.engine.events import MarketEvent
from base.models import (StockPriceHistory, FuturesPriceHistory,
                         ForexPriceHistory, ContinuousFuturesPriceHistory)
from dataclasses import dataclass
from datetime import datetime, timedelta, date
import datetime
from queue import Queue
from abc import ABC, abstractmethod
from typing import Optional
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
#Dataclass to represent a single bar of data, each data contains
#  the ticker, date, open, high, low, close, volume and asset type
@dataclass(frozen=True)
class Bar:
    '''
    Attributes are ticker, date, OHLVC, asset type
    '''
    symbol: str
    date: datetime.date
    open: float
    high: float
    low: float
    close: float
    volume: int
    asset_type: str
    
    #For forex
    base_currency: Optional[str] = None
    quote_currency: Optional[str] = None

    #For futures
    contract_multiplier: Optional[float] = None
    source_contract_code: Optional[str] = None
    is_roll: Optional[bool] = False
    roll_from_contract_code: Optional[str] = None
    roll_to_contract_code: Optional[str] = None
    roll_from_price: Optional[float] = None
    roll_to_price: Optional[float] = None

    @staticmethod
    def to_bar(stock_price_history):
        '''
        Converts a stock price history instance to a Bar
        '''
        return Bar(
            symbol= stock_price_history.stock.ticker,
            date = stock_price_history.date,
            open = stock_price_history.open_price,
            high = stock_price_history.high_price,
            low = stock_price_history.low_price,
            volume = stock_price_history.volume,
            close = stock_price_history.close_price,
            asset_type = "STOCK"
        )
    def __str__(self):
        return (f"open = {self.open},\nhigh = {self.high},\nlow = {self.low},\n" +
                f"volume = {self.volume},\n close = {self.close}")


class DataLoader(ABC):
    '''
    Description
    The DataLoader is a general class that contains methods to interact with some form
    of asset data.

    Attributes (Only cover non trivial ones)
    1. timeline: list[datetime.date], sorted. Stores valid dates for retrieving bars
    2. current_index: int. Used with timeline to get a specific bar/ bars

    Methods (Publicly available)
    1. get_current_date() => The day the data loader is looking at
    2. should_continue_bt() => is the day within the start and end date inclusive of backtest
    3. next_day() => increment the day the data loader looks at by one
    4. get_current_bar(ticker) => returns the current bar
    5. get_current_bar_value(ticker, bar_attribiute) => returns a specified attribute
    of the current bar
    6. get_tickers() => returns the list of tickers the data loader uses
    7. get_past_bars(num:int) => returns the num past bars inclusive of current sorted

    Advanced Features #TODO
    Implement a more robust timeline building function, the current function
    considers all dates where at least one stock traded as a valid date.
    '''
    # @timed
    def __init__(self, events : Queue, tickers: list[str], start_date: datetime.date,
                 end_date: datetime.date, asset_type : str):
        self.events = events
        self.tickers = tickers
        self.start_date = start_date
        self.end_date = end_date
        self.asset_type = asset_type

        #Data structures to hold loaded data
        #This will store all available data for each stock
        self.stock_data: dict[str, list[Bar]] = {}

        #This will store data from the beginning up till the current time index for each stock
        self.latest_stock_data: dict[str, list[Bar]] = {}

        #Optimisation: Fast lookup for each ticker for each date in the bar data
        self.bar_lookup: dict[str, dict[datetime.date, Bar]] = {}

        #Time index for backtest loop, increments whenever next_day is called
        #curr_index tracks index of current bar in the timeline,
        # curr_datetime tracks the date of the current bar
        self.curr_index = -1
        self.curr_datetime = None
        self.timeline: list[datetime.time] = []

        #Tracks if end_date is reached
        self.continue_bt = True

        self.load_data()

    @abstractmethod
    def load_data(self) -> None:
        '''
        initializes the variables necessary for the data loader to operate
        '''

    @staticmethod
    def date_to_datetime(date: datetime.date) -> datetime:
        return datetime.combine(date, datetime.min.time())

    def load_forex_data(self, forex_pair_code: str) -> list[Bar]:
        bars: list[Bar] = []
        rows = (ForexPriceHistory.objects.filter(pair__ticker =forex_pair_code, timestamp__range=(self.start_date, self.end_date))
                .select_related("pair")
                .order_by("timestamp")
                .values("pair__ticker", "pair__base_currency","pair__quote_currency", "timestamp", "open_price", "high_price", "low_price", "close_price", "volume"))
        
        for record in rows:
            bars_date = self.date_to_datetime(record["timestamp"])
            bars.append(Bar(
                symbol = record["pair__ticker"],
                date = bars_date,
                open = float(record["open_price"]),
                high = float(record["high_price"]),
                low = float(record["low_price"]),
                close = float(record["close_price"]),
                volume = record["volume"],
                asset_type = "FOREX",
                base_currency = record["pair__base_currency"],
                quote_currency = record["pair__quote_currency"],
            ))
        return bars

    def load_futures_data(self, contract_code: str) -> list[Bar]:
        futures_history = (ContinuousFuturesPriceHistory.objects.filter(series__contract_symbol=contract_code,
                                                                        series__contract_index = 1,
                                                                        date__range=(self.start_date, self.end_date),)
                                                            .select_related("series", "source_contract",
                                                                            "roll_from_contract", "roll_to_contract")
                                                            .order_by("date"))
        bars = []
        previous_contract_code = None
        visited_dates = set()
        for record in futures_history:
            # if record.date in visited_dates:
            #     raise RuntimeError(f"Duplicate date found in futures data for {contract_code}: {record.date}")
            visited_dates.add(record.date)
            current_contract_code = record.source_contract.contract_code
            is_roll = previous_contract_code is not None and current_contract_code != previous_contract_code
            from_contract = record.roll_from_contract.contract_code if record.roll_from_contract is not None else previous_contract_code if is_roll else None
            to_contract = record.roll_to_contract.contract_code if record.roll_to_contract is not None else current_contract_code if is_roll else None
            if is_roll:
                print(f"Roll detected on {record.date}: {from_contract} -> {to_contract}")
                print(
                    "FUTURES LOAD:",
                    record.date,
                    "series_id=",
                    record.series.id,
                    "source=",
                    current_contract_code,
                    "previous=",
                    previous_contract_code,
                    "detected_roll=",
                    is_roll,
                    "db_roll_from=",
                    (
                        record.roll_from_contract.contract_code
                        if record.roll_from_contract else None
                    ),
                    "db_roll_to=",
                    (
                        record.roll_to_contract.contract_code
                        if record.roll_to_contract else None
                    ),
                )
            bars.append(Bar(
                symbol = contract_code,
                date = record.date,
                open = float(record.open_price),
                high = float(record.high_price),
                low = float(record.low_price),
                close = float(record.close_price),
                volume = record.volume,
                asset_type = "FUTURES",
                source_contract_code = current_contract_code,
                contract_multiplier = float(record.source_contract.tick_multiplier),
                is_roll = is_roll,
                roll_from_contract_code = from_contract,
                roll_to_contract_code = to_contract,
                roll_from_price = float(record.roll_from_price) if record.roll_from_price is not None else None,
                roll_to_price = float(record.roll_to_price) if record.roll_to_price is not None else None
            ))
            previous_contract_code = current_contract_code
        return bars

    def next_day(self) -> None:
        '''
        points the data loader to the next valid day. And adds a bar to
        events queue.
        '''
        #Increment time index 
        next_index = self.curr_index + 1
        #If time index exceeds data length, end backtest loop

        market_event_needed = False
        if next_index >= len(self.timeline):
            self.continue_bt = False
            return
        
        self.curr_index = next_index
        self.curr_datetime = self.timeline[self.curr_index]

        for ticker in self.tickers:
            bar = self.bar_lookup[ticker].get(self.curr_datetime)
            
            #If bar exists, reveal bar to the backtester 
            if bar:
                self.latest_stock_data[ticker].append(bar)
                market_event_needed = True
                
        if market_event_needed:      
            self.events.put(MarketEvent(datetime=self.curr_datetime))


    def get_current_bar(self, ticker: str) -> Bar:
        '''
        Returns the current bar
        '''
        if ticker not in self.latest_stock_data or not self.latest_stock_data[ticker]:
            raise ValueError(f"No data available for ticker: {ticker} at the current time index.")
        return self.latest_stock_data[ticker][-1]


    def get_past_bars(self, ticker: str, num: int = 1) -> list[Bar]:
        '''
        Takes in a ticker and a number, returns the past num bars of the
        ticker in a list, sorted from oldest to latest

        Inclusive of current day
        '''
        # print(len(self.latest_stock_data[ticker]))
        # print(f"This should be a number {num}")
        if ticker not in self.latest_stock_data:
            raise ValueError(f"Not enough data available for ticker: {ticker} at the current time index.")
        if len(self.latest_stock_data[ticker]) < num:
            raise ValueError(f"The stock data for this date: {self.curr_datetime} is outside"
                             f" is outside range of the data loader: {self.end_date}")
        return self.latest_stock_data[ticker][-num:]


    # def get_latest_bar_datetime(self, ticker: str) -> datetime.date:
    #     latest_bar = self.get_latest_bar(ticker)
    #     return latest_bar.Date


    #returns specific value type (open, high, low, close, volume) of the latest bar for a given ticker
    def get_current_bar_value(self, ticker: str, value_type: str) -> float:
        '''
        Returns a specific attribute of the current bar
        '''
        latest_bar = self.get_current_bar(ticker)
        if not hasattr(latest_bar, value_type):
            raise ValueError(f"Invalid value type: {value_type}."
                             f" Must be one of 'open', 'high', 'low', 'close', 'volume'.")
        return getattr(latest_bar, value_type)

  
    #returns current date time of the backtester
    def get_current_datetime(self) -> datetime.date:
        '''
        Returns the current date the data loader is point to
        '''
        return self.curr_datetime

    # def should_continue_bt(self):
    #     return self.curr_index < len(self.timeline)


    def get_timeline(self) -> list[datetime.date]:
        '''
        Getter for timeline, returns a list of all dates where at least
        one stock is open for trading.
        '''
        return self.timeline

    def get_days_loaded(self) -> int:
        ''' 
        Returns an integer representing the number of days of data loaded
        '''
        return self.curr_index + 1

    def get_stock_data(self) -> dict[str, list[Bar]]:
        '''
        Returns the universe of stock data from start to end
        for interested tickers.
        '''
        return self.stock_data
    
    def get_tickers(self) -> list[str]:
        ''' 
        Returns a list of the tickers used by this data loader
        '''
        return self.tickers

    def get_current_change(self, ticker: str) -> float:
        ''' 
        Returns the change in the close price of the previous day and
        current day of a specified ticker
        '''
        return (self.stock_data[ticker][self.curr_index].close -
                self.stock_data[ticker][self.curr_index - 1].close)


class MCSDataLoader(DataLoader):
    '''
    This is a data laoder that initializes its attributes using a list of bars.

    Notes
    There are only 2 differences from DatabaseDataLoader
    1. The difference in its init method is that it takes in an additional parameter,
    which is data, a list of bars. Which represents historical data.
    2. The difference in load_stock_data, it still returns a list[Bar], just that
    the data is from input not from database.

    load_data is the exact same as in DatabaseDataLoader (I think this can be
    placed in parent class and have load stock data be the abstract method)
    '''
    # This init method has been overriden, creating attributes to allow load stock
    # data to work. Logic: Create necessary attribute => call parent constructor
    def __init__(self, events : Queue, tickers: list[str], start_date: datetime.date,
                 end_date: datetime.date, asset_type : str, data: dict[str, list[Bar]]):
        # self.data stores the dict[str, list[Bar]] passed as input,
        self.data = data.copy()
        super().__init__(events=events,
                         tickers=tickers,
                         start_date=start_date,
                         end_date=end_date,
                         asset_type=asset_type)
        

    def load_stock_data(self, ticker: str) -> list[Bar]:
        '''
        This method is created for load_data to remain 
        '''
        return self.data[ticker]
        
    def load_data(self) -> None:
        '''
        This load data method takes in a list of bars and uses it to initalize internal
        attributes. More specifically, self.stock_data, self.latest_stock_data, self.bar_lookup,
        self.timeline
        '''
        #track which date has already been visited
        date_times_visited = set()

        for ticker in self.tickers:
            if self.asset_type == "STOCK":
                main_bar = self.load_stock_data(ticker)
            elif self.asset_type == "FUTURES":
                main_bar = self.load_futures_data(ticker)
            else:
                raise ValueError(f"Unsupported asset type: {self.asset_type}")
            
            if not main_bar:
                raise  ValueError(f"No data found for ticker: {ticker} in the specified date range.")
            
            self.stock_data[ticker] = main_bar
            self.latest_stock_data[ticker] = []
            self.bar_lookup[ticker] = {}

            #populate bar lookup for fast access to bars by date
            for bar in main_bar:
                self.bar_lookup[ticker][bar.date] = bar
                date_times_visited.add(bar.date)

        self.timeline = sorted(date_times_visited)


class DatabaseDataLoader(DataLoader):
    '''
    This data laoder initializes its attributes using a connection to a 
    postgreSQL database
    '''


    def load_stock_data(self, ticker: str) -> list[Bar]:
        bars: list[Bar] = []
        rows = (StockPriceHistory.objects.filter(stock__ticker=ticker,
                                                 date__range=(self.start_date, self.end_date))
                .order_by("date")
                .values("stock__ticker", "date", "open_price",
                        "high_price", "low_price", "close_price", "volume"))

        for record in rows:
            bars_date = record["date"]
            bars.append(Bar(
                symbol = record["stock__ticker"],
                date = bars_date,
                open = float(record["open_price"]),
                high = float(record["high_price"]),
                low = float(record["low_price"]),
                close = float(record["close_price"]),
                volume = record["volume"],
                asset_type = "STOCK"
            ))
        return bars

    def load_data(self) -> None:
        #track which date has already been visited
        date_times_visited = set()

        for ticker in self.tickers:
            if self.asset_type == "STOCK":
                main_bar = self.load_stock_data(ticker)
            elif self.asset_type == "FUTURES":
                main_bar = self.load_futures_data(ticker)
            elif self.asset_type == "FOREX":
                main_bar = self.load_forex_data(ticker)
            else:
                raise ValueError(f"Unsupported asset type: {self.asset_type}")
            
            if not main_bar:
                raise  ValueError(f"No data found for ticker: {ticker} in the specified date range.")
            
            self.stock_data[ticker] = main_bar
            self.latest_stock_data[ticker] = []
            self.bar_lookup[ticker] = {}

            #populate bar lookup for fast access to bars by date
            for bar in main_bar:
                self.bar_lookup[ticker][bar.date] = bar
                date_times_visited.add(bar.date)

        self.timeline = sorted(date_times_visited)

if __name__ == "__main__":
    start_date = datetime.fromisoformat("2021-05-24").date()
    end_date = datetime.fromisoformat("2021-06-07").date()

    # Tests if changing DataLoader to an abstract class has broken the current
    # implementation, it has not, still works.
    # data_loader = DatabaseDataLoader(Queue(), ["AAPL"], start_date,
    #                          end_date, "STOCK")
    # data_loader.next_day()
    # print(f"This is the current bar = {data_loader.get_current_bar("AAPL")}")

    # Testing to see if MCSDataLoader works as expected
    data_loader = MCSDataLoader(Queue(), ["AAPL"], start_date,
                             end_date, "STOCK",{"AAPL" : [Bar("AAPL",
                                                              start_date,
                                                              100,
                                                              110,
                                                              90,
                                                              105,
                                                              100,
                                                              "STOCK"),
                                                              Bar("AAPL",
                                                              start_date + timedelta(1),
                                                              100,
                                                              110,
                                                              90,
                                                              105,
                                                              100,
                                                              "STOCK")]
                                                              })
    # Initialization works, I'm going to assume the other methods work as
    # they don't need to retrieve data.
    # data_loader.next_day()
    # print(f"This is the current bar = {data_loader.get_current_bar("AAPL")}") 

    # Next day doesn't seem to be working, going to test if methods inherited work.
    # data_loader.next_day()
    # print(f"This is the current bar = {data_loader.get_current_bar("AAPL")}") 
    # data_loader.next_day()
    # print(f"This is the next bar = {data_loader.get_current_bar("AAPL")}") 
    # print(data_loader.events.qsize())

    # Next day appears to work, but I need to check if events queue is updated.