
from dataclasses import dataclass, field
from datetime import datetime
from queue import Queue
from .data_loader import DataLoader, Bar

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
                 initial_capital: float = 100000.0,
                 strategy_params: dict[str, object] = None,
                 comission: float = 0.0):
        self.events = events
        self.tickers = tickers
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.strategy_params = strategy_params
        self.commission = comission

        self.events = Queue()

        self.data_loader = DataLoader(events, tickers, start_date, end_date, asset_type="STOCK")
        
    
    
    def run(self):
        while self.data_load.continue_bt:
            self.data_loader.next_day()
            self.execute_events()
            self.portfolio.update_records()


    def execute_events(self):
        while not self.events.empty():
            event = self.events.get()
            if event.type == "MARKET":
                self.strategy.calculate_signals(event)
            elif event.type == "SIGNAL":
                signal_event = self.portfolio.generate_order(event)
                self.events.put(signal_event)
            elif event.type == "ORDER":
                self.execution.execute(event)
            elif event.type == "FILL":
                self.portfolio.update_fill(event)




