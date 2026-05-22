from ..models import StockPriceHistory, FuturesPriceHistory
from dataclasses import dataclass
import datetime
from queue import Queue



@staticmethod
def date_to_datetime(date: datetime.date) -> datetime.datetime:
    return datetime.datetime.combine(date, datetime.time.min)


#Dataclass to represent a single bar of data, each data contains the ticker, date, open, high, low, close, volume and asset type
@dataclass(frozen=True)
class Bar:
    Symbol : str
    Date : datetime.date
    Open : float
    High : float
    Low : float
    Close : float
    Volume : int
    Asset_type : str


class DataLoader:
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

        self.data = self.load_data()

        #backtest condition
        self.continue_bt = True


    def load_stock_data(self, ticker: str) -> list[Bar]:
        bars: list[Bar] = []
        rows = (StockPriceHistory.objects.filter(stock__ticker=ticker, date__range=(self.start_date, self.end_date))
                .order_by("date")
                .values("date", "open_price", "high_price", "low_price", "close_price", "volume"))

        for record in rows:
            bars_date = self.date_to_datetime(record["date"])
            bars.append(Bar(
                Symbol = record["stock__ticker"],
                Date = bars_date,
                Open = float(record["open_price"]),
                High = float(record["high_price"]),
                Low = float(record.low_price),
                Close = float(record.close_price),
                Volume = record.volume,
                Asset_type = "STOCK"
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
    
    
    def load_data(self) -> list[Bar]:
        #track which date has already been visited
        date_times_visited = set()

        for ticker in self.tickers:
            if self.asset_type == "Stock":
                main_bar = self.load_stock_data(ticker)
            elif self.asset_type == "Futures":
                main_bar = self.load_futures_data(ticker)
            else:
                raise ValueError(f"Unsupported asset type: {self.asset_type}")
            
            if not main_bar:
                raise  ValueError(f"No data found for ticker: {ticker} in the specified date range.")
            
            self.stock_data[ticker] = main_bar

            #populate bar lookup for fast access to bars by date
            for bar in main_bar:
                self.bar_lookup[ticker][bar.Date] = bar
                date_times_visited.add(bar.Date)

        self.timeline = sorted(date_times_visited)


    def next_day(self) -> None:
        #Increment time index 
        next_index = self.curr_index + 1
        #If time index exceeds data length, end backtest loop
        if next_index >= len(self.data):
            self.continue_bt = False
            return
        
        self.curr_index = next_index
        self.curr_datetime = self.timeline[self.curr_index]

        for ticker in self.tickers:
            bar = self.bar_lookup[ticker].get(self.curr_datetime)
            
            #If bar exists, reveal bar to the backtester 
            if bar:
                self.latest_stock_data[ticker].append(bar)


    def get_latest_bar(self, ticker: str) -> Bar:
        if ticker not in self.latest_stock_data or not self.latest_stock_data[ticker]:
            raise ValueError(f"No data available for ticker: {ticker} at the current time index.")
        return self.latest_stock_data[ticker][-1]


    def get_latest_bars(self, ticker: str, n: int = 1) -> list[Bar]:
        if ticker not in self.latest_stock_data or len(self.latest_stock_data[ticker]) < n:
            raise ValueError(f"Not enough data available for ticker: {ticker} at the current time index.")
        return self.latest_stock_data[ticker][-n:]
    

    def get_latest_bar_datetime(self, ticker: str) -> datetime.date:
        latest_bar = self.get_latest_bar(ticker)
        return latest_bar.Date
    

    #returns specific value type (open, high, low, close, volume) of the latest bar for a given ticker
    def get_latest_bar_value(self, ticker: str, value_type: str) -> float:
        latest_bar = self.get_latest_bar(ticker)
        if not hasattr(latest_bar, value_type):
            raise ValueError(f"Invalid value type: {value_type}. Must be one of 'Open', 'High', 'Low', 'Close', 'Volume'.")
        return getattr(latest_bar, value_type)
    
    
    #returns current date time of the backtester 
    def get_current_datetime(self) -> datetime.date:
        return self.curr_datetime
    




