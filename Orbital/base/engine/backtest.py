from queue import Queue
import datetime
import pandas as pd
from base.engine import events
from base.engine.data_loader import DataLoader
from base.engine.performance import calculate_metrics
from base.engine.portfolio import Portfolio
from base.engine.execution import ExecutionLoader
from base.engine.strategy import Strategy

# The Backtest class runs the backtest
class BackTest():
    '''
    Description
    Each instance of this class runs a seperate backtesting instance

    Basic Features
    1. Initialize an instance of execution, strategy, and portfolio classes and a data loader
    2. Pass events into the aforementioned classes.

    Advanced Features TODO
    1. Allow the option to choose between flat comission and percentage comission.
    For now using percentage for simplification.
    2. Instead of passing in this long list of params, 
    we should pass in instances of the necessary classes

    Attributes (non trivial)
    1. events: Queue[Event] => Stores the events
    2. data_loader: DataLoader => pass this dataloader to various classes, allowing them
    to access current and historical bars
    3. portfolio: Portfolio => handles signal and update events
    4. strategy: Strategy => handles market events
    5. execution: Execution => handles order events

    Methods
    1. start => This is used to run the backtest, takes no input, returns BackTestResult

    Notes
    Comission should be calculated by portfolio and not execution
    '''

    # strategy_book is a dictionary of arguments for strategy
    def __init__(self, start_date: datetime.date, end_date: datetime.date,
                 tickers: list[str], asset_type: str, strategy_name: str, initial_capital: float,
                 risk_free_rate: float, comission: float, slippage: float, **kwargs):

        self.events = Queue()
        # After initializing the data loader, it has to be loaded
        self.data_loader = DataLoader(tickers=tickers,
                                      start_date=start_date,
                                      end_date=end_date,
                                      asset_type=asset_type)

        self.portfolio = Portfolio(initial_capital=initial_capital,
                                   data_loader=self.data_loader)

        self.strategy = Strategy(# pylint: disable=abstract-class-instantiated
                                 strategy_name=strategy_name,
                                 ticker=tickers[0],
                                 data_loader=self.data_loader,
                                 **kwargs) # This unpacks kwargs and passes it to Strategy

        self.execution = ExecutionLoader(events=self.events,
                                         data_loader=self.data_loader,
                                         commission=comission,
                                         slippage=slippage)

        self.initial_capital = initial_capital
        self.risk_free_rate = risk_free_rate

    def run(self) -> BackTestResult:
        '''
        Runs the backtest
        '''
        day = 0
        while self.data_loader.should_continue_bt():
            day += 1
            self.events.put(events.MarketEvent(datetime=self.data_loader.get_current_date()))
            self.execute_events() # Executes all events in the queue
            # print(f"Day {day}, has events: {list(self.events.queue)} run")
            self.data_loader.next_day() # Increments a day

        trade_records_df = pd.DataFrame(self.portfolio.history())

        initial_capital = self.initial_capital
        risk_free_rate = self.risk_free_rate
        # print("It reaches the stage of passing back result")
        print(f"{trade_records_df},"
              f"\nrisk free rate = {risk_free_rate},"
               f"\ninitial capital = {initial_capital}")
        return BackTestResult(trade_records_df, initial_capital, risk_free_rate)

    # The nested if elses that call the event clases. .handle()
    def execute_events(self):
        '''
        This method is operates on the events queue. It routes each event to the respective
        class.

        Note that each event typically results in another another event being created
        with MarketEvent being the exception.
        '''
        # functions below are to compartamentalize the calling of events
        def handle_market_event():
            # print("A Market event is handled")
            self.events.put(self.strategy.generate_signal(event))

        def handle_signal_event():
            self.events.put(self.portfolio.generate_order(event))
            # print("A signal event is handled")
            # print(list(self.events.queue))


        def handle_order_event():
            self.events.put(self.execution.execute(event))
            # print("A order event is handled")
            # print(list(self.events.queue))

        def handle_fill_event():
            # print(f"A fill event is handled")
            self.portfolio.update_from_fill(event) # Should not generate a new event
            # print(list(self.events.queue))

        # Loop to execute all events in the queue
        while not self.events.empty():
            event = self.events.get()
            # print(f"event = {event}")
            if event is None:
                break
            if event.type == "MARKET":
                # print("Reached event handling")
                handle_market_event()
            elif event.type == "SIGNAL":
                handle_signal_event()
                # print(list(self.events.queue))
            elif event.type == "ORDER":
                handle_order_event()
                # print(list(self.events.queue))
            elif event.type == "FILL":
                handle_fill_event()
    def __str__(self):
        return f"This is a Back Testing instance {self.__dict__}"


class BackTestResult():
    '''
    This class stores the result of a BackTest
    '''
    def __init__(self, trade_records_df: pd.DataFrame, initial_capital: float, risk_free_rate):
        self.trade_records_df = trade_records_df
        self.initial_capital = initial_capital
        self.risk_free_rate = risk_free_rate
    def get_metrics(self):
        '''
        returns metrics, a dictionary
        '''
        return calculate_metrics(self.trade_records_df,
                                 self.initial_capital,
                                 self.risk_free_rate)
