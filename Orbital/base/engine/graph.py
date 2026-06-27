import os
import sys
import django
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Orbital.settings")
django.setup()

#import plotly.express as px
from queue import Queue
# from base.engine.monte_carlo_simulation import MonteCarloSimulator
from datetime import datetime
from base.engine.data_loader import Bar
from base.engine.backtest import Backtest
import pandas as pd
import plotly.graph_objects as go


# def get_equity_graph(equity_record: list[dict[str, any]]):
#     '''
#     This function takes in a DataFrame with the columns of
#     "date"
#     "equity"
#     Note that these columnsa are a min requirement, having more is acceptable
#     and returns a Figure objects from plotly.py. FigureObj.show() displays a graph
#     '''
#     data_frame = pd.DataFrame(equity_record)
#     #fig = px.line(data_frame=data_frame, x="date", y="equity")
#     return fig

def get_ohlv_graph(stock_data: list[Bar]):
    data = {
        'Date' : [bar.date for bar in stock_data],
        'Open' : [bar.open for bar in stock_data],
        'High' : [bar.high for bar in stock_data],
        'Low' : [bar.low for bar in stock_data],
        'Close' : [bar.close for bar in stock_data]
    }
    df = pd.DataFrame(data)
    fig = go.Figure(data=[go.Ohlc(
        x=df['Date'],
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close']
    )])
    return fig

def get_ohlv_graph2(stock_data: list[Bar]):
    data = {
        'Date' : [bar.date for bar in stock_data],
        'Open' : [bar.open_price for bar in stock_data],
        'High' : [bar.high_price for bar in stock_data],
        'Low' : [bar.low_price for bar in stock_data],
        'Close' : [bar.close_price for bar in stock_data]
    }
    df = pd.DataFrame(data)
    fig = go.Figure(data=[go.Ohlc(
        x=df['Date'],
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close']
    )])
    return fig



#def show_price_graphs(prices: list[list[float]]) -> px.Figure:
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