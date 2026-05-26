import pytest
from model_bakery import baker

from Orbital.base.engine.data_loader import DataLoader
from Orbital.base.models import StockPriceHistory
from datetime import datetime, date
from queue import Queue

@pytest.mark.django_db
def test_data_handler():
    model = StockPriceHistory._meta.get_field('stock').remote_field.model
    stock = baker.make(model, ticker='AAPL')

    baker.make(StockPriceHistory, stock=stock, date = datetime.date(2023,1,1), open_price=150.00, high_price=155.00, low_price=149.00, close_price=154.00, volume=1000000)

    events = Queue()

    data_loader = DataLoader(events, tickers=['AAPL'], start_date=datetime.date(2023,1,1), end_date=datetime.date(2023,1,2), asset_type="STOCK")

    assert 'AAPL' in data_loader.stock_data
    