from dataclasses import dataclass
from datetime import datetime
from queue import Queue

from base.engine.execution import ExecutionLoader
from base.engine.portfolio import Portfolio
from base.engine.data_loader import DataLoader, DatabaseDataLoader
from base.engine.strategy import MovingAverageCross

@dataclass
class BacktestResult:
    '''
    An instance of this class is the output of the a Backtest run
    It contains all the data necessary to compute various metrics of the backtest
    '''
    initial_capital: float
    final_capital: float
    metric: dict[str, any]
    trade_log: list[dict]


class Backtest:
    def __init__(self, events: Queue,
                 tickers: list[str],
                 start_date: datetime.date,
                 end_date: datetime.date,
                 strategy_name: str,
                 data_loader: DataLoader,
                 strength: float = 1.0,
                 slippage: float = 0.0,
                 initial_capital: float = 100000.0,
                 strategy_params: dict[str, object] = None,
                 commission: float = 0.0,):
        self.events = events
        self.tickers = tickers
        self.start_date = start_date
        self.end_date = end_date
        self.strategy_name = strategy_name
        self.strength = strength
        self.initial_capital = initial_capital
        self.strategy_params = strategy_params or {
            "short_window": 2,
            "long_window": 5
        }
        self.commission = commission
        self.slippage = slippage

        self.data_loader = data_loader
        self.events = events
        self.portfolio = Portfolio(self.data_loader, self.events,
                                   run_name="test", strategy_name="Moving Average Cross",
                                   start_date=self.start_date, end_date=self.end_date,
                                   initial_capital=self.initial_capital, quantity=5)
        self.execute = ExecutionLoader(self.events, self.data_loader, commission=self.commission,
                                       slippage=self.slippage)
        self.strategy = MovingAverageCross(self.data_loader, self.events, self.tickers,
                                           self.strategy_params["short_window"],
                                           self.strategy_params["long_window"], self.strength)

    def run(self):
        '''
        Function that executes the backtest.
        '''
        print("A Backtest has occurred!")
        while self.data_loader.continue_bt:
            self.data_loader.next_day()
            self.execute_events()
            self.portfolio.update_equity_record()

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





