from django.shortcuts import render, redirect, get_object_or_404
from django.core.management import call_command






#from django.contrib.auth import logout as auth_logout

from datetime import datetime
from base.models import StockPriceHistory, Stock
from decimal import Decimal
from django.db.models import (DateField, DecimalField,
F, FloatField, OuterRef, Q, Subquery, Value, BigIntegerField, ExpressionWrapper)
from django.db.models.functions import Cast, NullIf
from django.core.paginator import Paginator


from queue import Queue
from base.engine.backtest import Backtest
from base.models import BacktestRun
from base.engine.data_loader import DatabaseDataLoader

# Create your views here.
PRICE_OUTPUT_FIELD = DecimalField(
    max_digits = 20,
    decimal_places = 2,
)

#Dashboard related
def dashboard(request):
    latest_price_rows = (StockPriceHistory.objects.filter(stock_id =OuterRef("pk")).order_by("-date", "pk"))
    market_stocks = (Stock.objects.all().all().annotate(
                                                latest_price = Subquery(
                                                    latest_price_rows.values("close_price")[:1],
                                                    output_field = PRICE_OUTPUT_FIELD,
                                                ),

                                                previous_close = Subquery(
                                                    latest_price_rows.values("close_price")[1:2],
                                                    output_field = PRICE_OUTPUT_FIELD,
                                                ),

                                                latest_volume = Subquery(
                                                    latest_price_rows.values("volume")[:1],
                                                    output_field = BigIntegerField(),
                                                ),

                                                latest_date = Subquery(
                                                    latest_price_rows.values("date")[:1],
                                                    output_field = DateField(),
                                                ),
                                                ).annotate(
                                                    price_change = ExpressionWrapper(
                                                        F("latest_price") - F("previous_close"),
                                                        output_field= PRICE_OUTPUT_FIELD,
                                                    ),
                                                    percentage_change = ExpressionWrapper(
                                                        (
                                                            Cast(F("latest_price"), FloatField())
                                                            - Cast(F("previous_close"), FloatField())
                                                        )
                                                        * 100.0
                                                        / NullIf(
                                                            Cast(F("previous_close"), FloatField()),
                                                            0.0,
                                                        ),
                                                        output_field=FloatField(),
                                                    ),
                                                    dollar_volume = ExpressionWrapper(
                                                        Cast(F("latest_price"), FloatField())
                                                        * Cast(F("latest_volume"),FloatField()),
                                                        output_field=FloatField(),
                                                    ),
                                                )
    
    )

    most_active_traded = list(
        market_stocks.exclude(latest_volume__isnull=True)
        .order_by("-latest_volume")[:5]
    )

    most_active_dollar = list(
        market_stocks.exclude(dollar_volume__isnull=True)
        .order_by("-dollar_volume")[:5]
    )

    stocks = market_stocks

    search_query = request.GET.get("q", "").strip()

    if search_query:
        stocks = stocks.filter(
            Q(ticker__icontains = search_query) | Q(name__icontains = search_query)
        )
    
    portfolio_summary = get_porfolio_summary(request)

    paginator = Paginator(stocks, 30)
    page = paginator.get_page(request.GET.get("page"))

    context = {
        "page" : page,
        "most_active_traded": most_active_traded,
        "most_active_dollar" : most_active_dollar,
        "US_Assets" : portfolio_summary["US_Assets"],
        "today_pnl" : portfolio_summary["Today_pnl"],
        "filters" : {
            "q" : search_query,
        },
     }

    return render(request, "dashboard.html", context)

def get_porfolio_summary(user):
    return {
        "US_Assets" : Decimal("9999.99"),
        "Today_pnl" : Decimal("999.99"),
    }

def stock(request):
    symbol = request.GET.get("symbol")
    stock = Stock.objects.filter(ticker = symbol).first()
    latest_price = (
        StockPriceHistory.objects.filter(stock=stock).order_by("-date").first()
    )

    context = {
        "stock": stock,
        "latest_price": latest_price,
    }
    
    return render(request, "stock.html", context)



def get_yf_period(start_date, end_date):
    days = (end_date - start_date).days +1

    if days <= 31:
        return "1mo"
    elif days <= 93:
        return "3mo"
    elif days <= 186:
        return "6mo"
    elif days <= 365:
        return "1y"
    elif days <=730:
        return "2y"
    elif days <=1825:
        return "5y"
    elif days <= 3650:
        return "10y"
    else:
        return "max"

def data_exists(symbol, start_date, end_date):
    stock = Stock.objects.filter(ticker = symbol).first()

    if not stock:
        return False
    
    bars = StockPriceHistory.objects.filter(stock = stock, date__range = (start_date, end_date),)

    if not bars.exists():
        return False

    return True    

#  I don't understand this code I'm going to comment it out
# def backtest_run(request):
#     start_date = request.POST.get("start_date")
#     end_date = request.POST.get("end_date")
#     ticker = request.POST.get("ticker","").upper().strip()

#     start_date_fixed = datetime.strptime(start_date, "%Y-%m-%d").date()
#     end_date_fixed = datetime.strptime(end_date, "%Y-%m-%d").date()

#     period = get_yf_period(start_date_fixed, end_date_fixed)

#     if not data_exists(ticker, start_date_fixed, end_date_fixed):
#         call_command(
#             "load_stock_data",
#             symbol = ticker,
#             period = period,
#             interval = "1d",
#         )

#     events = Queue()
#     # I'm placing asset_type as "STOCK" for now, because I don't understand
#     # the post method of this function well enough to pass asset_type in
#     data_loader = DatabaseDataLoader(events=events,
#                                      tickers=[ticker],
#                                      start_date=start_date_fixed,
#                                      end_date=end_date_fixed,
#                                      asset_type="STOCK")
#         events = events,
#         tickers = [ticker],
#         start_date = start_date_fixed,
#         end_date = end_date_fixed,
#         strategy_name= "MAC",
#     )

#     backtest_run = backtest.run()
#     return redirect(f"/backtestrunrecords/?run_id={backtest_run.id}")

def backtest_run_records(request):
    run_id = request.GET.get("run_id")
    date_query = request.GET.get("date")

    if run_id:
        selected_run = get_object_or_404(BacktestRun, id=run_id)
    else:
        return None
    
    dates = []
    equity_record = None
    position_record = []
    fill_record = []

    if selected_run:
        dates = selected_run.equity_record.values_list("date", flat=True).distinct().order_by("date")
        if not date_query:
            date_query = dates.last()
        
        equity_record = selected_run.equity_record.filter(date = date_query).first()
        position_record = selected_run.position_record.filter(date=date_query)
        fill_record = selected_run.fill_record.filter(date = date_query)

    return render(request, "backtestrunrecords.html", {
        "selected_run": selected_run,
        "dates": dates,
        "date_query": date_query,
        "equity_record": equity_record,
        "position_record": position_record,
        "fill_record": fill_record,
    })