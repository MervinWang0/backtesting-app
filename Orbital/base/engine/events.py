from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional
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

class AssetType(models.TextChoices):
    STOCK = "STOCK", "Stock"
    FUTURES = "FUTURES", "Futures"
    FOREX = "FOREX", "Forex"

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
    asset_type: str
    #strategy_id : str
    datetime: datetime
    signal_type : SignalType
    strength: float
    stop_price: float | None = None
    type: str = field(default="SIGNAL", init=False)


#Generates actl order based on signal event
@dataclass
class OrderEvent:
    ticker: str
    asset_type: str
    datetime: datetime
    order_type: OrderType
    quantity: float
    direction: DirectionType

    #only for limit orders, ekse 
    limit_price: Optional[float] = None
    
    type: str = field(default="ORDER", init=False)


#After order is executed, fill event is generated to update the portfolio
@dataclass
class FillEvent:
    ticker: str
    asset_type: str
    datetime: datetime
    quantity: float
    direction: DirectionType
    fill_cost: float
    commission: float = 0.
    
    #for forex
    base_currency: Optional[str] = None
    quote_currency: Optional[str] = None

    #For futures
    contract_multiplier: Optional[float] = None
    contract_code: Optional[str] = None
    
    type: str = field(default="FILL", init=False)


