
import os
import sys
from pathlib import Path
from queue import Queue
from datetime import datetime

import django
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Orbital.settings")
django.setup()


from base.models import Stock, StockPriceHistory, BacktestRun
from base.engine.backtest import Backtest


TICKER = "AAPL"
DOWNLOAD_DATA = False


def get_existing_date_range(ticker):
    rows = StockPriceHistory.objects.filter(stock__ticker=ticker).order_by("date")

    if not rows.exists():
        raise RuntimeError(
            f"No saved data found for {ticker}. Set DOWNLOAD_DATA = True once to download it."
        )

    start_date = rows.first().date
    end_date = rows.last().date

    print(f"Using saved {ticker} data from DB.")
    print(f"Date range: {start_date} to {end_date}")
    print(f"Rows: {rows.count()}")

    return start_date, end_date

def check_saved_data(ticker):
    rows = StockPriceHistory.objects.filter(stock__ticker=ticker).order_by("date")

    print("\n--- DB DATA CHECK ---")
    print(f"Ticker: {ticker}")
    print(f"Rows found: {rows.count()}")

    if rows.exists():
        print("First row:", rows.first().date, rows.first().close_price)
        print("Last row:", rows.last().date, rows.last().close_price)
    else:
        print("No saved rows found.")


def run_backtest(start_date, end_date):
    events = Queue()
    backtest_run = BacktestRun.objects.create(
        #user = User,
        run_name = "test",
        strategy_name= "MovingAverageCross",
        asset_type = "STOCK",
        start_date = start_date,
        end_date = end_date,
        initial_capital = 100000.0,
        end_equity = 0.0,
        fixed_quantity = 5,
        tickers = [TICKER],
    )

    asset_cache = {}
    benchmark_prices = {}
    for ticker in [TICKER]:
        asset_type = "STOCK"
        asset_cache[ticker] = Stock.objects.filter(ticker=ticker).first()
    
    benchmark_qs = StockPriceHistory.objects.filter(
        stock__ticker = "VOO",
        date__gte = start_date,
        date__lte = end_date,
    )
    benchmark_prices = {record.date: float(record.close_price) for record in benchmark_qs}

    backtest = Backtest(
        backtest_run= backtest_run,
        asset_cache= asset_cache,
        benchmark_prices= benchmark_prices, 
        events=events,
        tickers=[TICKER],
        asset_type= "STOCK",
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2025, 12, 31),
        strategy_name="MovingAverageCross",
        strength=1.0,
        slippage=0.0,
        initial_capital=100000.0,
        strategy_params={
            "short_window": 20,
            "long_window": 100,
        },
        comission=0.0,
    )

    print("\nRunning backtest...")
    result, benchmark = backtest.run()
    print("Backtest finished.")
    return result


if __name__ == "__main__":
    check_saved_data(TICKER)

    if DOWNLOAD_DATA:
        # df = download_data()
        # start_date, end_date = save_data_to_db(df)
        print("wrong")
    else:
        start_date, end_date = get_existing_date_range(TICKER)

    run_backtest(start_date, end_date)