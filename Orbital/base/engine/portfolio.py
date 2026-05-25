from events import *
from queue import Queue

class Portfolio:
    def __init__(self, bar: Bar, events: Queue, 
                 initial_capital: float =  100000.0, 
                 holdings: dict[str, int] = None, self.quantity =  1):
        self.bar = bar
        self.events = events
        self.initial_capital = initial_capital
        self.current_capital = initial_capital

        self.holdings = dict[str, float] = {
            ticker: 0 for ticker in self.bar_lookup.keys()
        }
        self.total_holdings_value = total_holdings_value
        
        #store equity data for every time step 
        self.equity_record: list[dict] = []
        self.open_trades: 
        self.closed_trades: 

#Target weight sizing

# Portfolio says: “I want AAPL to be 20% of the portfolio.”

# target_value = total_equity * target_weight
# current_value = current_position * current_price
# order_value = target_value - current_value
# quantity = int(order_value / current_price)

# This is common in portfolio strategies, especially multi-asset or rebalancing systems.



    
    def equity_update(self) -> None:
        holdings_value = self.calculate_holdings_value()
        total_equity = self.current_capital + holdings_value
        self.equity_record.append(
            {
                "date" : self.bar.Date,
                "cash": self.current_capital,
                "holdings_value": holdings_value,
                "equity": total_equity
            }
        )
    
    def calculate_holdings_value(self) -> float:
        total_value = 0.0
        for ticker, quantity in self.holdings.items():
            price = self.bar_lookup[ticker][self.bar.Date].Close
            total_value += quantity * price
        return total_value
    

    def generate_order(self, signal: SignalEvent) -> OrderEvent:
        ticker = signal.ticker
        signal_type = signal.signal_type
        stock_quantity = self.holdings[ticker]
        order_quantity = self.quantity * signal.strength

        if signal_type == "LONG":
            if current

