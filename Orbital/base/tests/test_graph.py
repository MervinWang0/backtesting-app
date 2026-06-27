from base.engine import graph
from base.engine.backtest import Backtest
from base.engine.data_loader import DatabaseDataLoader
from datetime import datetime
from queue import Queue

if __name__ == "__main__":
    start_date = datetime.fromisoformat("2021-05-24").date()
    end_date = datetime.fromisoformat("2023-06-07").date()
    data_loader = DatabaseDataLoader(Queue(), ["AAPL"], start_date,
                             end_date, "STOCK")
    backtest = Backtest(
                        events=data_loader.events,
                        tickers=["AAPL"],
                        start_date=start_date,
                        end_date=end_date,
                        asset_type="STOCK",
                        strategy_name="MovingAverageCross",
                        short_window= 10,
                        long_window= 100,
                        data_loader=data_loader
                        )
    test = backtest.run()
    stock_data = backtest.data_loader.get_past_bars("AAPL",
                len(backtest.data_loader.get_timeline()))
    test.get_equity_graph().show()
