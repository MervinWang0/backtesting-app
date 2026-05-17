# The rough idea of the data loader class is that it will be initialized with a time range, and a list of stocks
# Then internally stre StockPriceHistory in some data structure and retrieve info with functions
from datetime import timedelta, datetime
from base.models import StockPriceHistory

class DataLoader:
    # DataLoader takes in a time range, and list of stocks of interest
    # It loads the historical stock data from relevant data into some convenient data structure
    # Then functions return desired information
    def __init__(self, time_start:str, time_end:str, stocks : list):
        self.time_start = time_start
        self.time_end = time_end
        self.stocks = stocks
        self.data = StockPriceHistory.objects.none() #just creates an empty queryset
        # Initially time_index should point to first day
        self.time_index = time_start
        # filtering. Returns a queryset from start to end date inclusive of stocks in list
        self.data = data_queryset = (
                                    StockPriceHistory.objects # Queryset of SPH
                                    .filter(date__range=(self.time_start, self.time_end))
                                    .filter(stock__ticker__in=self.stocks)
                                    )
            
    def get_latest_bar(self, ticker:str) -> SPH: # output is single SPH
            return (self.data
                        .filter(date=self.time_index)
                        .filter(stock__ticker=ticker)
                    )

    def get_latest_bars(self) -> list: # output is list of SPH
            return (self.data
                        .filter(date=self.time_index)
                    )

    def get_time_index(self) -> datetime:
            return self.time_index

    def next_day(self) -> void:
        # converts date in str to datetime, increments, then converts back to str
        self.time_index = datetime.strptime(self.time_index, "%Y-%m-%d")
        self.time_index += timedelta(days=1)
        self.time_index = datetime.strftime(self.time_index, "%Y-%m-%d") 

    def __str__(self):
            return f"This is the data_queryset = {list(data_queryset)}"


    

