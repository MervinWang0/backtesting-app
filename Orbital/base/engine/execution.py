from base.engine.events import OrderEvent, FillEvent
from base.engine.data_loader import DataLoader
from datetime import datetime, date
from base.engine.data_loader import Bar
from queue import Queue


class executionLoader:
    def __init__(self, events: Queue, data_loader: DataLoader, commission: float = 0.0, slippage: float = 0.0):
        self.events = events
        self.data_loader = data_loader
        self.commission = commission
        self.slippage = slippage


    def execute(self, event: OrderEvent):
        if event.type != "ORDER":
            raise ValueError(f"Invalid event type passed to executionLoader. Expected 'ORDER' but got {event.type}")
        if event.order_type == "MKT":
            self.execute_market_order(event)
        elif event.order_type == "LMT":
            self.execute_limit_order(event)
        else:
            raise ValueError(f"Unsupported order type {event.order_type}")
        
    def slippage_adjustment(self, price: float, direction: str) -> float:
        #Buy: slippage adds to price , price increases
        #sell: splippage reduces price, price decreases
        if direction == "BUY":
            return price * (1 + self.slippage)
        elif direction == "SELL":
            return price * (1 - self.slippage)
        else:
            raise ValueError(f"Invalid order direction {direction} for slippage adjustment.")
        
    def calculate_commission(self, quantity: int, price: float) -> float:
        return quantity * price * self.commission

    
    def create_fill_event(self, order: OrderEvent, price: float, commission: float) -> FillEvent:
        return FillEvent(
            ticker = order.ticker,
            datetime = order.datetime,
            quantity = order.quantity,
            direction = order.direction,
            fill_cost = price,
            commission = commission
        )
    
    def execute_market_order(self, order: OrderEvent):
        latest_price = self.data_loader.get_latest_bar_value(order.ticker, "Close")
        if latest_price is None:
            raise ValueError(f"No price data available for ticker {order.ticker} at the time of order execution.")
        price = self.slippage_adjustment(latest_price, order.direction)
        commission = self.calculate_commission(order.quantity, price)
        fill = self.create_fill_event(order, price, commission)
        print(f"Executing market order for {order.ticker} at price {price} with commission {commission}")
        self.events.put(fill)

    def execute_limit_order(self, order: OrderEvent):
        latest_bar = self.data_loader.get_latest_bar(order.ticker)
        can_fill = False

        if latest_bar is None:
            raise ValueError(f"No price data available for ticker {order.ticker} at the time of order execution.")
        
        if (order.direction == "BUY"):
            can_fill = latest_bar.Low <= order.price
        elif (order.direction == "SELL"):
            can_fill = latest_bar.High >= order.price
        else:
            raise ValueError(f"Invalid order direction {order.direction} in limit order execution.")
        
        if can_fill:
            price = self.slippage_adjustment(order.price)
            commission = self.calculate_commission(order.quantity, price)
            fill = self.create_fill_event(order, price, commission)
            self.events.put(fill)
        else:
            return
        


    



    



    