from dataclasses import dataclass
from datetime import datetime
from queue import Queue
import plotly.express as px
import pandas as pd

from base.engine.execution import ExecutionLoader
from base.engine.portfolio import DatabasePortfolio, MCSPortfolio
from base.engine.data_loader import DataLoader, DatabaseDataLoader
from base.engine.strategy import MovingAverageCross
import base.engine.graph as graph
import base.engine.performance as p
import base.models as models
from functools import wraps
from time import time

def timed(f):
    '''
    This function is used to time any function
    Usage syntax
    @timed
    def funct()
    '''

    @wraps(f)
    def wrapper(*args, **kwds):
        start = time()
        result = f(*args, **kwds)
        elapsed = time() - start
        print(f"function {f.__name__} took {elapsed}")
        return result
    return wrapper

class BacktestResult:
    '''
    An instance of this class is the output of the a Backtest run
    It contains all the data used to generate various metrics.
    The methods are in performance.py
    '''
    # @timed
    def __init__(self, equity_records: dict[datetime.date, dict[str, any]], fill_records: list[dict[str, any]],
                 risk_free_rate: float):
        data_frame = pd.DataFrame(equity_records.values())
        data_frame = data_frame.sort_values(by="date")
        self.equity_records = data_frame
        self.fill_records = fill_records
        self.risk_free_rate = risk_free_rate
        self.trade_log = p.fill_to_trade_log(self.fill_records)

    def get_end_equity(self) -> float:
        '''
        Returns end equity used to update model
        '''
        return self.equity_records['equity'].iloc[-1]

    def get_equity_graph(self) -> px.Figure:
        '''
        Returns the equity graph of a backtest run
        '''
        return graph.get_equity_graph(self.equity_records)

    def get_fill_records(self):
        '''
        Returns the fill records
        '''
        return self.fill_records

    def get_equity_records(self) -> pd.DataFrame:
        '''
        Returns the equity records
        '''
        return self.equity_records

    def get_trade_log(self) -> tuple[list[dict[str, any]], dict[str, list[any]]]:
        '''
        Returns the trade log index 0 is open trades, index 1 is closed trades
        '''
        return p.fill_to_trade_log(self.fill_records) 

    def get_closed_trades(self) -> pd.DataFrame:
        '''
        Returns the closed trades
        '''
        df = pd.DataFrame(self.get_trade_log()[1])
        df["pnl"] = (df['sell_price'] - df['buy_price']) * df['quantity']
        return df

    @timed
    def get_metrics(self):
        '''
        Returns various performance and portfolio metrics
        '''
        return p.get_metrics(equity_record=self.equity_records,
                             risk_free_rate=self.risk_free_rate,
                             trade_log=self.get_closed_trades())

class Backtest:
    @timed
    def __init__(self, events: Queue,
                 tickers: list[str],
                 start_date: datetime.date,
                 end_date: datetime.date,
                 strategy_name: str,
                 data_loader: DataLoader,
                 asset_type: str,
                 strength: float = 1.0,
                 slippage: float = 0.0,
                 initial_capital: float = 100000.0,
                 commission: float = 0.0,
                 risk_free_rate: float = 2,
                 is_mcs = False,
                 **strategy_params: dict[str, object]):
        self.data_loader = data_loader
        # In the case of MCS data loader is passed in,
        # events has to point to the same queue for all the components
        self.events = events
        self.tickers = tickers
        self.start_date = start_date
        self.end_date = end_date
        self.strategy_name = strategy_name
        self.strength = strength
        self.initial_capital = initial_capital
        self.strategy_params = strategy_params
        self.commission = commission
        self.slippage = slippage
        self.risk_free_rate = risk_free_rate / 100

        self.events = events

        self.execute = ExecutionLoader(self.events, self.data_loader, commission=self.commission,
                                       slippage=self.slippage)
        self.strategy = MovingAverageCross(self.data_loader, self.events, self.tickers,
                                           self.strategy_params["short_window"],
                                           self.strategy_params["long_window"], self.strength)
        self.asset_type = asset_type
        
        # Stores this boolean for usage in methods of class
        self.is_mcs = is_mcs
        # If the backtest does not use MCS, the data should be stored in db
        if not self.is_mcs:
            # Create a model storing the backtest
            self.run_model = models.BacktestRun.objects.create(
                run_name="",
                strategy_name=self.strategy_name,
                asset_type = self.asset_type,
                fixed_quantity = 0,
                risk_free_rate = self.risk_free_rate,

                stock = None,
                futures = None,
                forex = None,

                start_date = self.start_date,
                end_date = self.end_date,
                initial_capital = self.initial_capital,
                end_equity = 0,

                is_completed = False,
                completed_at = self.end_date,

                #Stores list of tickers used in the backtest
                tickers = self.tickers,

                # Additional parameters necessary
                strength = strength,
                commission = commission,
                slippage = slippage,
                # Encodes strategy params in a dict
                strategy_params = strategy_params,
            )
            
            self.portfolio = DatabasePortfolio(self.data_loader, self.events,
                                    run_name="test", strategy_name="Moving Average Cross",
                                    start_date=self.start_date, end_date=self.end_date,
                                    initial_capital=self.initial_capital, quantity=5,
                                    run_model=self.run_model)
        else:
            # The difference between the creation of the portfolios is that MCSPortfolio does not create a 
            # db instance
            self.portfolio = MCSPortfolio(self.data_loader, self.events,
                                    run_name="test", strategy_name="Moving Average Cross",
                                    start_date=self.start_date, end_date=self.end_date,
                                    initial_capital=self.initial_capital, quantity=5,
                                    )

        

    def get_backtest_run_id(self) -> int:
        '''
        Returns the id of the run
        '''
        return self.run_model.id

    @timed
    def run(self):
        '''
        Function that executes the backtest.
        '''
        while self.data_loader.continue_bt:
            self.data_loader.next_day()
            self.execute_events()
            self.portfolio.update_equity_record()
        result = BacktestResult(equity_records=self.portfolio.get_equity_records(),
                              fill_records=self.portfolio.get_fill_records(),
                              risk_free_rate=self.risk_free_rate)
        if not self.is_mcs:
            self.portfolio.complete_bt()
            self.run_model.end_equity = result.get_end_equity()
            self.run_model.is_completed = True
            self.run_model.save()
        return result

    # @timed
    def execute_events(self):
        '''
        Helper function for run, represents the handling of each bar,
        from signal generation to orders to fill update
        '''
        while not self.events.empty():
            event = self.events.get()
            if event is None:
                continue
            if event.type == "MARKET":
                for ticker in self.tickers:
                    signal_event = self.strategy.generate_signal(ticker)
                    self.events.put(signal_event)
            elif event.type == "SIGNAL":
                order_event = self.portfolio.generate_order(event)
                self.events.put(order_event)
            elif event.type == "ORDER":
                self.execute.execute(event)
            elif event.type == "FILL":
                self.portfolio.update_fill(event)

    def __str__(self):
        '''
        Displays some attribute information of the backtest
        '''
        return (f"This is events = {self.events}"
            f"This is start date = {self.start_date}"
            f"This is end date = {self.end_date}"
            f"This is strategy name = {self.strategy_name}"
            f"This is strength = {self.strength}"
            f"This is initial capital = {self.initial_capital}"
            f"This is strategy params = {self.strategy_params}"
            f"This is commission = {self.commission}"
            f"This is slippage = {self.slippage}")

if __name__ == "__main__":
    data = {'short_window': int(5.0),
            'long_window': int(10.0),
            'asset_type': 'STOCK',
            'strength': 1.0,
            'slippage': 0.0,
            'initial_capital': 100000.0,
            'commission': 0.0,
            'start_date': datetime.fromisoformat("2024-01-01").date(),
            'end_date': datetime.fromisoformat("2025-01-01").date(),
            'tickers': ['AAPL'],
            'strategy_name': 'moving_average_crossover'}
    start_date = datetime.fromisoformat("2024-01-01").date()
    end_date = datetime.fromisoformat("2025-01-01").date()
    data_loader = DatabaseDataLoader(Queue(), ["AAPL"], start_date,
                             end_date, "STOCK")
    backtest1 = Backtest(
                        events=data_loader.events,
                        data_loader=data_loader,
                        **data
                        )
    backtest2 = Backtest(events=data_loader.events,
                        tickers=['AAPL'],
                        start_date=start_date,
                        end_date=end_date,
                        strategy_name="moving_average_crossover",
                        data_loader=data_loader,
                        short_window=10,
                        long_window=15
                        )
    # print(backtest1)
    # print(backtest2)
    btr = backtest1.run()
    btr.get_equity_graph().show()
