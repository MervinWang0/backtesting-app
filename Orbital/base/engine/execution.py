from queue import Queue
from base.engine.events import OrderEvent, FillEvent
from base.engine.data_loader import DataLoader


class ExecutionLoader:
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
    def __init__(self, events: Queue, data_loader: DataLoader,
                 commission: float, slippage: float):
        self.events = events
        self.data_loader = data_loader
        self.commission = commission
        self.slippage = slippage


    def execute(self, event: OrderEvent):
        '''
        Description
        Takes in an order event and returns a fill event
        '''
        if event.type  != "ORDER":
            raise ValueError("Invalid event type passed to executionLoader. " \
            "Expected 'ORDER' but got {event.type}")
        if event.order_type == "MKT":
            return self.execute_market_order(event)
        # elif event.order_type == "LMT":
        #     self.execute_limit_order(event)
        else:
            raise ValueError(f"Unsupported order type {event.order_type}")

    def execute_market_order(self, order: OrderEvent) -> FillEvent:
        '''
        Description
        Carries out execution when order is of market type
        '''
        latest_price = self.data_loader.get_current_bar_value(order.ticker, "close")
        if latest_price is None:
            raise ValueError(f"No price data available for ticker {order.ticker} at"
                              "the time of order execution.")
        price = self.slippage_adjustment(latest_price, order.direction)
        return self.create_fill_event(order, price)

    def slippage_adjustment(self, price: float, direction: str) -> float:
        '''
        Description
        For realism, adds a slippage cost to each trade.
        Takes in price and direction and returns new price
        '''
        #Buy: slippage adds to price , price increases
        #sell: splippage reduces price, price decreases
        if direction == "BUY":
            return float(price) * (1 + self.slippage) # decimal.Decimal and float error
        if direction == "SELL":
            return float(price) * (1 - self.slippage)
        raise ValueError(f"Invalid order direction {direction} for slippage adjustment.")

    def create_fill_event(self, order: OrderEvent, price: float) -> FillEvent:
        '''
        Description
        Encapsulates the creation of fill event
        '''
        # print("Create fill event works")
        return FillEvent(
            ticker = order.ticker,
            datetime = order.datetime,
            quantity = order.quantity,
            direction = order.direction,
            fill_cost = price,
            commission = self.commission
        )



    # def execute_limit_order(self, order: OrderEvent):
    #     '''
    #     Description
    #     Carries out execution when order is of limit type
    #     '''
    #     latest_bar = self.data_loader.get_latest_bar(order.ticker)
    #     can_fill = False

    #     if latest_bar is None:
    #         raise ValueError(f"No price data available for ticker {order.ticker}"
    #                          " at the time of order execution.")

    #     if order.direction == "BUY":
    #         can_fill = latest_bar.Low <= order.price
    #     elif order.direction == "SELL":
    #         can_fill = latest_bar.High >= order.price
    #     else:
    #         raise ValueError(f"Invalid order direction {order.direction} in limit order execution.")

    #     if can_fill:
    #         price = self.slippage_adjustment(order.price, order.direction)
    #         fill = self.create_fill_event(order, price)
    #         self.events.put(fill)
    #     else:
    #         return