from dataclasses import dataclass
from decimal import Decimal


ZERO = Decimal("0")


@dataclass(frozen=True)
class PositionUpdate:
    prev_qty: Decimal
    new_qty: Decimal

    prev_entry_price: Decimal
    new_entry_price: Decimal

    closed_quantity: Decimal
    opened_quantity: Decimal
    realised_pnl: Decimal


def updatePosition(prev_qty: Decimal,prev_entry_price: Decimal, type: str,trade_qty: Decimal,entry_price: Decimal,) -> PositionUpdate:
    prev_qty = Decimal(str(prev_qty))
    prev_entry_price = Decimal(str(prev_entry_price))
    trade_qty = Decimal(str(trade_qty))
    entry_price = Decimal(str(entry_price))

    order_type = type.strip().upper()

    if order_type not in {"BUY", "SELL"}:
        raise ValueError(f"Invalid order type: {type}")

    if trade_qty <= ZERO:
        raise ValueError("Trade quantity must be greater than zero")

    signed_trade_qty = (
        trade_qty
        if order_type == "BUY"
        else -trade_qty
    )

    new_total_qty = prev_qty + signed_trade_qty

    # Opening a completely new position.
    if prev_qty == ZERO:
        return PositionUpdate(
            prev_qty=ZERO,
            new_qty=new_total_qty,
            prev_entry_price=ZERO,
            new_entry_price=entry_price,
            closed_quantity=ZERO,
            opened_quantity=trade_qty,
            realised_pnl=ZERO,
        )

    # Trade is adding to the current position:
    # long + buy, or short + sell.
    if prev_qty * signed_trade_qty > ZERO:
        previous_value = abs(prev_qty) * prev_entry_price
        added_value = trade_qty * entry_price

        new_entry_price = (
            previous_value + added_value
        ) / abs(new_total_qty)

        return PositionUpdate(
            prev_qty=prev_qty,
            new_qty=new_total_qty,
            prev_entry_price=prev_entry_price,
            new_entry_price=new_entry_price,
            closed_quantity=ZERO,
            opened_quantity=trade_qty,
            realised_pnl=ZERO,
        )

    # Trade is reducing, closing or reversing the position.
    closed_qty = min(abs(prev_qty), trade_qty)

    if prev_qty > ZERO:
        # Closing a long position.
        realised_pnl = (
            entry_price - prev_entry_price
        ) * closed_qty
    else:
        # Closing a short position.
        realised_pnl = (
            prev_entry_price - entry_price
        ) * closed_qty

    remaining_trade_qty = trade_qty - closed_qty

    # Partial close; original position remains open.
    if abs(new_total_qty) < abs(prev_qty):
        return PositionUpdate(
            prev_qty=prev_qty,
            new_qty=new_total_qty,
            prev_entry_price=prev_entry_price,
            new_entry_price=prev_entry_price,
            closed_quantity=closed_qty,
            opened_quantity=ZERO,
            realised_pnl=realised_pnl,
        )

    # Position is fully closed.
    if new_total_qty == ZERO:
        return PositionUpdate(
            prev_qty=prev_qty,
            new_qty=ZERO,
            prev_entry_price=prev_entry_price,
            new_entry_price=ZERO,
            closed_quantity=closed_qty,
            opened_quantity=ZERO,
            realised_pnl=realised_pnl,
        )

    # Existing position was closed and a new opposite position opened.
    return PositionUpdate(
        prev_qty=prev_qty,
        new_qty=new_total_qty,
        prev_entry_price=prev_entry_price,
        new_entry_price=entry_price,
        closed_quantity=closed_qty,
        opened_quantity=remaining_trade_qty,
        realised_pnl=realised_pnl,
    )