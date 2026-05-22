import pytest
from base.models import StockPriceHistory, Stock
from datetime import datetime

# Create some date objects
date1 = datetime.strptime("2026-01-01", "%Y-%m-%d")
date2 = datetime.strptime("2026-01-02", "%Y-%m-%d") 
date3 = datetime.strptime("2026-01-03", "%Y-%m-%d")  

# Create Database pytest fixtures
@pytest.fixture
def StockPriceHistory_db(db):
    stock1 = Stock.objects.create(ticker="AAPL", name="APPLE", industry="Electronics", is_active=true)
    stock2 = Stock.objects.create(ticker="COST", name="COSTCO", industry="SUPERMARKT", is_active=true)
    stock3 = Stock.objects.create(ticker="BTT", name="BUTT", industry="Electronics", is_active=true)

    StockPriceHistory.objects.create(stock=stock1, date=date1, open_price=10, high_price=12,
                                    low_price=9, volume=1000, close_price=11)

    StockPriceHistory.objects.create(stock=stock2, date=date1, open_price=10, high_price=12,
                                    low_price=9, volume=1000, close_price=11)

    StockPriceHistory.objects.create(stock=stock3, date=date1, open_price=10, high_price=12,
                                    low_price=9, volume=1000, close_price=11)

    StockPriceHistory.objects.create(stock=stock3, date=date2, open_price=10, high_price=12,
                                    low_price=9, volume=1000, close_price=11)

    StockPriceHistory.objects.create(stock=stock3, date=date3, open_price=10, high_price=12,
            low_price=9, volume=1000, close_price=11)