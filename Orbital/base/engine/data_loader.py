class DataLoader:
    # DataLoader takes in a time range, loads the historical stock data from
    # that time frame into a dict, each key having the format {date : HistoricalStockData}
    # Then functions return desired information
    def __init__(self, time_start:str, time_end:str):
        self.time_index = time_start
        self.time_end = time_end

    

