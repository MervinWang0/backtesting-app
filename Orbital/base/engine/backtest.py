from dataclasses import dataclass
from datetime import datetime
from queue import Queue

from base.engine.execution import ExecutionLoader
from base.engine.portfolio import Portfolio
from base.engine.data_loader import DataLoader, DatabaseDataLoader
from base.engine.strategy import MovingAverageCross

class BacktestResult:
    '''
    An instance of this class is the output of the a Backtest run
    It contains all the data used to generate various metrics.
    The methods are in performance.py
    '''
    def __init__(self, equity_records: list[dict[str, any]], fill_records: list[dict[str, any]]):
        self.equity_records = equity_records
        self.fill_records = fill_records

    def get_total_return(self) -> float:
        '''
        Returns the total return as a percentage.
        Final equity - initial equity / initial equity
        '''
        return ((self.equity_records[-1]["equity"] - self.equity_records[0]["equity"]) /
                self.equity_records[0]["equity"]) * 100
        # self.trade_log = fill_to_trade_log(self.fill_records)

    def get_fill_records(self):
        return self.fill_records
    
    def get_equity_records(self):
        return self.equity_records

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
        self.strategy_params = strategy_params or {
            "short_window": 2,
            "long_window": 5
        }
        self.commission = commission
        self.slippage = slippage

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
        while self.data_loader.continue_bt:
            self.data_loader.next_day()
            self.execute_events()
            self.portfolio.update_equity_record()
        return BacktestResult(equity_records=self.portfolio.get_equity_records(),
                              fill_records=self.portfolio.get_fill_records())

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


if __name__ == "__main__":
    pass


