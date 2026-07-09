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


from base.models import ForexPair, ForexPriceHistory, BacktestRun, StockPriceHistory
from base.engine.backtest import Backtest
from django.utils import timezone

pair_symbol = "EURUSD=X"
DOWNLOAD_DATA = False


def get_existing_date_range(pair_symbol):
    rows = ForexPriceHistory.objects.filter(pair__ticker=pair_symbol).order_by("timestamp")

    if not rows.exists():
        raise RuntimeError(
            f"No saved data found for {pair_symbol}. Set DOWNLOAD_DATA = True once to download it."
        )

    start_date = rows.first().timestamp
    end_date = rows.last().timestamp

    print(f"Using saved {pair_symbol} data from DB.")
    print(f"Date range: {start_date} to {end_date}")
    print(f"Rows: {rows.count()}")

    return start_date, end_date

def check_saved_data(pair_symbol):
    rows = ForexPriceHistory.objects.filter(pair__ticker=pair_symbol).order_by("timestamp")

    print("\n--- DB DATA CHECK ---")
    print(f"Ticker: {pair_symbol}")
    print(f"Rows found: {rows.count()}")

    if rows.exists():
        print("First row:", rows.first().timestamp, rows.first().close_price)
        print("Last row:", rows.last().timestamp, rows.last().close_price)
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
        tickers = [pair_symbol],
    )

    asset_cache = {}
    benchmark_prices = {}
    for ticker in [pair_symbol]:
        asset_type = "FUTURES"
        asset_cache[ticker] = ForexPair.objects.filter(ticker=ticker).first()
    
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
        tickers=[pair_symbol],
        asset_type= "FOREX",
        start_date=start_date,
        end_date=end_date,
        strategy_name="MovingAverageCross",
        strength=1.0,
        slippage=0.0,
        initial_capital=100_000.0,
        strategy_params={
            "short_window": 20,
            "long_window": 100,
        },
        comission=0.0,
        # The management command already built it.
        build_continuous_series=False,
    )

    print("\nRunning backtest...")
    result = backtest.run()
    print("Backtest finished.")

    return result


if __name__ == "__main__":
    check_saved_data(pair_symbol)

    if DOWNLOAD_DATA:
        # df = download_data()
        # start_date, end_date = save_data_to_db(df)
        print("wrong")
    else:
        start_date, end_date = get_existing_date_range(pair_symbol)

    run_backtest(start_date, end_date)

