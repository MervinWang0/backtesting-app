from dataclasses import dataclass
from datetime import timedelta, datetime
from base.models import StockPriceHistory

# Bar is a fundamental data structure representing data of an asset
@dataclass
class Bar:
    '''
    Attributes are ticker, date, OHLVC, asset type
    '''
    ticker: str
    date: datetime.date
    open: float
    high: float
    low: float
    volume: int
    close: float
    asset_type: str

    @staticmethod
    def to_bar(stock_price_history)-> Bar:
        '''
        Converts a stock price history instance to a Bar
        '''
        return Bar(
        ticker = stock_price_history.stock.ticker,
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
    def __init__(self, start_date: datetime.date, end_date: datetime.date, tickers: list[str],
                 asset_type: str):
        # Straight-forward initializations
        self.start_date = start_date
        self.end_date = end_date
        self.tickers = tickers
        self.asset_type = asset_type

        # Initializations needed to track time
        self.timeline: list[datetime.date] = DataLoader.__build_timeline(start_date,
                                                                         end_date, tickers)
        self.current_index = 0

        # Dictionary for fast access of bars
        self.data = DataLoader.__load_data(start_date, end_date, tickers)

    @staticmethod
    def __build_timeline(start_date: datetime.date, end_date: datetime.date,
                         tickers: list[str]) -> list[datetime.date]:
        '''
        Description
        This method is prefixed by "__" to indicate is should not be called outside the class.
        This method is used to create an attribute of the data loader instance.
        This method is a simplified approach without error handling 
        in the case of a date not being valid. (Some tickers made not trade that day).
        But it accounts for all days in which at least one stock trades.
        (Alternate method is all days in which all stocks trade)
        Logic
        1. Filter StockPriceHistory to get entries with relevant date and tickers
        2. Get every distinct date and return it in a sorted list

        Note
        Currently it only returns the dates of which all tickers trade on
        '''
        # dates stores the valid dates
        dates = []

        # Filtering
        sph_queryset = StockPriceHistory.objects # Returns the Manager of model
        # filter to get date range within start and end
        filtered_date = sph_queryset.filter(date__range=(start_date, end_date))
        # filter to get interested stocks. Uses syntax for FK lookup
        filtered_tickers = filtered_date.filter(stock__ticker__in=tickers)

        # gets distinct dates of queryset into a list
        dates = list(filtered_tickers.values_list("date", flat=True).distinct())
        return sorted(dates) # sorts datetimes from oldest to latest

    @staticmethod
    def __load_data(start_date: datetime.date, end_date: datetime.date,
                         tickers: list[str]) -> dict[str:dict[datetime.date: Bar]]:
        '''
        Description
        This function creates a nested dict for fast access of bars
        '''
        # Filtering for detailed comments check __build_timeline
        sph_queryset = StockPriceHistory.objects
        filtered_date = sph_queryset.filter(date__range=(start_date, end_date))
        filtered_tickers = filtered_date.filter(stock__ticker__in=tickers)

        # First create dict[ticker : empty dict]
        # Then for each entry, place the bar with the correct inner and outer key
        result = {ticker: dict() for ticker in tickers}
        for stock_price_history in filtered_tickers:
            ticker = stock_price_history.stock.ticker
            result[ticker][stock_price_history.date] = Bar.to_bar(stock_price_history)  
        return result

    def get_current_date(self) -> datetime.date:
        '''
        Returns the current date the data loader is point to
        '''
        # print(f"{self.current_index}, {len(self.timeline)}")
        return self.timeline[self.current_index]

    def should_continue_bt(self) -> bool:
        '''
        returns true if current_date <= end_date
        '''
        # Originally I used self.get_current_date() <= self.end_date
        # But the fail case causes list index out of range bug in get_current_date
        return self.current_index < len(self.timeline)

    def next_day(self) -> None:
        '''
        points the data loader to the next valid day.
        Doesn't contain any error handling now, as it is only used in backtest while loop
        Which uses should_continue_bt as a condition
        '''
        self.current_index += 1

    def get_current_bar(self, ticker: str) -> Bar:
        '''
        Returns the current bar
        '''
        return self.data[ticker][self.get_current_date()]

    def get_current_bar_value(self, ticker: str, bar_attribiute: str)-> str|float|int|datetime.date:
        '''
        Returns a specific attribute of the current bar
        '''
        return getattr(self.get_current_bar(ticker), bar_attribiute)

    def get_tickers(self) -> list[str]:
        '''
        getter for tickers
        '''
        return self.tickers

    def get_past_bars(self, ticker: str, num: int) -> list[Bar]:
        '''
        Takes in a ticker and a number, returns the past num bars of the
        ticker in a list, sorted from oldest to latest
        '''
        # Type check that num is not negative, nor greater than start to current
        # current index + 1 = nth day of backtesting
        if not isinstance(num,int) or num <= 0 or num > self.current_index + 1:
            raise ValueError("The past bars must be a positive int and less than days loaded")

        # Quick check if num = 1 returns current index, num = 2, returns current_index -1
        # and current_index
        first_day = (self.current_index + 1) - num # inclusive 
        last_day = self.current_index # inclusive 
        result = []
        for index in range(first_day, last_day + 1): # range excludes last index
            result.append(self.data[ticker][self.timeline[index]])
        return result
