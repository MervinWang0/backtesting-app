from typing import Optional

from base.engine.events import MarketEvent
from base.models import StockPriceHistory, FuturesPriceHistory, ForexPriceHistory
from dataclasses import dataclass
import datetime
from queue import Queue


#Dataclass to represent a single bar of data, each data contains the ticker, date, open, high, low, close, volume and asset type
@dataclass(frozen=True)
class Bar:
    '''
    Attributes are ticker, date, OHLVC, asset type
    '''
    symbol: str
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: Optional[int]
    asset_type: str

    base_currency: Optional[str] = None
    quote_currency: Optional[str] = None

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


class DataLoader:
    '''
    Description
    Each instance of the class is a pointer to a specific bar,
    with methods to get current date, increment date and obtain
    values of the bar.

    Attributes (Only cover non trivial ones)
    1. timeline: list[datetime.date], sorted. Stores valid dates for retrieving bars
    2. current_index: int. Used with timeline to get a specific bar/ bars
    3. data: dict{ticker: dict{date: Bar}}

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
     
    def __init__(self, events : Queue, tickers: list[str], start_date: datetime.date, end_date: datetime.date, asset_type : str):
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
        #curr_index tracks index of current bar in the timeline, curr_datetime tracks the date of the current bar
        self.curr_index = -1
        self.curr_datetime = None
        self.timeline: list[datetime.time] = []

        #Tracks if end_date is reached
        self.continue_bt = True

        self.load_data()

    @staticmethod
    def date_to_datetime(date: datetime.date) -> datetime.datetime:
        return datetime.datetime.combine(date, datetime.time.min)


    def load_stock_data(self, ticker: str) -> list[Bar]:
        bars: list[Bar] = []
        rows = (StockPriceHistory.objects.filter(stock__ticker=ticker, date__range=(self.start_date, self.end_date))
                .order_by("date")
                .values("stock__ticker", "date", "open_price", "high_price", "low_price", "close_price", "volume"))

        for record in rows:
            bars_date = self.date_to_datetime(record["date"])
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
    
    def load_forex_date(self, forex_pair_code: str) -> list[Bar]:
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
    
    
    # def load_futures_data(self, contract_code: str) -> list[Bar]:
    #     futures_history = FuturesPriceHistory.objects.filter(contracts__contract_code=contract_code, date__range=(self.start_date, self.end_date)).order_by("date")
    #     bars = []
    #     for record in futures_history:
    #         bars.append(Bar(
    #             Symbol = record.contracts.contract_code,
    #             Date = record.date,
    #             Open = float(record.open_price),
    #             High = float(record.High_price),
    #             Low = float(record.low_price),
    #             Close = float(record.close_price),
    #             Volume = record.volume,
    #             Asset_type = "Futures"
    #         ))
    #     return bars


    
    def load_data(self) -> None:
        #track which date has already been visited
        date_times_visited = set()

        for ticker in self.tickers:
            if self.asset_type == "STOCK":
                main_bar = self.load_stock_data(ticker)
            elif self.asset_type == "FUTURES":
                main_bar = self.load_futures_data(ticker)
            elif self.asset_type == "FOREX":
                main_bar = self.load_forex_date(ticker)
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


    def next_day(self) -> None:
        '''
        points the data loader to the next valid day.
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
        '''
        if ticker not in self.latest_stock_data or len(self.latest_stock_data[ticker]) < num:
            raise ValueError(f"Not enough data available for ticker: {ticker} at the current time index.")
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
            raise ValueError(f"Invalid value type: {value_type}. Must be one of 'Open', 'High', 'Low', 'Close', 'Volume'.")
        return getattr(latest_bar, value_type)
    
    
    #returns current date time of the backtester 
    def get_current_datetime(self) -> datetime.date:
        '''
        Returns the current date the data loader is point to
        '''
        return self.curr_datetime
    
    # def should_continue_bt(self):
    #     return self.curr_index < len(self.timeline)
    




