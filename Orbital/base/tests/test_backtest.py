from datetime import datetime
from base.engine.backtest import BackTest

start_date = datetime.fromisoformat("2024-08-16").date()
end_date = datetime.fromisoformat("2025-10-17").date()
backtest_instance = BackTest(start_date=start_date,
                    end_date=end_date,
                    tickers=["AAPL"],
                    asset_type="STOCK",
                    strategy_name="Moving Average Crossover",
                    initial_capital=10000.00,
                    risk_free_rate=0,
                    slow_period=200,
                    fast_period=50,
                    comission=5,
                    slippage=0.01)

result = backtest_instance.run()
print(type(result))
