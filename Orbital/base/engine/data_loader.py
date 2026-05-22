from datetime import timedelta, datetime
from base.models import StockPriceHistory
from dataclasses import dataclass

# Bar is a fundamental data structure representing data of an asset 
@dataclass  
class Bar:
    ticker: str
    date: datetime.date
    open: float
    high: float
    low: float
    close: float
    volume: int
    asset_type: str

    @staticmethod
    def to_bar(self, stock_price_history)-> Bar:
        return Bar(
        ticker = ticker,
        date = stock_price_history.date,
        open = stock_price_history.open_price,
        high = stock_price_history.high_price,
        low = stock_price_history.low_price,
        close = stock_price_history.close_price,
        volume = stock_price_history.volume,
        asset_type = "STOCK"
        )




# The DataLoader class should be initalized with a time range, a list of stocks and an asset type
class DataLoader:

    def __init__(self, start_time: date, end_time: date, tickers: list):
        # time is stored as date object as interval of historical data is by day
        self.start_time = start_time
        self.end_time = end_time
        self.tickers = tickers

        # current time is used to index the object
        self.current_time = start_time

        # filtering. Returns a queryset from start to end date inclusive of stocks in list
        # Mostly for easy referencing
        self.data = data_queryset = (
                                    StockPriceHistory.objects # Queryset of SPH
                                    .filter(date__range=(self.start_time, self.end_time))
                                    .filter(stock__ticker__in=self.tickers)
                                    )
    # These are the methods of the class
    # Constructors
    #   load_data => creates an instance of the data loader based on input passed
    # Accessors/Mutators
    #   For stocks
    #       get current bar, get bars from start to current inclusive, get current date, increment current date
    # Printers
    # Predicates
    # Operations

    # Constructor
    @classmethod
    def load_data(cls, asset_type: str, **kwargs)-> DataLoader:
        if asset_type == "STOCK":
            return DataLoader(kwargs["start_date"], kwargs["end_date"], kwargs["tickers"])
        elif asset_type == "FUTURES":
            pass

    # get get the current bar of a specific stock
    def get_current_bar(self, ticker:str) -> Bar:
        # dict key is string, has to convert date to string
        return get_bar_historical(ticker)[self.current_time.strftime("%Y-%m-%d")]

    # get current bars of inclusive of all stocks of interests
    def get_current_bars(self) -> list[Bar]: 
        return get_current_bars_selection(self.tickers)

    # gets current bars based on a list of tickers
    def get_current_bars_selection(self, tickers: list[str])-> list[Bar]:
        result = list()
        for ticker in tickers:
            result.append(get_current_bar(ticker))
        return result

    # stores the start to current inclusive bars of a stock in a dict
    def get_bar_historical(self, ticker: str)-> dict["date" : Bar]:
        # gets a query set of the start to current date rows of a stock
        stock_price_history = (self.data
                                    .filter(stock__ticker=ticker)
                                    .filter(date__range=(self.start_time, self.current_time))
                              )
        return {"date" : to_bar(stock_price) for stock_price in stock_price_history}
    
    # stores all bars of all stocks of interest in dict{"ticker" : dict{"date" : Bar}}
    def get_bars_historical(self)-> dict["ticker" : dict["date" : Bar]]:
        return get_bars_historical_selection(self.tickers)

    def get_bars_historical_selection(self, tickers: list[str])-> dict["ticker" : dict["date" : Bar]]:
        result = dict()
        for ticker in tickers:
            result[ticker] = get_bar_historical(ticker)
        return result

    # just returns the current time of the object
    def get_current_time(self) -> date:
            return self.current_time
    
    # increments the current date   
    def next_day(self) -> void:
        self.current_time += timedelta(days=1)



    

