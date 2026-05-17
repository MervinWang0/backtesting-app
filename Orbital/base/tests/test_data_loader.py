import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Orbital.settings")
django.setup()


from base.engine.data_loader import DataLoader


DataLoaderObj = DataLoader("2025-09-18", "2026-10-10", ["AAPL","COST"])
print(DataLoaderObj.get_latest_bar("AAPL"), DataLoaderObj.get_latest_bars(), DataLoaderObj.get_time_index(), sep ='\n')
DataLoaderObj.next_day()
print(DataLoaderObj.get_latest_bar("AAPL"), DataLoaderObj.get_latest_bars(), DataLoaderObj.get_time_index(), sep ='\n')