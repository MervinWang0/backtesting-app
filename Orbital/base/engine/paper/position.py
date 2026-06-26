from decimal import Decimal
from dataclasses import dataclass

zero = Decimal("0")

@dataclass
class PositionUpdate(frozen=True):
    prev_qty : Decimal
    new_qty : Decimal

    prev_entry_price : Decimal
    new_entry_price : Decimal

    closed_quantity : Decimal
    opened_quantity : Decimal 
    realised_pnl : float

def updatePosition(prev_qty : Decimal, prev_entry_price : Decimal, type : str, trade_qty : Decimal, entry_price : Decimal):
    type = type.upper()

    signed_trade_qty = (trade_qty if type == "BUY" else -trade_qty)

    new_total_qty = prev_qty + signed_trade_qty

    #Open a new position from 0 qty
    if prev_qty == 0:
        return PositionUpdate(
            prev_qty= 0,
            new_qty = new_total_qty,
            prev_entry_price= Decimal("0"),
            new_entry_price= entry_price,
            closed_quantity= Decimal("0"),
            opened_quantity= new_total_qty,
            realised_pnl=Decimal("0"),
        )

    #Trade in same direction as current position, long + buy, short + sell
    if prev_qty * new_total_qty > zero:
        prev_total = abs(prev_qty) * prev_entry_price
        curr_total = trade_qty * entry_price
        avg = (prev_total + curr_total) / abs(new_total_qty)

        return PositionUpdate(
            prev_qty= prev_qty,
            new_qty = new_total_qty,
            prev_entry_price= prev_entry_price,
            new_entry_price= entry_price,
            closed_quantity= zero,
            opened_quantity= new_total_qty,
            realised_pnl=Decimal("0"),
        ) 
    
    #Opposite directions
    closed_qty = min(abs(prev_qty), trade_qty)

    if closed_qty > zero:
        realised_pnl = (entry_price - prev_entry_price) * closed_qty
    else:
        realised_pnl = (prev_entry_price - entry_price) * closed_qty
    
    remaining_qty = (trade_qty - closed_qty)

    #Close some, position still open
    if abs(new_total_qty) < abs(prev_qty):
        return PositionUpdate(
            prev_qty= prev_qty,
            new_qty = new_total_qty,
            prev_entry_price= prev_entry_price,
            new_entry_price= entry_price,
            closed_quantity= closed_qty,
            opened_quantity= zero,
            realised_pnl=realised_pnl,
        ) 
    
    #Close out all positions:
    if new_total_qty == zero:
        return PositionUpdate(
            prev_qty= prev_qty,
            new_qty = new_total_qty,
            prev_entry_price= prev_entry_price,
            new_entry_price= entry_price,
            closed_quantity= closed_qty,
            opened_quantity= zero,
            realised_pnl= realised_pnl,
        ) 

    #Opposite direction 
    return PositionUpdate(
        prev_qty= prev_qty,
        new_qty = new_total_qty,
        prev_entry_price= prev_entry_price,
        new_entry_price= entry_price,
        closed_quantity= closed_qty,
        opened_quantity= remaining_qty,
        realised_pnl=realised_pnl,
    ) 

