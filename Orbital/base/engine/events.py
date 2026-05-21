from models import StockPriceHistory, FuturesPriceHistory, Stock, FuturesContract
from data_loader import Bar
from datetime import datetime
from dataclasses import dataclass
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
    type: str 
    bar: Bar

#Tells what it wants to do EG: Long/Short/Exit
#Note: Exit applies to a short position as well.
@dataclass
class SignalEvent:
    symbol: str
    datetime: datetime
    signal_type : SignalType.choices
    strength: float


#Generates actl order based on signal event
@dataclass
class OrderEvent:
    symbol: str
    datetime: datetime
    order_type: OrderType.choices
    quantity: int
    direction: DirectionType.choices
    datetime: datetime


#After order is executed, fill event is generated to update the portfolio
@dataclass
class FillEvent:
    symbol: str
    datetime: datetime
    quantity: int
    direction: DirectionType.choices
    fill_cost: float
    commission: float = 0.0

