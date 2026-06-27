from dataclasses import dataclass
from datetime import datetime
from queue import Queue
import plotly.express as px
import pandas as pd

from base.engine.execution import executionLoader
from base.engine.portfolio import Portfolio
from base.engine.data_loader import DataLoader, DatabaseDataLoader
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
        Returns end equity used to update mode
document.querySelectorAll(".link-to-stock").forEach((row) => {
    row.addEventListener("click", () => {
        window.location.href = row.dataset.href;
    });

    row.addEventListener("keydown", (event) => {
        if (event.key == "Enter" || event.key == " ") {
            event.preventDefault();
            window.location.href = row.dataset.href;
        }
    });
});
        '''
        return self.equity_records['equity'].iloc[-1]

    def get_equity_graph(self) -> px.Figure:
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
        self.portfolio = Portfolio(self.data_loader, self.events,
                                   run_name="test", strategy_name="Moving Average Cross",
                                   start_date=self.start_date, end_date=self.end_date,
                                   initial_capital=self.initial_capital, quantity=5)
        self.execute = executionLoader(self.events, self.data_loader, commission=self.commission,
                                       slippage=self.slippage)
        self.strategy = MovingAverageCross(self.data_loader, self.events, self.tickers,
                                           self.strategy_params["short_window"],
                                           self.strategy_params["long_window"], self.strength)
        self.asset_type = asset_type
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

    def get_backtest_run_id(self) -> int:
        '''
        Returns the id of the run
        '''
        return self.run_model.id

    def run(self):
        '''
        Function that executes the backtest.
        '''
        while self.data_loader.continue_bt:
            print("A Backtest day is executed")
            self.data_loader.next_day()
            # print(f"This is the events {list(self.events)}")
            self.execute_events()
            self.portfolio.update_equity_record()
            # self.portfolio.update_benchmark_record()
        result = BacktestResult(equity_records=self.portfolio.get_equity_records(),
                              fill_records=self.portfolio.get_fill_records(),
                              risk_free_rate=self.risk_free_rate)
        self.run_model.end_equity = result.get_end_equity()
        self.run_model.is_completed = True
        self.run_model.save()
        return result

    def execute_events(self):
        '''
        Helper function for run, represents the handling of each bar,
        from signal generation to orders to fill update
        '''
        print("executes an event")
        while not self.events.empty():
            event = self.events.get()
            print(f"event is {event}")
            if event is None:
                continue
            if event.type == "MARKET":
                print("executed a market event")
                for ticker in self.tickers:
                    signal_event = self.strategy.generate_signal(ticker)
                    self.events.put(signal_event)
            elif event.type == "SIGNAL":
                print("executed a SIGNAL event")
                order_event = self.portfolio.generate_order(event)
                self.events.put(order_event)
            elif event.type == "ORDER":
                self.execute.execute(event)
                print("executed a ORDER event")
            elif event.type == "FILL":
                print("executed a FILL event")
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


