from django.shortcuts import render, redirect, get_object_or_404







#from django.contrib.auth import logout as auth_logout

from datetime import datetime


from queue import Queue
from base.engine.backtest import Backtest
from base.models import BacktestRun

# Create your views here.
def dashboard(request):
    return render(request, "dashboard.html")


def backtest_run(request):
    start_date = request.POST.get("start_date")
    end_date = request.POST.get("end_date")
    ticker = request.POST.get("ticker","").upper().strip()

    start_date_fixed = datetime.strptime(start_date, "%Y-%m-%d").date()
    end_date_fixed = datetime.strptime(end_date, "%Y-%m-%d").date()

    events = Queue()

    backtest = Backtest(
        events = events,
        tickers = [ticker],
        start_date = start_date_fixed,
        end_date = end_date_fixed,
        strategy_name= "MAC",
    )

    backtest_run = backtest.run()
    return redirect(f"/backtestrunrecords/?run_id={backtest_run.id}")

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



