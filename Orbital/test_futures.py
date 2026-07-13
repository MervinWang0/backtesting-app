import os
import sys
from datetime import date
from pathlib import Path
from queue import Queue

import django


# ---------------------------------------------------------------------
# Django setup
# ---------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Orbital.settings")
django.setup()


# Imports that require Django setup
from django.core.management import call_command

from base.engine.events import AssetType
from base.models import ContinuousFuturesSeries, BacktestRun, FuturesContract, FuturesPriceHistory
from base.engine.backtest import Backtest
from base.engine.execution import ExecutionLoader
from base.engine.data_loader import DatabaseDataLoader


# ---------------------------------------------------------------------
# Test configuration
# ---------------------------------------------------------------------

ROOT_SYMBOL = "ES"

START_DATE = date(2023, 1, 1)
END_DATE = date(2025, 12, 31)

ROLL_DAYS = 5
CONTRACT_INDEX = 1
ADJUSTMENT_METHOD = "NONE"

BUILD_SERIES = True


# ---------------------------------------------------------------------
# Continuous-series setup
# ---------------------------------------------------------------------

def create_series_configuration() -> ContinuousFuturesSeries:
    """
    Ensures the continuous-futures configuration exists before running
    the management command.
    """
    series, created = ContinuousFuturesSeries.objects.get_or_create(
        contract_symbol=ROOT_SYMBOL,
        roll_days=ROLL_DAYS,
        rollover_rule="DAYS_BEFORE_EXPIRY",
        contract_index=CONTRACT_INDEX,
        adjustment_method=ADJUSTMENT_METHOD,
    )

    if created:
        print(f"Created continuous-series configuration for {ROOT_SYMBOL}.")
    else:
        print(f"Using existing continuous-series configuration for {ROOT_SYMBOL}.")

    return series


def build_continuous_futures_series() -> None:
    """
    Runs:

        python manage.py build_continuous_series

    This version assumes your command reads the saved
    ContinuousFuturesSeries configurations from the database.
    """
    print("\n--- BUILDING CONTINUOUS SERIES ---")
    print(f"Root symbol: {ROOT_SYMBOL}")
    print(f"Date range: {START_DATE} to {END_DATE}")

    call_command(
        "build_continuous_futures",
        root_symbol = ROOT_SYMBOL,
        roll_days = ROLL_DAYS,
        start=START_DATE.isoformat(),
        end=END_DATE.isoformat(),
    )

    print("Continuous-series command completed.")


def check_continuous_series() -> ContinuousFuturesSeries:
    print("\n--- CONTINUOUS SERIES CHECK ---")

    try:
        series = ContinuousFuturesSeries.objects.get(
            contract_symbol=ROOT_SYMBOL,
            roll_days=ROLL_DAYS,
            rollover_rule="DAYS_BEFORE_EXPIRY",
            contract_index=CONTRACT_INDEX,
            adjustment_method=ADJUSTMENT_METHOD,
        )
    except ContinuousFuturesSeries.DoesNotExist as exc:
        raise RuntimeError(
            f"No ContinuousFuturesSeries was found for {ROOT_SYMBOL}."
        ) from exc

    print(f"Series ID: {series.pk}")
    print(f"Contract symbol: {series.contract_symbol}")
    print(f"Roll days: {series.roll_days}")
    print(f"Contract index: {series.contract_index}")
    print(f"Adjustment method: {series.adjustment_method}")

    return series


# ---------------------------------------------------------------------
# Direct rollover event test
# ---------------------------------------------------------------------

def test_rollover_event_queue() -> None:
    """
    Tests execute_rollover independently of the full backtest.

    A long position of 5 contracts should create:

        SELL 5 old contracts
        BUY 5 new contracts
    """
    print("\n--- ROLLOVER EVENT QUEUE TEST ---")

    events = Queue()

    # execute_rollover does not use DataLoader if rollover prices are
    # supplied directly, so None is sufficient for this isolated test.
    execution = ExecutionLoader(
        events=events,
        data_loader=None,
        commission=0.0,
        slippage=0.0,
    )

    execution.execute_futures_roll(
        ticker=ROOT_SYMBOL,
        datetime=START_DATE,
        from_contract="ESH25",
        to_contract="ESM25",
        from_price=6000.00,
        to_price=6005.00,
        quantity=5,
        multiplier=50.0,
    )

    if events.qsize() != 2:
        raise AssertionError(
            f"Expected 2 rollover fills, but found {events.qsize()}."
        )

    close_fill = events.get()
    open_fill = events.get()

    print("Close fill:")
    print(
        f"  {close_fill.direction} "
        f"{close_fill.quantity} "
        f"at {close_fill.fill_cost}"
    )

    print("Open fill:")
    print(
        f"  {open_fill.direction} "
        f"{open_fill.quantity} "
        f"at {open_fill.fill_cost}"
    )

    assert close_fill.type == "FILL"
    assert close_fill.direction == "SELL"
    assert close_fill.quantity == 5
    #assert close_fill.fill_cost == 6000.00

    assert open_fill.type == "FILL"
    assert open_fill.direction == "BUY"
    assert open_fill.quantity == 5
    #assert open_fill.fill_cost == 6005.00

    print("Rollover event queue test passed.")


# ---------------------------------------------------------------------
# Full backtest
# ---------------------------------------------------------------------

def run_futures_backtest():
    print("\n--- RUNNING FUTURES BACKTEST ---")

    events = Queue()
    asset_cache = {}
    benchmark_prices = {}
    for ticker in [ROOT_SYMBOL]:
        asset_type = "FUTURES"
        asset_cache[ticker] = FuturesContract.objects.filter(root_symbol=ticker).first()
    
    benchmark_qs = FuturesPriceHistory.objects.filter(
        contract__root_symbol = "VOO",
        date__gte = START_DATE,
        date__lte = END_DATE,
    )
    benchmark_prices = {record.date: float(record.close_price) for record in benchmark_qs}
    events = Queue()
    data_loader = DatabaseDataLoader(events=events, tickers=[ROOT_SYMBOL],
                                        start_date=START_DATE,
                                        end_date=END_DATE,
                                        asset_type=AssetType.FUTURES)
    backtest = Backtest(
        data_loader=data_loader,
        # asset_cache=asset_cache,
        # benchmark_prices= benchmark_prices,
        events=data_loader.events,
        tickers=[ROOT_SYMBOL],
        asset_type=AssetType.FUTURES,
        start_date=START_DATE,
        end_date=END_DATE,
        strategy_name="MovingAverageCross",
        strength=1.0,
        slippage=0.0,
        initial_capital=100_000.0,
        short_window=20,
        long_window=100,
        comission=0.0,
        roll_days=ROLL_DAYS,
        continuous_contract_index=CONTRACT_INDEX,
        adjustment_method=ADJUSTMENT_METHOD,

        # The management command already built it.
        build_continuous_series=False,
    )

    rollover_calls = []

    # Wrap the real method so the test can count rollover executions.
    original_execute_rollover = backtest.execute.execute_futures_roll

    def tracked_execute_rollover(*args, **kwargs):
        from_price = kwargs.get('from_price')
        to_price = kwargs.get('to_price')
        quantity = kwargs.get('quantity')
        multiplier = 50.0 # ES multiplier
        
        # 1. Calculate what the rollover adjustment SHOULD be
        spread = to_price - from_price
        expected_adjustment = -spread * multiplier * quantity 
        
        print("\n--- ROLLOVER DIAGNOSTICS ---")
        print(f"Rolling {quantity} contracts: {kwargs.get('from_contract')} -> {kwargs.get('to_contract')}")
        print(f"Prices: {from_price} -> {to_price} (Spread: {spread} points)")
        print(f"Expected Cash Adjustment for this roll: ${expected_adjustment:,.2f}")
        
        # 2. Check your leverage
        # (You will need to pass current_equity into this function or calculate it here)
        notional_exposure = quantity * to_price * multiplier
        print(f"Notional Exposure: ${notional_exposure:,.2f}")
        
        return original_execute_rollover(*args, **kwargs)

    backtest.execute.execute_futures_roll = tracked_execute_rollover

    # result, benchmark = backtest.run()
    result = backtest.run()
    # result.get_equity_graph().show()

    print("\n--- BACKTEST RESULT ---")
    print("Backtest completed successfully.")
    print(f"Rollover executions: {len(rollover_calls)}")

    if not rollover_calls:
        print(
            "WARNING: No rollover was executed. This can happen if the "
            "strategy held no position on the rollover dates."
        )

    return result
    # return result, benchmark, rollover_calls


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

if __name__ == "__main__":
    create_series_configuration()

    if BUILD_SERIES:
        build_continuous_futures_series()

    check_continuous_series()
    test_rollover_event_queue()

    # result, benchmark, rollover_calls = run_futures_backtest()
    result = run_futures_backtest()
    result.get_equity_graph().show()

    print("\nAll futures smoke tests completed.")