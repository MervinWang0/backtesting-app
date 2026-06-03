import pandas as pd
from math import sqrt
import json
import random
import numpy
from queue import Queue
from datetime import datetime
from base.engine.data_loader import DataLoader

# The metrics I'm interested in computing are these 10
# Total return
# Annualized return
# Sharpe Ratio
# Maximum Drawdown
# Calmar Ratio
# Win Rate
# Profit Factor
# Average Win/Loss Ratio
# Expectancy
# Sortino Ratio

def calculate_total_returns(trade_records_df, initial_capital):
    # Calculates total_return as a percentage of initial capital
    win_df = trade_records_df[trade_records_df['pnl'] >= 0]
    lose_df = trade_records_df[trade_records_df['pnl'] < 0]
    total_return = (win_df['pnl'].sum() + lose_df['pnl'].sum()) / initial_capital
    return total_return

def calculate_annualized_return(trade_records_df, initial_capital):
    # Calculates annualized_return (estimated return if carried out over a year)
    # annualized_return is compounding, days_traded is in calendar days. dates is a series of datetime values
    # .days is refering a field in the Timedelta object (produced by subtracting two datetime values)
    trade_records_df['date'] = pd.to_datetime(trade_records_df['date'])
    dates = trade_records_df['date']
    days_traded = (dates.max() - dates.min()).days
    total_return = calculate_total_returns(trade_records_df, initial_capital)
    annualized_return = (1 + total_return) ** (252 / days_traded) - 1
    return annualized_return

def calculate_sharpe_ratio(trade_records_df, initial_capital, risk_free_rate):
    # Calculates sharpe,
    # requires mean_returns, which is the mean daily returns as a percentage of initial capital
    daily_returns_df = trade_records_df.groupby('date')['pnl'].sum()
    daily_returns_percentage_df = daily_returns_df / initial_capital
    mean_returns = daily_returns_percentage_df.mean()
    std_dev_returns = daily_returns_percentage_df.std()
    sharpe = (mean_returns - risk_free_rate) / std_dev_returns * sqrt(252)
    return sharpe

def calculate_max_drawdown(trade_records_df, initial_capital):
    # Calculates Maximum Drawdown (MDD)
    # This is a simplified approach to calculating equity which ignores open holdings
    # An equity curve is created as a series. date : equity. Where equity = initial_capital + cumulative returns
    # equity_curve_df.cummax() => series of date : peak equity so far
    daily_returns_df = trade_records_df.groupby('date')['pnl'].sum()
    equity_curve_df = initial_capital + daily_returns_df.cumsum() 
    equity_peak_df = equity_curve_df.cummax() 
    # drawdown formula = (Peak equity - equity at day ) / Peak equity. There are multiple conventions
    # This one results in a positive value, the bigger it is, the greater the drawdown
    drawdown_df = (equity_peak_df - equity_curve_df) / equity_peak_df
    max_drawdown = drawdown_df.max()
    return max_drawdown

def calculate_calmar_ratio(trade_records_df, initial_capital):
    # Calculate Calmar Ratio
    annualized_return = calculate_annualized_return(trade_records_df, initial_capital)
    max_drawdown = calculate_max_drawdown(trade_records_df, initial_capital)
    calmar_ratio = annualized_return / max_drawdown 
    return calmar_ratio

def calculate_win_rate(trade_records_df):
    # Calculate Win Rate
    win_df = trade_records_df[trade_records_df['pnl'] >= 0]
    win_rate = len(win_df) / len(trade_records_df)
    return win_rate

def calculate_profit_factor(trade_records_df):
    # Calculate Profit Factor => total raw profit/loss
    win_df = trade_records_df[trade_records_df['pnl'] >= 0]
    lose_df = trade_records_df[trade_records_df['pnl'] < 0]
    profit_factor = abs(win_df['pnl'].sum() / lose_df['pnl'].sum())
    return profit_factor

def calculate_win_loss_ratio(trade_records_df):
    # Calculate Average Win/Loss Ratio. Avg Win / Avg Loss = |Mean(winning trade pnl) / |Mean(losing trade pnl)|
    win_df = trade_records_df[trade_records_df['pnl'] >= 0]
    lose_df = trade_records_df[trade_records_df['pnl'] < 0]
    win_loss_ratio = abs(win_df['pnl'].mean() / lose_df['pnl'].mean())
    return win_loss_ratio
    
def calculate_expectancy(trade_records_df):
    # Calculate Expectancy. Expectancy = (Win Rate × Avg Win) - (Loss Rate × Avg Loss)
    win_df = trade_records_df[trade_records_df['pnl'] >= 0]
    lose_df = trade_records_df[trade_records_df['pnl'] < 0]
    win_rate = calculate_win_rate(trade_records_df)
    # abs of loss_mean has to be taken otherwise - (loss mean) is additive
    expectancy = win_rate * win_df['pnl'].mean() - (1 - win_rate) * abs(lose_df['pnl'].mean())
    return expectancy

def calculate_sortino_ratio(trade_records_df, initial_capital, risk_free_rate):
    # Calculate Sortino Ratio. 
    # Sortino = (Mean(returns) - Rf) / StdDev(negative returns only) * sqrt(252)
    # Note that mean_returns is mean daily returns in percentage. daily_returns_percentage_df is a series not df
    daily_returns_df = trade_records_df.groupby('date')['pnl'].sum()
    daily_returns_percentage_df = daily_returns_df / initial_capital
    neg_daily_returns_percentage_stdev = daily_returns_percentage_df[daily_returns_percentage_df < 0].std()
    mean_returns = daily_returns_percentage_df.mean()
    sortino = (mean_returns - risk_free_rate) / neg_daily_returns_percentage_stdev * sqrt(252)
    return sortino


def calculate_metrics(trade_records_df, initial_capital, risk_free_rate):
    # Carry out some checks on the input
    assert len(trade_records_df) > 0, "trade_records_df cannot be empty"
    assert initial_capital > 0, "initial_capital must be greater than 0"
    assert risk_free_rate >= 0, "risk_free_rate cannot be negative"
    assert 'date' in trade_records_df.columns, "trade_records_df must have a 'date' column"
    assert 'pnl' in trade_records_df.columns, "trade_records_df must have a 'pnl' column"

    return {    'totalreturn': calculate_total_returns(trade_records_df, initial_capital),
                'annualized return': calculate_annualized_return(trade_records_df, initial_capital),
                'shapre ratio': calculate_sharpe_ratio(trade_records_df, initial_capital, risk_free_rate),
                'max drawdown': calculate_max_drawdown(trade_records_df, initial_capital),
                'calmar ratio': calculate_calmar_ratio(trade_records_df, initial_capital),
                'win rate': calculate_win_rate(trade_records_df),
                'profit factor': calculate_profit_factor(trade_records_df),
                'win loss ratio': calculate_win_loss_ratio(trade_records_df),
                'expectancy': calculate_expectancy(trade_records_df),
                'sortino': calculate_sortino_ratio(trade_records_df, initial_capital, risk_free_rate)
        }

