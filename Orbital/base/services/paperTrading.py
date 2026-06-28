from base.engine.paper.position import updatePosition
from base.models import PaperAccount, PaperOrder, PaperPositions, PaperTrade, Stock, StockPriceHistory, ForexPair, FuturesContract
from django.contrib.auth import get_user_model
from decimal import Decimal

from django.db import transaction
from django.utils import timezone



User = get_user_model()
zero = Decimal("0")

def load_stock_data(ticker: str):
        rows = (StockPriceHistory.objects.filter(stock__ticker=ticker).order_by('-date').first())
        return rows.date, rows.close_price

def calc_cash(type: str, qty : Decimal, entry_price : Decimal, commission: Decimal):
        gross = (qty * entry_price)
        
        if type == PaperOrder.Order.BUY:
            cash = -(gross + commission)
        else:
            cash = gross - commission
        
        return gross, cash

def execute_order(user , account_id: int, ticker : str, type : str, qty : Decimal):
    qty = Decimal(str(qty))
    try: 
        account_ref = PaperAccount.objects.get(id = account_id, user=user)
    except PaperAccount.DoesNotExist as e:
         raise ValueError("paper account not found") from e
    
    stock = Stock.objects.get(ticker = ticker)

    order = PaperOrder.objects.create(
         account = account_ref,
         stock = stock,
         type = type,
         quantity = qty,
         status = PaperOrder.Status.PENDING,
    )

    try:
         with transaction.atomic():
            account = (PaperAccount.objects.select_for_update()
                                    .get(
                                         id = account_ref.id,
                                         user = user,
                                    ))
            final_order = (PaperOrder.objects.select_for_update()
                                    .get(id = order.id))

            date, price = load_stock_data(ticker)  
            price = Decimal(str(price))

            position = (PaperPositions.objects.select_for_update()
                        .filter(
                             account=account,
                             stock=stock,
                        )).first()
            
            if position is None:
                 position = PaperPositions.objects.create(
                    account = account,
                    stock = stock,
                    stock_quantity=zero,
                    avg_cost = zero,
                    realised_pnl = zero,
                 )
            
            prev_qty = position.stock_quantity
            prev_entry_price = position.avg_cost

            position_update = updatePosition(
                 prev_qty= prev_qty,
                 prev_entry_price=prev_entry_price,
                 type = type,
                 trade_qty= qty,
                 entry_price= price,
            )

            commission = zero

            gross, cash = calc_cash(type=type, qty= qty, entry_price= price, commission=commission)

            realised_pnl = (position_update.realised_pnl)
            account.cash_balance = (account.cash_balance + cash)
            position.stock_quantity = position_update.new_qty
            position.avg_cost = position_update.new_entry_price
            position.realised_pnl = position.realised_pnl + position_update.realised_pnl

            account.save(update_fields=[
                 "cash_balance",
                 "updated_at",
            ])

            position.save(
                 update_fields=[
                      "stock_quantity",
                      "avg_cost",
                      "realised_pnl",
                      "updated_at",
                 ]
            )

            trade = PaperTrade.objects.create(
                order = final_order,
                date = date,
                fulfilled_price = price,
                quantity = qty,
                closed_quantity = position_update.closed_quantity,
                opened_quantity = position_update.opened_quantity,
                gross_amount = gross,
                commission = commission,
                realised_pnl = realised_pnl,
                cash_change = cash,
            )

            final_order.status = PaperOrder.Status.FILLED
            final_order.filled_at = timezone.now()
            
            final_order.save(
                 update_fields=[
                      "status",
                      "filled_at",
                      "updated_at"
                 ]
            )

            return trade
    except:
        PaperOrder.objects.filter(
              id = order.id,
              status = PaperOrder.Status.PENDING,
        ).update(
              status = PaperOrder.Status.REJECTED,
        )
        raise
         