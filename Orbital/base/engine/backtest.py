from dataclasses import dataclass, field
from datetime import datetime
from queue import Queue

from base.engine.execution import executionLoader
from base.engine.portfolio import Portfolio
from base.engine.data_loader import DataLoader, Bar
from base.engine.strategy import MovingAverageCross

@dataclass
class BacktestResult:
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
                 strength: float = 1.0,
                 slippage: float = 0.0,
                 initial_capital: float = 100000.0,
                 strategy_params: dict[str, object] = None,
                 comission: float = 0.0):
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
        self.commission = comission
        self.slippage = slippage

        self.data_loader = DataLoader(events, tickers, start_date, end_date, asset_type="STOCK")
        self.data_loader.load_data()
        self.events = events
        self.portfolio = Portfolio(self.data_loader, self.events, initial_capital=self.initial_capital, quantity=5)
        self.execute = executionLoader(self.events, self.data_loader, commission=self.commission, slippage=self.slippage)
        self.strategy = MovingAverageCross(self.data_loader, self.events, self.tickers, self.strategy_params["short_window"], self.strategy_params["long_window"], self.strength)
    
    def run(self):
        while self.data_loader.continue_bt:
            self.data_loader.next_day()
            print(f"Processing market event for {self.data_loader.curr_datetime}")
            self.execute_events()
            #self.portfolio.update_records()

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




