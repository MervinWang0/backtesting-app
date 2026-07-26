from base.engine.events import SignalEvent
from base.engine.data_loader import DataLoader, Bar
from base.engine.execution import ExecutionLoader
from queue import Queue
from abc import ABC,abstractmethod
from functools import wraps
from time import time
import numpy as np
import pandas as pd
from dataclasses import dataclass
import math

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

# Config classes to reduce the number of args passed into
# functions at once

@dataclass
class RSIConfig:
    window: int
    ticker: str
    prev_AG: float = None
    prev_AL: float = None
    oversold: int = 30
    overbought: int = 70

@dataclass
class BollingerConfig:
    window: int
    ticker: str

@dataclass
class ZConfig:
    window: int
    ticker: str
    lower: float = -2
    upper: float = 2

class Strategy(ABC):
    def __init__(self,
                 data_loader: DataLoader,
                 strength: float = 1,
                 ):
        ''' 
        Some attributes are common to all trading strategies.
        1. data_loader

        Methods
        Generally methods to calculate metrics return None if 
        They cannot be calculated based on various conditions
        '''
        self.data_loader = data_loader
        self.tickers: list[str] = data_loader.get_tickers()
        self.strength = strength

        # The below params are updated by the get_rsi method
        self.prev_AG: dict[str, float] = {}
        self.prev_AL: dict[str, float] = {}
        self.rsi = {}
        


    @abstractmethod
    def generate_signal(self, ticker: str) -> SignalEvent:
        ''' 
        Takes in nothing and generates a SignalEvent
        '''

    # pre-compute indicators at the start for better bug checking and efficiency
    # def calculate_rsi(self, ticker, period=14):
    #     prices = [bar.close for bar in self.data_loader.stock_data[ticker]]
    #     diff = pd.DataFrame(prices).diff()
        
    #     # 2. Isolate gains and losses
    #     gain = diff.clip(lower=0)
    #     loss = -diff.clip(upper=0)
    #     print(f"This is the gain, and loss : {gain, loss}")
        
    #     avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    #     avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
        
    #     # 4. Calculate Relative Strength (RS)
    #     rs = avg_gain / avg_loss
        
    #     # 5. Calculate RSI and map it to 0-100
    #     rsi = 100 - (100 / (1 + rs))
    #     return rsi
                
                
    # These methods are used to calculate metrics


    def get_percent_k_d_list(self, window: int, ticker: str) -> pd.Series:
        ''' 
        Generates the entire list at the start using pd
        
        Note that the current day is excluded from calculating
        '''
        data = self.data_loader.stock_data[ticker]
        high = pd.Series([bar.high for bar in data])
        low = pd.Series([bar.low for bar in data])
        close = pd.Series([bar.close for bar in data])
        df = pd.DataFrame()

        # Store the highest and lowest prices each day looking back window days
        # Conventional definition does not require shift
        df['upper'] = high.rolling(window=window).max()
        df['lower'] = low.rolling(window=window).min()
        df['close'] = close
        df['k'] = (df['close'] - df['lower']) / (df['upper'] - df['lower']) * 100
        df['d'] = df['k'].rolling(window=3).mean()
        # print(f'These are the k d lines \n{df.to_string()}')
        return df

    def get_roc(self, window: int, ticker: str) -> float:
        ''' 
        This method obtains price roc 
        
        This method computes by day and does not return a list
        
        1 window day ago requires 2 days to be loaded,
        '''
        curr_price = self.data_loader.get_current_bar_value(ticker=ticker,
                                                            value_type='close')
        price_n_days_ago = self.get_window_bars(ticker=ticker,
                                                window=window + 1)
        if curr_price is None or price_n_days_ago is None:
            return None
        # print(len(price_n_days_ago))
        n_price = price_n_days_ago.pop(0).close
        roc = (curr_price - n_price) / n_price * 100
        # print(f"This is price n days ago {n_price}")
        # print(f"This is the curr price = {curr_price}")
        # print(f"This is the roc {roc}")
        return roc

    def get_donchian_channels(self, window:int, ticker:str) -> pd.DataFrame:
        ''' 
        Returns a df with the columns of min/max/medium price of the past window days
        non-inclusive of the current day
        '''
        data = self.data_loader.stock_data[ticker]
        high = pd.Series([bar.high for bar in data])
        low = pd.Series([bar.low for bar in data])
        df = pd.DataFrame()
        df['upper'] = high.rolling(window=window).max().shift(1)
        df['lower'] = low.rolling(window=window).min().shift(1)
        df['middle'] = (df['upper'] + df['lower']) / 2
        # print(f'These are the donchian channels {df.to_string()}')
        return df

    def get_ema_list(self, window: int, ticker: str) -> pd.Series:
        ''' 
        Return a list, with each element being the ema at that day.
        For the period
        '''
        prices = [bar.close for bar in self.data_loader.stock_data[ticker]]
        data = {'close' : prices}
        df = pd.DataFrame(data)
        # adjust=False calculates the first value with a sma, conventional method
        df['ema'] = df['close'].ewm(span=window, adjust=False).mean()
        # print(df)
        # print(type(df['ema']))
        # print(f"This is the length of data {len(prices)}")
        return df['ema']

    def get_rolling_z_score(self, window: int, ticker: str) -> float:
        '''
        Calculate and return the Z score over the pass window days.
        
        Formula: (Today's Close - Rolling Mean) / Rolling Std
        
        TODO Conceptual error, the mean and std should not include current day's close price
        '''
        if window == 1:
            raise ValueError("Z score is undefined for 1 day window, as std = 0,"
                             "Causing a divide by 0 error")
        today_close = self.data_loader.get_current_bar_value(ticker=ticker, value_type="close")
        rolling_std = self.get_rolling_std(ticker=ticker, window=window)
        rolling_mean = self.get_rolling_mean(ticker=ticker, window=window)
        if rolling_mean is None or rolling_std is None:
            return None
        return (today_close - rolling_mean) / rolling_std

    def get_window_bars(self, ticker: str, window: int) -> list[Bar]:
        ''' 
        Obtain a list of past bars based on a window
        
        Note that this is inclusive of current bar
        '''
        # print("generating signal for ticker", ticker)
        try:
            window_bars = self.data_loader.get_past_bars(ticker, window)
        except ValueError:
            # print(f"Not enough bars yet for {ticker}. Need {window}.")
            window_bars = None
        return window_bars

    def get_rsi(self, window: int, ticker: str) -> int:
        ''' 
        Calculate the RSI of a ticker based on a window. Requires previous average to
        determine new average.

        prev_AG and prev_AL are None when the days loaded is less than the window

        output is (RSI, new_AG, new_AL)
        
        Returns None if the bars loaded is less than window
        '''
        # print("Computing RSI")
        # print(f"prev_AL = {self.prev_AL[ticker]}")
        # print(f"prev_AG = {self.prev_AG[ticker]}")
        
        # Try and load the bars
        window_bars = self.get_window_bars(ticker, window + 1)
        if window_bars is None:
            return None

        # Obtain the list of prices, with should be of length
        # window + 1 (after difference bcomes length window)
        closes = [bar.close for bar in window_bars]

        # Consider the case when window + 1 first matches days loaded,
        # first AG AL calculated
        # print(f"Days loaded = {self.data_loader.get_days_loaded()}")
        if window + 1 == self.data_loader.get_days_loaded():
            # Testing
            # print("This is the original prices \n")
            # print(closes)
            # print("This is the difference in prices \n")
            # print(pd.DataFrame(closes).diff().dpona())

            # Note that this has one less element should be len window
            price_change = pd.Series(closes).diff().dropna()

            # Obtain AG and AL
            new_ag = abs(price_change[price_change > 0].sum() / window)
            new_al = abs(price_change[price_change < 0].sum() / window)
            if new_ag is None or new_al is None:
                raise ValueError("al and ag should not be none")
            
            rs = new_ag / new_al
            rsi = int(100 - (100/ (1 + rs)))
            # print(f"This is rsi, it should be an int :{rsi}")
            self.prev_AG[ticker] = new_ag
            self.prev_AL[ticker] = new_al
            return rsi

        # Updating old ag and al to new ag al
        current_change = self.data_loader.get_current_change(ticker)
        # print(f"This is the current change {current_change}")
        current_gain = max(current_change, 0)
        current_loss = max(-current_change, 0)
        new_ag = abs((self.prev_AG[ticker] * (window - 1)) + current_gain) / window
        new_al = abs((self.prev_AL[ticker] * (window - 1)) + current_loss) / window

        rs = new_ag / new_al
        rsi = int(100 - (100/ (1 + rs)))
        # print(f"This is rsi, it should be an int :{rsi}")
        self.prev_AG[ticker] = new_ag
        self.prev_AL[ticker] = new_al
        return rsi

    def get_bollinger_bands(self, window: int, ticker: str) -> tuple[float, float, float]:
        ''' 
        Returns a tuple of (low band, middle band, high band) prices for the day
        '''
        middle_band = self.get_rolling_mean(window, ticker)
        sigma = self.get_rolling_std(window, ticker)
        # print(f"this is the sigma for the day {sigma}")
        if middle_band is None or sigma is None:
            return None
        return (middle_band - 2 * sigma, middle_band,
                middle_band + 2 * sigma)

    def get_rolling_mean_exclusive(self, window: int, ticker: str) -> float:
        ''' 
        Returns a mean, calculating using the past n days, where the current day
        is not calculated
        
        E.g 20 day average on day 21, is the average of day 1 - 20 inclusive
        '''
        window_bars = self.get_window_bars(ticker, window + 1)
        if window_bars is None:
            return None
        closes = [bar.close for bar in window_bars]
        # Remove today's prices such that it isn't included in avg
        closes.pop()
        return sum(closes) / len(closes)

    def get_rolling_mean(self, window: int, ticker: str ) -> float:
        ''' 
        Return the historical mean calculated for the past window days.
        Uses the close price. Returns None if days traded < window.
        '''
        window_bars = self.get_window_bars(ticker, window)
        if window_bars is None:
            return None
        closes = [bar.close for bar in window_bars]
        return sum(closes) / len(closes)

    def get_rolling_std_exclusive(self, window: int, ticker: str ) -> float:
        ''' 
        Average without including current day
        '''
        window_bars = self.get_window_bars(ticker, window + 1)
        if window_bars is None:
            return None
        closes = [bar.close for bar in window_bars]
        closes.pop()
        return float(np.std(closes, ddof=1))

    def get_rolling_std(self, window: int, ticker: str ) -> float:
        ''' 
        Return the historical std calculated for the past window days.
        Uses the close price. Returns None if days traded < window.
        '''
        window_bars = self.get_window_bars(ticker, window)
        if window_bars is None:
            return None
        closes = [bar.close for bar in window_bars]
        return float(np.std(closes, ddof=1))

    # These methods obtain some sort of indicator from the metrics
    def get_rsi_signal(self, config: RSIConfig) -> str:
        ''' 
        Based on some parameters, determine if market condition is
        overbought or oversold
        '''
        rsi_value = self.get_rsi(window=config.window, ticker=config.ticker)
        if rsi_value is None:
            return "neutral"
        if rsi_value < config.oversold:
            return "oversold"
        elif rsi_value > config.overbought:
            return "overbought"
        return "neutral"

    def get_bollinger_signal(self, config: BollingerConfig):
        ''' 
        Based on some parameters, determine if market condition is
        overbought or oversold
        '''
        bands = self.get_bollinger_bands(window=config.window,
                                         ticker=config.ticker)
        if bands is None:
            return "neutral"
        lower_band = bands[0]
        upper_band = bands[2]
        curr_price = self.data_loader.get_current_bar_value(
            ticker=config.ticker, value_type='close')
        if curr_price < lower_band:
            return "oversold"
        elif curr_price > upper_band:
            return "overbought"
        return "neutral"

    def get_z_score_signal(self, config: ZConfig) -> str:
        ''' 
        Based on some parameters, determine if market condition is
        overbought or oversold
        '''
        z = self.get_rolling_z_score(window=config.window,
                                     ticker=config.ticker)
        if z is None:
            return "neutral"
        if z < config.lower:
            return "oversold"
        elif z > config.upper:
            return "overbought"
        return "neutral"

    def obtain_market_condition(self, logic: str, rsi_config: RSIConfig,
                                bollinger_config: BollingerConfig,
                                z_config: ZConfig):
        '''
        logic is used to combine signals to buy/sell

        and => buy/sell when market conditions are same
        majority => buy/sell based on majority
        
        Returns decision which is either, none, buy or sell
        '''
        # condition determine threshold of signals agreeing to buy/sell
        condition = 0
        if logic == "AND":
            condition = 3
        elif logic == "MAJORITY":
            condition = 2
        else:
            raise ValueError("The logic is not correctly specified"
                             " for obtaining market condition")

        # market conditions stores the condition of the market
        # as determined by different indicators
        market_conditions: list[str] = []

        market_conditions.append(self.get_rsi_signal(rsi_config))
        market_conditions.append(
            self.get_bollinger_signal(bollinger_config))
        market_conditions.append(self.get_z_score_signal(z_config))
        # print("-----Market Conditions determined by "
        #       "indicators for Mean Reversion-----\n")
        # print(f"These are the market conditions = {market_conditions}\n")
        # If any of the metrics cannot be compyted yet due to insufficient
        # data, do not trade
        if None in market_conditions:
            return None
        
        count = 0
        for market in market_conditions:
            if market == 'overbought':
                count += 1
            elif market == 'oversold':
                count -= 1

        # Decision is either buy, sell or none
        decision = None
        if abs(count) >= condition and count > 0:
            decision = "SHORT"
        elif abs(count) >= condition and count < 0:
            decision = "LONG"
        else:
            decision = None
            
        # print(f"This is the market condition = {market_conditions}\n"
        #       f"This is the decision from the market = {decision}")
        return decision

    def get_k_signal(self, k: float):
        ''' 
        Uses standard overbought and oversold threshold to determine
        if the k value indicates the market is overbought or oversold
        '''
        if k > 100 or k < 0:
            raise ValueError("k cannot be above 100 or below 0")
        if k > 80:
            return "overbought"
        if k < 20:
            return "oversold"
        else:
            return "neutral"

class MeanReversion(Strategy):
    ''' 
    This class carries out a mean reverting trading strategy

    The input has to take in inputs of rsi, z, and bollinger
    instead of configs because strategy_params is saved as
    a model which cannot save python obects
    '''
    def __init__(self,
                 data_loader: DataLoader,
                 rsi_window : int = 14,
                 bollinger_window : int = 20,
                 z_window: int = 20,
                 rsi_oversold : int = 30,
                 rsi_overbought : int = 70,
                 z_lower: float = -2,
                 z_upper: float = 2,
                 mean_reversion_logic: str = "MAJORITY",
                 strength: float = 1,
                 **kwargs):
        super().__init__(data_loader)
        self.rsi_window = rsi_window
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.bollinger_window = bollinger_window
        self.z_window = z_window
        self.z_upper = z_upper
        self.z_lower = z_lower
        self.logic = mean_reversion_logic
        for ticker in self.tickers:
            self.prev_AG[ticker] = None
            self.prev_AL[ticker] = None
            # self.rsi[ticker] = self.calculate_rsi(ticker, period=rsi_window)

    def generate_signal(self, ticker: str):
        ''' 
        Generates signal for each ticker passed
        '''

        rsi_config = RSIConfig(window=self.rsi_window,
                                    ticker=ticker,
                                    oversold=self.rsi_oversold,
                                    overbought=self.rsi_overbought,
                                    prev_AG=self.prev_AG,
                                    prev_AL=self.prev_AL
                                    )
        bollinger_config = BollingerConfig(window=self.bollinger_window,
                                                ticker=ticker)
        z_config = ZConfig(window=self.z_window,
                                ticker=ticker,
                                lower=self.z_lower,
                                upper=self.z_upper)

        # decision is LONG/SHORT
        decision = self.obtain_market_condition(logic=self.logic,
                                                rsi_config=rsi_config,
                                                bollinger_config=bollinger_config,
                                                z_config=z_config)

        # print(f"This is the decision generated by MeanReversion {decision}\n")
        # Returns None if not buying/selling
        if decision is not None:
            signal = SignalEvent(ticker=ticker,
                                asset_type=self.data_loader.asset_type,
                                datetime=self.data_loader.get_current_datetime(),
                                signal_type=decision,
                                strength=self.strength
                                )
            # print("This is the signal generated for the mean "
            #         f"reversion strategy {signal}")
            return signal
        else: 
            return None

class MACDStrategy(Strategy):
    ''' 
    Pretty similar to moving average crossover, 
    it has two lines, computed with a longer/medium/shorter window.
    It uses exponential moving average instead of simple moving average to calculate
    Which gives greater weight to recent points
    '''
    def __init__(self,
                 data_loader,
                 strength: float = 1,
                 macd_short: int = 9,
                 macd_medium: int = 12,
                 macd_long: int = 26,
                 **kwargs):
        super().__init__(data_loader)
        self.medium_ema = {}
        self.long_ema = {}
        self.MACD = {}
        self.prev_state = {}
        self.signal = {}
        for ticker in self.tickers:
            self.medium_ema[ticker] = self.get_ema_list(window=macd_medium, ticker=ticker)
            self.long_ema[ticker] = self.get_ema_list(window=macd_long, ticker=ticker)
            self.MACD[ticker] = self.medium_ema[ticker] - self.long_ema[ticker]
            self.signal[ticker] = self.MACD[ticker].ewm(span=macd_short, adjust=False).mean()
            # print(f"This is the MACD line {self.MACD[ticker]}")
            # print(f"This is the Signal line {self.signal[ticker]}")


    def generate_signal(self, ticker: str):
        ''' 
        Generate Long signal when MACD crosses above signal line and previously 
        MACD not above signal line
        
        Genearte Short when Signal crosses above MACD line and previous Signal
        not above MACD
        
        The lines are just a pandas series of floats, their positions at
        a specific index, curr_MACD and curr_signal is just a float
        '''
        index = self.data_loader.curr_index
        curr_MACD = self.MACD[ticker][index]
        curr_signal = self.signal[ticker][index]
        # On first day, there cannot be a trade
        if index == 0:
            self.prev_state[ticker] = curr_MACD > curr_signal
            return None

        # Obtain new state to determine if crossover happened
        new_state = curr_MACD > curr_signal
        # Change in state means crossover
        # print("------MACD Strategy Generating Signal-----\n")
        # print(f"This is the previous state "
        #       f"{self.prev_state[ticker]}"
        #       " MACD line is above Signal line\n")
        # print(f"This is the new state {new_state} "
        #       "MACD line is above Signal line\n")
        if self.prev_state[ticker] != new_state:
            if new_state:
                decision = "LONG"
            else:
                decision = "SHORT"
        else:
            decision = None
        # Update the previous state to new state
        self.prev_state[ticker] = new_state
        # print(f"This is the decision: {decision}\n")

        if decision is not None:
            signal = SignalEvent(ticker=ticker,
                                asset_type=self.data_loader.asset_type,
                                datetime=self.data_loader.get_current_datetime(),
                                signal_type=decision,
                                strength=self.strength)
            # print(f"This is the signalEvent: {signal}")
            return signal
        return None

class BreakoutStrategy(Strategy):
    ''' 
    Buying/Selling when a stock price moves beyond a defined support/resistance level.
    
    Using Donchian channels for now
    '''
    def __init__(self,
                 data_loader,
                 strength = 1,
                 donchian_window: int = 20,
                 **kwargs):
        super().__init__(data_loader, strength)
        self.high = {}
        self.low = {}
        self.donchian_channels = {}
        for ticker in self.tickers:
            self.donchian_channels[ticker] = self.get_donchian_channels(window=donchian_window,
                                                                        ticker=ticker)

    def generate_signal(self, ticker: str):
        ''' 
        LONG when price breaks above resistance
	    SHORT when preice breaks below support
        '''
        # print("-----Generating Signal for Breakout Strategy----------")
        index = self.data_loader.curr_index
        resistance = self.donchian_channels[ticker]['upper'][index]
        support = self.donchian_channels[ticker]['lower'][index]
        curr_close = self.data_loader.get_current_bar_value(ticker=ticker,
                                                  value_type='close')
        if curr_close >= resistance:
            decision = "LONG"
            # print(f"This is the close price = {curr_close}\n")
            # print(f"This is the resistance price = {resistance}\n")
            # print(f"This is the decision = {decision}\n")
        elif curr_close <= support:
            decision = "SHORT"
            # print(f"This is the close price = {curr_close}\n")
            # print(f"This is the support price = {support}\n")
            # print(f"This is the decision = {decision}\n")
        else:
            # print(f"This is the close price = {curr_close}\n")
            # print(f"This is the support price = {support}\n")
            # print(f"This is the resistance price = {resistance}\n")
            # print(f"This is the decision = None\n")
            return None
        # print(f"This is the decision: {decision}")
        signal = SignalEvent(ticker=ticker,
                            asset_type=self.data_loader.asset_type,
                            datetime=self.data_loader.get_current_datetime(),
                            signal_type=decision,
                            strength=self.strength)
        # print(f"This is the signalEvent: {signal}")
        return signal

class MomentumStrategy(MACDStrategy):
    ''' 
    Momentum Strategy is a more advanced version of MACDStrategy which
    incorporates RSI and MA to determine the trend.
    
    It relies on the logic or buying high and selling hihger
    '''
    def __init__(self,
                 data_loader,
                 strength: float = 1,
                 macd_short: int = 9,
                 macd_medium: int = 12,
                 macd_long: int = 26,
                 rsi_window: int = 14,
                 **kwargs):
        super().__init__(data_loader, strength, macd_short,
                         macd_medium, macd_long)
        self.rsi_window = rsi_window
        self.ema_21 = {}
        for ticker in self.tickers:
            self.ema_21[ticker] = self.get_ema_list(window=21,
                                                    ticker=ticker)
            
    
    def generate_signal(self, ticker):
        ''' 
        Only when RSI < 70, close > 200MA, macd_decision = LONG BUY
        While if close < 200MA or macd_decision=SHORT SELL
        '''
        # index used by all three indicators
        index = self.data_loader.curr_index

        # Obtain macd_decision Copied from macd strat
        curr_macd = self.MACD[ticker][index]
        curr_signal = self.signal[ticker][index]
        # On first day, there cannot be a trade
        if index == 0:
            self.prev_state[ticker] = curr_macd > curr_signal
            return None

        # Obtain new state to determine if crossover happened
        new_state = curr_macd > curr_signal
        # Change in state means crossover
        # print(f"This is the previous state"
            #   f"{self.prev_state[ticker]}")
        # print(f"This is the new state {new_state}")
        if self.prev_state[ticker] != new_state:
            if new_state:
                macd_decision = "LONG"
            else:
                macd_decision = "SHORT"
        else:
            macd_decision = None
        # Update the previous state to new state
        self.prev_state[ticker] = new_state
        # print(f"This is the decision: {decision}")

        # Obtain ema and rsi value
        ema_value = self.ema_21[ticker][index]
        rsi_value = self.get_rsi(window=self.rsi_window,
                                 ticker=ticker)
        if None in [macd_decision, ema_value, rsi_value]:
            return None
        else:
            # Asymmetry between entry and exit is for design choise of fast to exit, slow to enter
            curr_close = self.data_loader.get_current_bar_value(ticker=ticker,
                                                                value_type='close')
            long_condition = curr_close > ema_value and rsi_value < 70 and macd_decision == "LONG"
            short_condition = (curr_close < ema_value or macd_decision == "SHORT") and rsi_value > 30
        
        if long_condition:
            decision = "LONG"
        elif short_condition:
            decision = "SHORT"
        else:
            return None
        # print("-------------Generating Signal in Momentum Strategy-------------")
        # print(f"This is the curernt close price = {curr_close}\n")
        # print(f"This is the 200 day EMA = {ema_value}\n")
        # print(f"This is the rsi value = {rsi_value}\n")
        # print(f"This is the macd decision = {macd_decision}\n")
        # print(f"This is the decision = {decision}\n")
        # print("---------------------------")
        signal = SignalEvent(ticker=ticker,
                            asset_type=self.data_loader.asset_type,
                            datetime=self.data_loader.get_current_datetime(),
                            signal_type=decision,
                            strength=self.strength)
        # print(f"This is the signalEvent: {signal}")
        return signal
        
class RateOfChangeStrategy(Strategy):
    ''' 
    ROC is a momentum strategy, measuring price acceleration
    '''
    def __init__(self, data_loader, strength = 1,
                 roc_window: int = 12,
                 **kwargs):
        super().__init__(data_loader, strength)
        self.roc_window = roc_window
        self.prev_roc = {}

    def generate_signal(self, ticker):
        ''' 
        Buy order occurs when ROC crosses negative to positive
        and close price is above 20-day SMA
        
        Exits when ROC crosses back below 0
        '''

        # print(self.data_loader.get_days_loaded())
        # roc window requires window + 1 days to be laoded to calculate
        if self.data_loader.get_days_loaded() < self.roc_window + 1:
            return None

        # roc can be calculated but no trades can occur
        if self.data_loader.get_days_loaded() == self.roc_window + 1:
            roc = self.get_roc(window=self.roc_window,
                               ticker=ticker)
            self.prev_roc[ticker] = roc
            # print(f"This is prev_roc {self.prev_roc[ticker]}")
            return None

        # Use a simple MA as a filter for false signals
        ma_20 = self.get_rolling_mean_exclusive(window=20,
                                                ticker=ticker)
        if ma_20 is None:
            return None

        # Determine buy signal
        new_roc = self.get_roc(window=self.roc_window,
                               ticker=ticker)
        
        curr_close = self.data_loader.get_current_bar_value(ticker=ticker,
                                                            value_type='close')
        filtered = curr_close > ma_20
        # print("----Generating Rate of Change signal----\n")
        # print(f"This is the prev roc = {self.prev_roc[ticker]}\n")
        # print(f"This is the new roc = {new_roc}\n")
        if self.prev_roc[ticker] < 0 and new_roc > 0 and filtered:
            decision = "LONG"
        elif self.prev_roc[ticker] > 0 and new_roc < 0:
            decision = "EXIT"
        else:
            # print("None decision generated\n")
            return None

        # print(f"This is the decision generated {decision}\n")
        # Update prev roc
        self.prev_roc[ticker] = new_roc

        # Return Signal
        signal = SignalEvent(ticker=ticker,
                            asset_type=self.data_loader.asset_type,
                            datetime=self.data_loader.get_current_datetime(),
                            signal_type=decision,
                            strength=self.strength)
        # print(f"This is the signalEvent: {signal}")
        return signal

class StochasticOscillatorStrategy(Strategy):
    ''' 
    - The stochastic oscillator is a momentum indicator that measures
    the relationship between an asset's closing price and it's high and low
    price over a window
	- It uses two lines, %K and %D, %K is the current value,
    %D is a 3-day SMA of %K for smoothing
    '''
    def __init__(self, data_loader, strength = 1, stoc_window: int = 14,
                 **kwargs):
        super().__init__(data_loader, strength)
        self.stoc_window = stoc_window
        self.k_d_list = {}
        self.prev_state = {}
        for ticker in self.tickers:
            self.k_d_list[ticker] = self.get_percent_k_d_list(window=stoc_window,
                                                              ticker=ticker)
            self.prev_state[ticker] = None
        
        
    def generate_signal(self, ticker: str):
        ''' 
        There are multiple ways of generating signals based on k and d lines,
        But the current implemntation looks at the k
        
        Then previous state was in overbought/oversold market and 
        current price crosses the threshold, long/short
        '''
        # print("-------Generating Signal for Stochastic Oscillator--------\n")
        index = self.data_loader.curr_index
        k_indicator = self.k_d_list[ticker]['k'][index]
        # print(f"This is the k_indicator {k_indicator}")

        # If the data has not been calculated yet return none
        if k_indicator is None or math.isnan(k_indicator):
            return None
        
        # First time k_signal is computed store it and don't trade
        k_signal = self.get_k_signal(k_indicator)
        if self.prev_state[ticker] is None:
            self.prev_state[ticker] = k_signal
            return None

        # If previous state is neutral signal not generated
        if self.prev_state[ticker] == "neutral":
            # print("None Signal generated\n")
            self.prev_state[ticker] = k_signal
            return None
        
        crossover = self.prev_state[ticker] != k_signal
        # print(f"This is the previous state of the market {self.prev_state}\n")
        if crossover and self.prev_state[ticker] == "overbought":
            self.prev_state[ticker] = k_signal
            decision = "SHORT"
        elif crossover and self.prev_state[ticker] == "oversold":
            self.prev_state[ticker] = k_signal
            decision = "LONG"
        else: 
            self.prev_state[ticker] = k_signal
            # print("None Signal generated\n")
            return None
        # print(f"This is the decision of the signal {decision}\n")
        signal = SignalEvent(ticker=ticker,
                            asset_type=self.data_loader.asset_type,
                            datetime=self.data_loader.get_current_datetime(),
                            signal_type=decision,
                            strength=self.strength
                            )
        # print("This is the signal generated for the Stochastic "
        #         f"Oscillator strategy {signal}")
        return signal
    
class MovingAverageCross:
    def __init__(self, data_loader: DataLoader, events: Queue,
                 tickers: list[str], mac_short_window, mac_long_window, strength: float = 1.0,
                 comission: float = 0, **kwargs):
        self.data_loader = data_loader
        self.events = events
        self.tickers = tickers
        self.short_window = mac_short_window
        self.long_window = mac_long_window
        self.strength = strength
        self.previous_signal = {ticker: None for ticker in tickers}


    def calculate_SMA(self, bars: list[Bar]) -> float:
        closes = [bar.close for bar in bars]
        return sum(closes) / len(closes)

    # @timed
    def generate_signal(self, ticker: str) -> SignalEvent:
        # print("----Moving Average Cross Generates Signal----", ticker)
        try:
            long_window_bars = self.data_loader.get_past_bars(ticker, self.long_window)
        except ValueError:
            #print(f"Not enough bars yet for {ticker}. Need {self.long_window}.")
            return None
        short_window_bars = long_window_bars[-self.short_window:]
        long_SMA = self.calculate_SMA(long_window_bars)
        short_SMA = self.calculate_SMA(short_window_bars)

        current_datetime = self.data_loader.get_current_datetime()
        if short_SMA > long_SMA:
            current_signal = "LONG"
        elif short_SMA < long_SMA:
            current_signal = "SHORT"
        else:
            current_signal = None
        
        prev_signal = self.previous_signal.get(ticker)
        # print(f"This is the previous signal, {prev_signal}\n")
        # print(f"This is the new signal, {current_signal}\n")
        if current_signal == prev_signal:
            # print("No Buy/Sell order generated\n")
            return None
        self.previous_signal[ticker] = current_signal
        if current_signal is None:
            return None
        # print(f"A {current_signal} order generated")
        return SignalEvent(
            ticker = ticker,
            datetime= current_datetime,
            signal_type= current_signal,
            strength= self.strength,
            asset_type=self.data_loader.asset_type
        )
        