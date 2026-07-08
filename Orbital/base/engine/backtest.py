from dataclasses import dataclass, field
from datetime import datetime
from queue import Queue

from base.engine.events import AssetType
from base.futures.continuous_series import ContinuousFuturesSeriesBuilder
from base.models import ContinuousFuturesSeries
from base.engine.execution import executionLoader
from base.engine.portfolio import Portfolio
from base.engine.data_loader import DataLoader, Bar
from base.engine.strategy import MovingAverageCross
from base.engine.graph import get_equity_graph

@dataclass
class BacktestResult:
    initial_capital: float
    final_capital: float
    metric: dict[str, any]
    trade_log: list[dict]

class Backtest:
    def __init__(self, events: Queue, 
                 tickers: list[str], 
                 asset_type: str,
                 start_date: datetime.date,
                 end_date: datetime.date,
                 strategy_name: str,
                 strength: float = 1.0,
                 slippage: float = 0.0,
                 initial_capital: float = 100000.0,
                 strategy_params: dict[str, object] = None,
                 comission: float = 0.0,
                 roll_days: int = 5,
                 continuous_contract_index: int = -1,
                 adjustment_method: str = None,
                 build_continuous_series: bool = True,
                 ):
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
        self.roll_days = roll_days
        self.continuous_contract_index = continuous_contract_index
        self.adjustment_method = adjustment_method
        self.build_continuous_series = build_continuous_series
        self.continuous_series: dict[str, ContinuousFuturesSeries] = {}
        if (self.is_futures() and self.build_continuous_series): self.prepare_continuous_series()
        self.rollover_count = 0
        self.processed_rollovers = set()

        self.data_loader = DataLoader(events, tickers= tickers, start_date= self.start_date, end_date= self.end_date, asset_type=self.asset_type)

        self.events = events
        self.portfolio = Portfolio(self.data_loader, self.events,run_name = "test", strategy_name= "Moving Average Cross", start_date= self.start_date, end_date = self.end_date, initial_capital=self.initial_capital, quantity=5 )
        self.execute = executionLoader(self.events, self.data_loader, commission=self.commission, slippage=self.slippage)
        self.strategy = MovingAverageCross(self.data_loader, self.events, self.tickers, self.strategy_params["short_window"], self.strategy_params["long_window"], self.strength)
        
    def run(self):
        while self.data_loader.continue_bt:
            self.data_loader.next_day()

            if self.is_futures():
                self.futures_rollover()

            self.execute_events()
            self.portfolio.update_equity_record()
            self.portfolio.update_benchmark_record()
        
        self.portfolio.complete_bt()
        
        #print("Backtest finished; generating graph")
        fig = get_equity_graph(self.portfolio.equity_record)
        
        fig.write_html(
            "equity_graph.html",
            auto_open=True,
            include_plotlyjs=True,
        )
        return self.portfolio.backtest_run, self.portfolio.benchmark_records
    
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

        




