from dataclasses import dataclass, field
from datetime import datetime
from queue import Queue
import pandas as pd


from base.engine.execution import executionLoader
from base.engine.portfolio import Portfolio
from base.engine.data_loader import DataLoader, Bar
from base.engine.strategy import MovingAverageCross
import base.engine.graph as graph
import base.engine.performance as p
import base.models as models

class BacktestResult:
    '''
    An instance of this class is the output of the a Backtest run
    It contains all the data used to generate various metrics.
    The methods are in performance.py
    '''
    def __init__(self, equity_records: list[dict[str, any]], fill_records: list[dict[str, any]],
                 risk_free_rate: float):
        self.equity_records = pd.DataFrame(equity_records)
        self.fill_records = fill_records
        self.risk_free_rate = risk_free_rate

    def get_end_equity(self) -> float:
        '''
        Returns end equity used to update model
        '''
        return self.equity_records['equity'].iloc[-1]

    def get_equity_graph(self):
        '''
        Returns the equity graph of a backtest run
        '''
        return graph.get_equity_graph(self.equity_records)

    def get_fill_records(self):
        return self.fill_records

    def get_equity_records(self) -> pd.DataFrame:
        return self.equity_records

    def get_trade_records(self):
        return p.fill_to_trade_log(self.fill_records)

    def get_metrics(self):
        return p.get_metrics(equity_record=self.equity_records,
                             risk_free_rate=self.risk_free_rate)

class Backtest:
    def __init__(self, events: Queue, 
                tickers: list[str], 
                asset_type: str,
                start_date: datetime.date,
                end_date: datetime.date,
                data_loader: DataLoader,
                strategy_name: str,
                strength: float = 1.0,
                slippage: float = 0.0,
                initial_capital: float = 100000.0,
                risk_free_rate: float = 2,
                comission: float = 0.0,
                **strategy_params: dict[str, object]):
        self.events = events
        self.tickers = tickers
        self.asset_type = asset_type
        self.start_date = start_date
        self.end_date = end_date
        self.strategy_name = strategy_name
        self.strength = strength
        self.initial_capital = initial_capital
        self.strategy_params = strategy_params or {
            "short_window": 2,
            "long_window": 5
        }
        self.commission = comission
        self.slippage = slippage

        self.data_loader = data_loader
        self.events = events
        self.portfolio = Portfolio(self.data_loader, self.events,run_name = "test", strategy_name= "Moving Average Cross", start_date= self.start_date, end_date = self.end_date, initial_capital=self.initial_capital, quantity=5 )
        self.execute = executionLoader(self.events, self.data_loader, commission=self.commission, slippage=self.slippage)
        self.strategy = MovingAverageCross(self.data_loader, self.events, self.tickers, self.strategy_params["short_window"], self.strategy_params["long_window"], self.strength)
        
    def run(self):
        while self.data_loader.continue_bt:
            self.data_loader.next_day()
            self.execute_events()
            self.portfolio.update_equity_record()
            self.portfolio.update_benchmark_record()

        return self.portfolio.backtest_run

    def execute_events(self):
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

        




