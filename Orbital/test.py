
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

TICKER = "AAPL"
DOWNLOAD_DATA = False

from base.models import StockPriceHistory
from base.engine.backtest import Backtest
from base.engine.data_loader import DatabaseDataLoader

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

    backtest = Backtest(
        asset_type="STOCK",
        events=events,
        tickers=[TICKER],
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2025, 12, 31),
        strategy_name="MovingAverageCross",
        strength=1.0,
        slippage=0.0,
        initial_capital=100000.0,
        short_window= 20,
        long_window= 100,
        data_loader=DatabaseDataLoader(events=events,
                                                    tickers=["AAPL", 'GOOGL'],
                                                    start_date=start_date,
                                                    end_date=end_date,
                                                    asset_type="STOCK"),
        commission=0.0,
    )

    print("\nRunning backtest...")
    result = backtest.run()
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

    btr = run_backtest(start_date, end_date)
    btr.get_equity_graph().show()