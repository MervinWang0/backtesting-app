# The rough idea of the data loader class is that it will be initialized with a time range, and a list of stocks
# Internally, the class filters using ORM of HistoricalStockData to obtain a dictionary of a dictionary
# {date : {stock_ticker : HistoricalStockData}}
# dict[date] = dict of stocks of interest for that day
# dict[date]["AAPL"] = HSD of apple on day

class DataLoader:
    # DataLoader takes in a time range, and list of stocks of interest
    # It loads the historical stock data from relevant data into a dict of form {date : HistoricalStockData}
    # Then functions return desired information
    def __init__(self, time_start:str, time_end:str, stocks : list):
        self.time_index = time_start
        self.time_end = time_end
        self.stocks = stocks
        self.dict = dict()
        # filtering


    

