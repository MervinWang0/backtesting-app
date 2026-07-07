from base.engine.events import OrderEvent, FillEvent
from base.engine.data_loader import DataLoader
from datetime import datetime, date
from base.engine.data_loader import Bar
from queue import Queue


class executionLoader:
    '''
    Description
    The ExecutionLoader class should handle taking in an order, and returning a fill event
    
    Basic Features
    1. adjust price of order to be more realistic, accounting for slippage

    Advanced Features
    More dynamic adjustment to the price to reflect realistic trading

    Attributes
    1. events => shared queue from BackTest
    2. data_loader => shared data loader from BackTest
    3. comission => Only used to pass to fillEvent
    4. slippage => for price adjustment

    Methods
    execute => takes in order event and returns fill event
    
    Other methods are helper methods
    Notes
    '''
    def __init__(self, events: Queue, data_loader: DataLoader, commission: float = 0.0, slippage: float = 0.0):
        self.events = events
        self.data_loader = data_loader
        self.commission = commission
        self.slippage = slippage


    def execute(self, event: OrderEvent):
        '''
        Description
        Takes in an order event and execute accordingly
        '''
        if event.type != "ORDER":
            raise ValueError(f"Invalid event type passed to executionLoader. Expected 'ORDER' but got {event.type}")
        if event.order_type == "MKT":
            self.execute_market_order(event)
        elif event.order_type == "LMT":
            self.execute_limit_order(event)
        else:
            raise ValueError(f"Unsupported order type {event.order_type}")
        
    def slippage_adjustment(self, price: float, direction: str) -> float:
        '''
        Description
        For realism, adds a slippage cost to each trade.
        Takes in price and direction and returns new price
        '''
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
        '''
        Description
        Encapsulates the creation of fill event
        '''
        return FillEvent(
            ticker = order.ticker,
            datetime = order.datetime,
            asset_type= order.asset_type,
            quantity = order.quantity,
            direction = order.direction,
            fill_cost = price,
            commission = commission
        )
    
    def execute_market_order(self, order: OrderEvent):
        '''
        Description
        Carries out execution when order is of market type 
        Note: Use open instead of close to prevent look ahead bias
        '''
        latest_price = self.data_loader.get_current_bar_value(order.ticker, "open")
        if latest_price is None:
            raise ValueError(f"No price data available for ticker {order.ticker} at the time of order execution.")
        price = self.slippage_adjustment(latest_price, order.direction)
        commission = self.calculate_commission(order.quantity, price)
        fill = self.create_fill_event(order, price, commission)
        print(self.data_loader.get_current_datetime())
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
    
    def execute_futures_roll(self, 
                             ticker: str,
                             datetime: datetime,
                             from_contract: str,
                             to_contract: str,
                             from_price: float,
                             to_price: float,
                             quantity: int,
                             multiplier: int
                             ):
        if quantity == 0:
            return
        
        quantity = abs(quantity)

        if quantity > 0:
            close_direction = "SELL"
            open_direction = "BUY"
        else:
            close_direction = "BUY"
            open_direction = "SELL"
        
        adjusted_from_price = self.slippage_adjustment(from_price, close_direction)
        adjusted_to_price = self.slippage_adjustment(to_price, open_direction)
        close_commission = self.calculate_commission(quantity, adjusted_from_price)
        open_commission = self.calculate_commission(quantity, adjusted_to_price)

        close_fill = FillEvent(
            ticker = ticker,
            datetime = datetime,
            asset_type= "FUTURES",
            quantity = quantity,
            direction = close_direction,
            fill_cost = adjusted_from_price * multiplier,
            commission = close_commission
        )

        open_fill = FillEvent(
            ticker = ticker,
            datetime = datetime,
            asset_type= "FUTURES",
            quantity = quantity,
            direction = open_direction,
            fill_cost = adjusted_to_price * multiplier,
            commission = open_commission
        )

        self.events.put(close_fill)
        self.events.put(open_fill)



    



    