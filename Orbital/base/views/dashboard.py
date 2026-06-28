from django.shortcuts import render, redirect, get_object_or_404
from django.core.management import call_command
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db import transaction

#from django.contrib.auth import logout as auth_logout

from datetime import datetime
from base.models import StockPriceHistory, Stock, PaperAccount, PaperOrder, PaperTrade, PaperPositions
from decimal import Decimal
from django.db.models import DateField, DecimalField, F, FloatField, OuterRef, Q, Subquery, Value, BigIntegerField, ExpressionWrapper
from django.db.models.functions import Cast, NullIf
from django.core.paginator import Paginator
from base.services.paperTrading import execute_order
from base.engine.graph import get_ohlv_graph2
from base.forms import PaperAccountCreation, RegisterForm
from django.urls import reverse
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required

from queue import Queue
from base.engine.backtest import Backtest
from base.models import BacktestRun
import plotly.io as pio

# Create your views here.
PRICE_OUTPUT_FIELD = DecimalField(
    max_digits = 20,
    decimal_places = 2,
)

#register related
def register_view(request):
    # if request.user.is_authenticated:
    #     return redirect("dashboard")
    
    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save()

            login(request, user)

            messages.success(
                request, f"Welcome {user.username}"
            )

            return redirect("dashboard")
    else:
        form = RegisterForm()
    
    return render(
        request,
        "base/register.html",
        {
            "form": form,
        },
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

    accounts = (PaperAccount.objects.filter(user = request.user).order_by("name", "id"))
    selected_account = None
    positions = None
    orders = None
    trades = None
    if accounts.exists():
        selected_account_id = request.GET.get("account")

        if selected_account_id:
            selected_account = accounts.filter(id = selected_account_id).first()

        if selected_account is None:
            messages.warning(request, "Account could not be found")
    if selected_account is None:
        selected_account = accounts.first()
    
    if selected_account is None:
        context = {
            "accounts" : accounts,
            "selected_account" : None,
            "total_assets" : 0,
            "positions" : [],
            "orders" : [],
            "trades" : [],
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

    positions = (
        PaperPositions.objects.filter(account = selected_account)
        .select_related("stock")
        .order_by("stock__ticker")
    )

    trades = (
        PaperTrade.objects
        .filter(order__account=selected_account)
        .select_related("order", "order__stock")
        .order_by("-date")
    )

    total_assets = get_total_assets(positions, selected_account.cash_balance)

    context = {
        "accounts" : accounts,
        "selected_account" : selected_account,
        "total_assets" : total_assets,
        "positions" : positions,
        "orders" : orders,
        "trades" : trades,
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

def get_total_assets(positions, cash):
    assets = Decimal("0")
    for position in positions:
        latest_price = (StockPriceHistory.objects.filter(stock_id=position.stock_id).order_by('-date','-pk').values_list("close_price", flat=True).first())
        print("quantity:", repr(position.stock_quantity))
        print("price:", repr(latest_price))
        print("cash:", repr(cash))
        if latest_price is not None:
            qty = Decimal(str(position.stock_quantity))
            price = Decimal(str(latest_price))
            assets += (qty * price)
    return assets + cash


def stock(request):
    accounts = PaperAccount.objects.filter(user=request.user).order_by("name", "id")
    account_id = request.GET.get("account")
    selected_account = accounts.filter(pk=account_id).first()
    if selected_account is None:
        selected_account= accounts.first()
    symbol = request.GET.get("symbol")
    stock = Stock.objects.filter(ticker = symbol).first()
    latest_price = (
        StockPriceHistory.objects.filter(stock=stock).order_by("-date").first()
    )
    stock_data = StockPriceHistory.objects.filter(stock=stock).order_by("-date")
    
    graph = None

    

    if stock_data.exists():
        graph = get_ohlv_graph2(list(stock_data))
        graph = pio.to_html(
            graph,
            full_html=False,
            include_plotlyjs="cdn",
            config = {
                "responsive": True,
                "displaylog": False,
            }
        )

    context = {
        "stock": stock,
        "accounts" : accounts,
        "selected_account" : selected_account,
        "latest_price": latest_price,
        "graph" : graph,
    }
    
    return render(request, "stock.html", context)

@require_POST
def submit_paper_order(request, symbol):
    account_id = request.POST.get("account_id")
    account = get_object_or_404(PaperAccount, id = account_id, user = request.user)
    stock = Stock.objects.filter(ticker = symbol).first()

    type = request.POST.get("type")
    qty = request.POST.get("quantity")

    try:
        trade = execute_order(
            user = request.user,
            account_id= account.id,
            ticker= symbol,
            type = type,
            qty = qty,
        )
        print("TRADE CREATED:", trade)
        print("TRADE ID:", trade.pk)
        print("QUANTITY:", trade.quantity)
        print("PRICE:", trade.fulfilled_price)
    except Exception as error:
        print("ORDER ERROR:", repr(error))
        messages.error(
            request,
            f"Order failed: {error}",
        )
    else:
        messages.success(
            request,
            (
                f"{trade.order.type}"
                f"{trade.quantity}"
                f"{symbol}"
                f"${trade.fulfilled_price}"
            ),
        )
    url = reverse("stock")
    return redirect(f"{url}?symbol={symbol}&account={account.pk}")

def create_paper_account(request):
    if request.method == "POST":
        form = PaperAccountCreation(
            request.POST,
            user = request.user,
        )
        if form.is_valid():
            with transaction.atomic():
                account = form.save()
            
            messages.success(
                request,
                f"{account.name} paper account was created"
            )

            prev_url = reverse("dashboard")

            return redirect(f"{prev_url}?account={account.id}")
        
        print("FORM ERRORS:", form.errors)
        print("POST DATA:", request.POST)

    else:
        form = PaperAccountCreation(user=request.user)
    return render(request, "create_paper_account.html", {"form": form},)




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

#     backtest = Backtest(
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

@login_required
def portfolio(request):
    accounts = (
        PaperAccount.objects.filter(user=request.user).order_by("id")
    )

    selected_account = None
    positions = []
    trades = []

    selected_account_id = request.GET.get("account")

    if selected_account_id:
        selected_account = get_object_or_404(
            accounts,
            pk = selected_account_id,
        )
    else:
        selected_account = accounts.first()
    
    if selected_account:
        positions = (
            selected_account.positions
            .select_related("stock", "forex", "futures")
            .order_by("-updated_at")
        )

        trades = (
            PaperTrade.objects.filter(order__account = selected_account)
            .select_related("order")
            .order_by("-executed_at", "-id")
        )
    
    context = {
        "accounts": accounts,
        "selected_account": selected_account,
        "positions" : positions,
        "trades" : trades,
    }

    return render(request, "portfolio.html", context)