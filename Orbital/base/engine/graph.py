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
# from base.engine.monte_carlo_simulation import MonteCarloSimulator
from datetime import datetime
from base.engine.data_loader import DatabaseDataLoader, Bar
import pandas as pd
import plotly.graph_objects as go
from functools import wraps
from time import time

def timed(f):
    '''
    This function is used to time any function
    Usage syntax
    @timed
    def funct()
    '''

    @wraps(f)
    def wrapper(*args, **kwds):
        start = time()
        result = f(*args, **kwds)
        elapsed = time() - start
        print(f"function {f.__name__} took {elapsed}")
        return result
    return wrapper

def get_equity_graph(equity_record: pd.DataFrame) -> px.Figure:
    '''
    This function takes in a DataFrame with the columns of
    "date"
    "equity"
    Note that these columnsa are a min requirement, having more is acceptable
    and returns a Figure objects from plotly.py. FigureObj.show() displays a graph
    '''
    fig = px.line(data_frame=equity_record, x="date", y="equity")
    return fig

def get_stock_graph(stock_data: list[Bar]) -> px.Figure:
    '''
    Returns a figure that stores OHLC data.
    '''

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

@timed
def get_monte_graph(btr_lst: list[BacktestResult]) -> px.Figure:
    '''
    This function takes in a list of backtest results, basically the ouput of MCS simulate,
    and plots their equity graphs
    '''
    # Each figure has multiple traces, each trace has to be added seperately
    figs = list(map(lambda btr: btr.get_equity_graph(), btr_lst))
    og_fig = figs.pop(0)
    for fig in figs:
        traces = fig.select_traces()
        for trace in traces:
            og_fig.add_traces(trace) 
    og_fig.data[0].line.color = "black"
    return og_fig

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
    fig.data[0].line.color = 'black'
    return fig

def get_ohlv_graph2(stock_data: list[StockPriceHistory]):
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

if __name__ == "__main__":
    pass

