from base.engine.data_loader import *
from datetime import datetime, date

# create some dates
date1 = datetime.strptime("2026-01-01", "%Y-%m-%d")
date2 = datetime.strptime("2026-01-02", "%Y-%m-%d") 
date3 = datetime.strptime("2026-01-03", "%Y-%m-%d")  

# I need to create a test database to test the functions


# Test load_data
# First test with good inputs
def test_load_data_good():
    assert type(DataLoader.load_data("STOCK", start_date=date1, end_date=date3, tickers=["AAPL", "COST", "BTT"])) == DataLoader

# Test next_day
# Test get_latest_bar
# Test get_latest_bars
# Test get_latest_bar_datetime
# Test get_latest_bar_value
# get_current_datetime















# import django
# import os

# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Orbital.settings")
# django.setup()


# from base.engine.data_loader import DataLoader


# DataLoaderObj = DataLoader("2025-09-18", "2026-10-10", ["AAPL","COST"])
# print(DataLoaderObj.get_latest_bar("AAPL"), DataLoaderObj.get_latest_bars(), DataLoaderObj.get_time_index(), sep ='\n')
# DataLoaderObj.next_day()
# print(DataLoaderObj.get_latest_bar("AAPL"), DataLoaderObj.get_latest_bars(), DataLoaderObj.get_time_index(), sep ='\n')