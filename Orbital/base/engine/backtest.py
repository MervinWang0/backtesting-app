from dataclasses import dataclass
from datetime import datetime
from queue import Queue
import plotly.express as px
import pandas as pd

from base.engine.execution import ExecutionLoader
from base.engine.portfolio import DatabasePortfolio, MCSPortfolio
from base.engine.data_loader import DataLoader, DatabaseDataLoader
from base.engine.strategy import (MovingAverageCross,
                                  MeanReversion,
                                  Strategy,
                                  MACDStrategy,
                                  BreakoutStrategy,
                                  MomentumStrategy,
                                  RateOfChangeStrategy,
                                  StochasticOscillatorStrategy)
from base.futures.continuous_series import ContinuousFuturesSeriesBuilder
from base.engine.events import AssetType
from base.models import ContinuousFuturesSeries
import base.engine.graph as graph
import base.engine.performance as p
import base.models as models
from functools import wraps
from time import time

def initialize_strategy(name: str,
                    data_loader: DataLoader,
                    strength: float = 1,
                    **strategy_params) -> Strategy:
    
    if name == "Moving Average Crossover":
        return MovingAverageCross(data_loader=data_loader,
                                  events=data_loader.events,
                                  tickers=data_loader.tickers,
                                  **strategy_params)
    if name == "Mean Reversion":
        return MeanReversion(data_loader=data_loader,
                             strength=strength,
                             **strategy_params)
    if name == "MACD":
        return MACDStrategy(data_loader=data_loader,
                            strength=strength,
                            **strategy_params
                            )
    if name == "Breakout":
        return BreakoutStrategy(data_loader=data_loader,
                                strength=strength,
                                **strategy_params)
    if name == "Momentum":
        return MomentumStrategy(data_loader=data_loader,
                                strength=strength,
                                **strategy_params)
    if name == "Rate Of Change":
        return RateOfChangeStrategy(data_loader=data_loader,
                                    strength=strength,
                                    **strategy_params)
    if name == "Stochastic Oscillator":
        return StochasticOscillatorStrategy(data_loader=data_loader,
                                            strength=strength,
                                            **strategy_params)
        

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
        # if len(fill_records) == 0:
        #     raise ValueError("fill records are empty. No trades executed and metrics not obtainable")
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
        if df.empty:
            return df
        df["pnl"] = (df['sell_price'] - df['buy_price']) * df['quantity']
        return df

    @timed
    def get_metrics(self) -> dict[str: float]:
        '''
        Returns various performance and portfolio metrics.

        Returns a dict or metric : 0 if no trades were conducted
        '''
        trade_log = self.get_closed_trades()
        # print("This is the trade log generated")
        # print(f"\n{trade_log}")
        return p.get_metrics(equity_record=self.equity_records,
                             risk_free_rate=self.risk_free_rate,
                             trade_log=trade_log)

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
                 risk_free_rate: float = 0.02,
                 is_mcs = False,
                 roll_days: int = 5,
                 continuous_contract_index: int = 1,
                 adjustment_method: str = "NONE",
                 build_continuous_series: bool = True,
                 **strategy_params: dict[str, object]):
        self.data_loader = data_loader
        self.asset_type = self.data_loader.asset_type
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
        self.risk_free_rate = risk_free_rate

        # Parameters for futures
        self.roll_days = roll_days
        self.continuous_contract_index = continuous_contract_index
        self.adjustment_method = adjustment_method
        self.build_continuous_series = build_continuous_series
        self.continuous_series: dict[str, ContinuousFuturesSeries] = {}
        if (self.is_futures() and self.build_continuous_series):
            print("-----------------------------------------")
            print("This is from backtest init in engine.backtest.py")
            print("This backtest uses a futures and builds a series")
            self.prepare_continuous_series()
        self.rollover_count = 0
        self.processed_rollovers = set()


        self.events = events

        self.execute = ExecutionLoader(self.events, self.data_loader, commission=self.commission,
                                       slippage=self.slippage)
        self.strategy = initialize_strategy(name=strategy_name,
                                            data_loader=data_loader,
                                            strength=strength,
                                            **strategy_params)
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
            if self.is_futures():
                self.futures_rollover()
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
                # print("Executing fill order")
                self.portfolio.update_fill(event)

    def is_futures(self):
        return self.asset_type == AssetType.FUTURES
    
    def futures_rollover(self):
        if not self.is_futures():
            return
        for ticker in self.tickers:
            bar = self.data_loader.get_current_bar(ticker)
            if bar is None:
                continue

            if not bar.is_roll:
                continue

            quantity = self.portfolio.holdings.get(ticker, 0)
            if quantity == 0:
                print(
                    f"{bar.date}: rollover available for {ticker}, "
                    "but no position is currently open."
                )
                continue
            multiplier = float(bar.contract_multiplier)

            if bar.roll_from_price is None:
                roll_from_price = float(bar.close) 
                print(f"Warning: roll_from_price is None on {bar.date}. Using bar.close as fallback.")
            else:
                roll_from_price = float(bar.roll_from_price)

            if bar.roll_to_price is None:
                roll_to_price = float(bar.close)
                print(f"Warning: roll_to_price is None on {bar.date}. Using bar.close as fallback.")
            else:
                roll_to_price = float(bar.roll_to_price)

            roll_cash = (
                roll_from_price
                - roll_to_price
            ) * quantity * multiplier

            print("\n--- ROLLOVER DEBUG ---")
            print("Date:", bar.date)
            print("Ticker:", ticker)
            print(
                "Contracts:",
                bar.roll_from_contract_code,
                "->",
                bar.roll_to_contract_code,
            )
            print("Prices:", bar.roll_from_price, "->", bar.roll_to_price)
            print("Quantity:", quantity)
            print("Multiplier:", multiplier)
            print(
                "Potential incorrect cash effect:",
                roll_cash,
            )
                        
            current_quantity = self.portfolio.holdings.get(ticker, 0)
            print(
                    f"{bar.date}: rolling {ticker} "
                    f"{bar.roll_from_contract_code} -> "
                    f"{bar.roll_to_contract_code}, "
                    f"quantity={current_quantity}"
                )
            if current_quantity == 0:
                continue
            from_contract = bar.roll_from_contract_code
            to_contract = bar.roll_to_contract_code
            from_price = roll_from_price
            to_price = roll_to_price

            # if not from_contract or not to_contract:
            #     print(
            #         f"Skipping invalid rollover for {ticker} on "
            #         f"{bar.date}: missing contract codes."
            #     )
            #     continue

            # if from_contract == to_contract:
            #     print(
            #         f"Skipping invalid rollover for {ticker} on "
            #         f"{bar.date}: contracts are identical."
            #     )
            #     continue

            roll = (ticker, bar.date, from_contract, to_contract)

            if roll in self.processed_rollovers:
                print(
                    f"{bar.date}: skipping previously processed rollover "
                    f"{ticker} {from_contract} -> {to_contract}"
                )
                continue

            self.execute.execute_futures_roll(
                ticker = ticker,
                datetime = bar.date,
                from_contract = from_contract,
                to_contract = to_contract,
                from_price = from_price,
                to_price = to_price,
                quantity = current_quantity,
                multiplier = bar.contract_multiplier)
            
            #currency = "USD"
            #self.portfolio.add_cash(roll_cash, currency=currency)
            
            self.processed_rollovers.add(roll)
            self.rollover_count += 1

    def prepare_continuous_series(self):
        if self.roll_days < 0:
            raise ValueError("Roll days must be a non-negative integer.")
        
        for root_symbol in self.tickers:
            series, created = (ContinuousFuturesSeries.objects.get_or_create(
                contract_symbol=root_symbol,
                roll_days=self.roll_days,
                rollover_rule = "DAYS_BEFORE_EXPIRY",
                contract_index=self.continuous_contract_index,
                adjustment_method=self.adjustment_method
            ))
            builder = ContinuousFuturesSeriesBuilder(series)

            if created:
                print("created")
            
            try:
                price_count = builder.build(
                    start_date = self.start_date,
                    end_date = self.end_date,
                )
            except RuntimeError as e:
                raise RuntimeError(f"Failed to build continuous series for {root_symbol}: {str(e)}")
            
            self.continuous_series[root_symbol] = series

            print(f"Continuous series for {root_symbol} built successfully with {price_count} price records.")








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
    pass