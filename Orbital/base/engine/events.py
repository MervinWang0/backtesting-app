from queue import Queue
from datetime import datetime


class EventTypes(Enum):
    MARKET = "MARKET"
    SIGNAL = "SIGNAL"
    ORDER = "ORDER"
    FILL = "FILL"

@dataclass
class MarketEvent:
    type : EventTypes.MARKET

@dataclass
class SignalEvent:
    type : EventTypes.SIGNAL
    strategy_id : str # identifies unique strategy that generated event
    ticker : str
    date : datetime 
    direction : str # Strategy want to buy or sell "LONG", "SHORT", "EXIT"
    strength : float # range [0, 1], represents confidence, higher is more confident

@dataclass
class OrderEvent:
    type : EventTypes.ORDER
    ticker : str # Stock being traded
    order_type : str # Market of Limit
    quantity : int # volume buy/sell
    direction : str # buy/sell


@dataclass
class FillEvent:
    type : EventTypes.FILL
    time_index : datetime # date the trade occured
    ticker : str # the stock traded
    quantity : int # volume buy/sell
    direction : str # buy/sell
    comission : float # maybe have a default or a method of calculating it
    fill_price : float # price per share traded

while true:
    while not backtest_queue.is_empty():
        event = backtest_queue.pop()
        if event.type == EventTypes.MARKET:
            strategy.market_event
        elif event.type == EventTypes.SIGNAL:
            portfolio.signal_event
        elif event.type == EventTypes.EXECUTION:
            execution.execution
        elif event.type == EventTypes.FILL:
            portfolio.fill







