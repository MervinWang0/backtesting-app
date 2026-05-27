from datetime import datetime
from dataclasses import dataclass, field
from django.db import models

class SignalType(models.TextChoices):
    '''
    Description
    Enumerated Signal values
    '''
    LONG = "LONG", "Long"
    SHORT = "SHORT", "Short"
    EXIT = "EXIT", "Exit"

class OrderType(models.TextChoices):
    '''
    Description
    Enumerated Order values
    '''
    MKT = "MKT", "Market"
    LMT = "LMT", "Limit"

class DirectionType(models.TextChoices):
    '''
    Description
    Enumerated Direction values
    '''
    BUY = "BUY", "Buy"
    SELL = "SELL", "Sell"


#dataclass to track whenever a new bar is generated
@dataclass
class MarketEvent:
    '''
    A market event is an indicator to carry out a trade 
    '''
    datetime: datetime
    type: str = field(default="MARKET", init=False)

#Tells what it wants to do EG: Long/Short/Exit
#Note: Exit applies to a short position as well.
@dataclass
class SignalEvent:
    '''
    A signal is the decision to buy/sell and how much based on a strategy
    '''
    ticker: str
    strategy_id : str
    datetime: datetime
    signal_type : SignalType
    strength: float
    type: str = field(default="SIGNAL", init=False)


#Generates actl order based on signal event
@dataclass
class OrderEvent:
    '''
    The order is a translation of a signal by the portfolio to a trade request to the brokerage
    based on various factors such as cash on hand, risk, ...
    '''
    ticker: str
    datetime: datetime
    order_type: OrderType
    quantity: int
    direction: DirectionType
    type: str = field(default="ORDER", init=False)


#After order is executed, fill event is generated to update the portfolio
@dataclass
class FillEvent:
    '''
    A fill event is the actual trade that occured which is produced by an ExecutionHandler and
    sent to the portfolio to update the data stored.
    '''
    ticker: str
    datetime: datetime
    quantity: int
    direction: DirectionType
    fill_cost: float
    commission: float
    type: str = field(default="FILL", init=False)
