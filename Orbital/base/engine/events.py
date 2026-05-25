from models import StockPriceHistory, FuturesPriceHistory, Stock, FuturesContract
from data_loader import Bar
from datetime import datetime
from dataclasses import dataclass, field
from django.db import models

class SignalType(models.TextChoices):
        LONG = "LONG", "Long"
        SHORT = "SHORT", "Short"
        EXIT = "EXIT", "Exit"

class OrderType(models.TextChoices):
        MKT = "MKT", "Market"
        LMT = "LMT", "Limit"

class DirectionType(models.TextChoices):
        BUY = "BUY", "Buy"
        SELL = "SELL", "Sell"


#dataclass to track whenever a new bar is generated
@dataclass
class MarketEvent:
    datetime: datetime
    type: str = field(default="MARKET", init=False)

#Tells what it wants to do EG: Long/Short/Exit
#Note: Exit applies to a short position as well.
@dataclass
class SignalEvent:
    ticker: str
    strategy_id : str
    datetime: datetime
    signal_type : SignalType
    strength: float
    type: str = field(default="SIGNAL", init=False)


#Generates actl order based on signal event
@dataclass
class OrderEvent:
    ticker: str
    datetime: datetime
    order_type: OrderType
    quantity: int
    direction: DirectionType
    type: str = field(default="ORDER", init=False)


#After order is executed, fill event is generated to update the portfolio
@dataclass
class FillEvent:
    ticker: str
    datetime: datetime
    quantity: int
    direction: DirectionType
    fill_cost: float
    commission: float = 0.0
    type: str = field(default="FILL", init=False)


