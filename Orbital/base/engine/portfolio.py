import math
from base.engine.data_loader import DataLoader
from datetime import datetime
from base.engine.events import SignalEvent, OrderEvent, FillEvent
from queue import Queue

class Portfolio:
    def __init__(self, data_loader: DataLoader, events: Queue, 
                 initial_capital: float =  100000.0, quantity =  5):
        self.data_loader = data_loader
        self.events = events
        self.initial_capital = initial_capital
        self.current_capital = initial_capital

        self.fixed_quantity = quantity

        self.holdings : dict[str, float] = {
            ticker: 0 for ticker in self.data_loader.tickers
        }

        self.commission = 0.0
        self.total_commission = 0.0
        #self.total_holdings_value
        
        #store equity data for every time step 
        self.equity_record: list[dict] = []
        # self.open_trades: 
        # self.closed_trades: 

    def equity_update(self) -> None:
        holdings_value = self.calculate_holdings_value()
        total_equity = self.current_capital + holdings_value
        self.equity_record.append(
            {
                "date" : self.data_loader.curr_datetime,
                "cash": self.current_capital,
                "holdings_value": holdings_value,
                "equity": total_equity
            }
        )
    
    def calculate_holdings_value(self) -> float:
        total_value = 0.0
        for ticker, quantity in self.holdings.items():
            price = self.data_loader.bar_lookup[ticker][self.data_loader.curr_datetime].Close
            total_value += quantity * price
        return total_value
    

    def generate_order(self, signal: SignalEvent) -> OrderEvent:
        ticker = signal.ticker
        signal_type = signal.signal_type
        stock_quantity = self.holdings[ticker]
        order_quantity = self.fixed_quantity * signal.strength

        if order_quantity <= 0:
            raise ValueError(f"Invalid order quantity {order_quantity} generated from signal strength {signal.strength}. Order quantity must be positive.")
        
        if signal_type == 'LONG':
            return self.generate_long_order(ticker, stock_quantity, order_quantity, signal.datetime)
        
        elif signal_type == 'SHORT':
            return self.generate_short_order(ticker, stock_quantity, order_quantity,signal.datetime)
        
        elif signal_type == 'EXIT':
            return self.generate_exit_order(ticker, stock_quantity, exit_frac = signal.strength, dt = signal.datetime)
       
        else:
            raise ValueError(f"Invalid signal type {signal_type} in signal event. Expected 'LONG', 'SHORT', or 'EXIT'.")

    def generate_long_order(self, ticker: str, stock_quantity: int, order_quantity: int, dt: datetime) -> OrderEvent:
        if stock_quantity >= 0:
            #If current position is flat or long, buy more
            buy_quantity = order_quantity
        else:
            #If current position is short, buy to cover existing short position and open a new long position
            buy_quantity = abs(stock_quantity) + order_quantity
        return OrderEvent(
            ticker = ticker,
            datetime = dt,
            order_type = "MKT",
            quantity = buy_quantity,
            direction = "BUY"
        )
    
    def generate_short_order(self, ticker: str, stock_quantity: int, order_quantity: int, dt: datetime) -> OrderEvent:
        if stock_quantity <= 0:
            #If current position is flat or short, sell more
            sell_quantity = order_quantity
        else:
            #If current position is long, sell to reduce the existing long position
            sell_quantity = stock_quantity + order_quantity
        return OrderEvent(
            ticker = ticker,
            datetime = dt,
            order_type = "MKT",
            quantity = sell_quantity,
            direction = "SELL"
        )

    def generate_exit_order(self, ticker: str, stock_quantity: int, exit_frac: float, dt: datetime) -> OrderEvent:
        if stock_quantity == 0:
            raise ValueError(f"No existing position in {ticker} to exit.")
        if exit_frac < 0 or exit_frac > 1:
            raise ValueError(f"Invalid exit fraction {exit_frac}. Must be between 0 and 1.")
        buy_or_sell_quantity = abs(stock_quantity) * exit_frac

        if stock_quantity > 0:
            direction = "SELL"
        else:
            direction = "BUY"
        
        return OrderEvent(
            ticker = ticker,
            datetime = dt,
            order_type = "MKT",
            quantity = buy_or_sell_quantity,
            direction = direction
        )


    def update_fill(self, event: FillEvent) -> None:
        if event.type != "FILL":
            raise ValueError(f"Invalid event type {event.type} in fill update. Expected 'FILL'.")
        
        ticker = event.ticker
        curr_quantity = self.holdings.get(ticker, 0)
        trade_quantity = event.quantity if event.direction == "BUY" else -event.quantity
        new_quantity = curr_quantity + trade_quantity

        self.update_cash(event)
        #self.update_records(event)

        self.holdings[ticker] = new_quantity
        print(f"Updated holdings for {ticker}: {curr_quantity} -> {new_quantity}")
        print(f"Current capital after fill: {self.current_capital}")
    

    def update_cash(self, fill: FillEvent) -> None:
        fill_cost = fill.quantity * fill.fill_cost
        if fill.direction == "BUY":
            self.current_capital -= fill_cost + fill.commission
        elif fill.direction == "SELL":
            self.current_capital += fill_cost - fill.commission
        else:
            raise ValueError(f"Invalid fill direction {fill.direction} in cash update. Expected 'BUY' or 'SELL'.")
        self.total_commission += fill.commission
    
