import os
import sys
import django
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Orbital.settings")
django.setup()

import plotly.express as px
from queue import Queue
from base.engine.monte_carlo_simulation import MonteCarloSimulator
from datetime import datetime
from base.engine.data_loader import DatabaseDataLoader
from base.engine.backtest import Backtest
import pandas as pd


def equity_graph(df: pd.DataFrame) -> px.Figure:
    '''
    This function takes in a DataFrame with the columns of
    "date"
    "equity"
    Note that these columnsa are a min requirement, having more is acceptable
    and returns a Figure objects from plotly.py. FigureObj.show() displays a graph
    '''
    fig = px.line(data_frame=df, x="date", y="equity")
    return fig

def show_price_graphs(prices: list[list[float]]) -> px.Figure:
    df = pd.DataFrame(prices).T
    # print(df)
    df = df.rename(columns={i: 'OG' if i == 0 else f"Sim {i}" for i in range(len(df))})
    # print(df)

    # Label each column

    # highlight_col = "OG"
    # highlight_colour = "black"
    # non_highlight_colour = "#837B7B"
    # color_map = {col : (highlight_colour if col == highlight_col else "blue")
                #  for col in df}

    fig = px.line(df)
    fig.update_layout(xaxis_title="Date",
                      yaxis_title="Price")
    return fig

if __name__ == "__main__":
    start_date = datetime.fromisoformat("2021-05-24").date()
    end_date = datetime.fromisoformat("2023-06-07").date()
    data_loader = DatabaseDataLoader(Queue(), ["AAPL"], start_date,
                             end_date, "STOCK")
    backtest = Backtest(
                        events=Queue(),
                        tickers=["AAPL"],
                        start_date=start_date,
                        end_date=end_date,
                        strategy_name="MovingAverageCross",
                        strategy_params={"short_window": 5,
                                        "long_window": 10},
                        data_loader=DatabaseDataLoader(events=Queue(),
                                                    tickers=["AAPL"],
                                                    start_date=start_date,
                                                    end_date=end_date,
                                                    asset_type="STOCK"))
    backtest.run()
    stock_data = backtest.data_loader.get_past_bars("AAPL",
                len(backtest.data_loader.get_timeline()))
    mcs = MonteCarloSimulatior(backtest)

    # Creates a dataframe for graph testing
    df = pd.DataFrame()
    for equity_record in mcs.simulate(1):
        df = pd.DataFrame(equity_record.get_equity_records())
    equity_graph(df).show()

