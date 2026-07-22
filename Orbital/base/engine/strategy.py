from base.engine.events import SignalEvent, PairSignalEvent
from base.engine.data_loader import DataLoader, Bar
from base.engine.execution import executionLoader
from queue import Queue
import numpy as np
from collections import deque


class MovingAverageCross:
    def __init__(self, data_loader: DataLoader, events: Queue, tickers: list[str], short_window, long_window, strength: float = 1.0):
        self.data_loader = data_loader
        self.events = events
        self.tickers = tickers
        self.short_window = short_window
        self.long_window = long_window
        self.strength = strength
        
        self.previous_signal = {ticker: None for ticker in tickers}

    def get_asset_type(self):
        return self.data_loader.asset_type

    def calculate_SMA(self, bars: list[Bar]) -> float:
        closes = [bar.close for bar in bars]
        return sum(closes) / len(closes)
    
    def generate_signal(self, ticker: str) -> SignalEvent:
        #print("generating signal for ticker", ticker)
        try:
            long_window_bars = self.data_loader.get_past_bars(ticker, self.long_window)
        except ValueError:
            print(f"Not enough bars yet for {ticker}. Need {self.long_window}.")
            return None
        short_window_bars = long_window_bars[-self.short_window:]
        long_SMA = self.calculate_SMA(long_window_bars)
        short_SMA = self.calculate_SMA(short_window_bars)

        asset_type = self.get_asset_type()

        current_datetime = self.data_loader.get_current_datetime()
        if short_SMA > long_SMA:
            current_signal = "LONG"
        elif short_SMA < long_SMA:
            current_signal = "SHORT"
        else:
            current_signal = None
        
        prev_signal = self.previous_signal.get(ticker)

        if current_signal == prev_signal:
            return None
        self.previous_signal[ticker] = current_signal
        if current_signal is None:
            return None

        return SignalEvent(
            ticker = ticker,
            asset_type = asset_type,
            datetime= current_datetime,
            signal_type= current_signal,
            strength= self.strength
        )




class PairTradingStrategy:
    #Spread = Y - (alpha + beta * X)

    def __init__(
            self,
            events: Queue,
            data_loader: DataLoader,
            y_ticker: str,
            x_ticker: str,
            lookback: int = 60,
            entry_z: float = 2.0,
            exit_z: float = 0.5,
            stop_z: float = 4.0,
            strength: float = 1.0,
        ):
            if lookback < 20:
                raise ValueError("Pair-trading lookback should normally be at least 20.")

            if exit_z >= entry_z:
                raise ValueError("exit_z must be smaller than entry_z.")

            if stop_z <= entry_z:
                raise ValueError("stop_z must be greater than entry_z.")

            self.events = events
            self.data_loader = data_loader

            self.y_ticker = y_ticker
            self.x_ticker = x_ticker
            self.pair_id = f"{y_ticker}:{x_ticker}"

            self.lookback = lookback
            self.entry_z = entry_z
            self.exit_z = exit_z
            self.stop_z = stop_z
            self.strength = strength

            self.y_prices = deque(maxlen=lookback)
            self.x_prices = deque(maxlen=lookback)

            self.state = "FLAT"
            self.last_evaluated_date = None

    def estimate_spread(y_prices, x_prices):
        x_variance = np.var(x_prices, ddof=1)

        if x_variance <= 1e-12:
            raise ValueError("Cannot estimate hedge ratio: X has no variance.")

        covariance = np.cov(x_prices, y_prices, ddof=1)[0, 1]
        beta = covariance / x_variance
        alpha = np.mean(y_prices) - beta * np.mean(x_prices)

        spread = y_prices - (alpha + beta * x_prices)

        return float(alpha), float(beta), 

    def calculate_z_score(spread):
        spread_std = np.std(spread, ddof=1)

        if spread_std <= 1e-12:
            return 0.0

        return float((spread[-1] - np.mean(spread)) / spread_std)
    
    def generate_signal(
        self,
        signal_date,
        action: str,
        hedge_ratio: float,
        z_score: float,
    ):
        event = PairSignalEvent(
            pair_id=self.pair_id,
            signal_date=signal_date,
            y_ticker=self.y_ticker,
            x_ticker=self.x_ticker,
            action=action,
            hedge_ratio=hedge_ratio,
            z_score=z_score,
            strength=self.strength,
        )

        return event
    
    def calculate_signals(self, event):
        if event.type != "MARKET":
            return

        y_bar = self.data_loader.get_latest_bar(self.y_ticker)
        x_bar = self.data_loader.get_latest_bar(self.x_ticker)

        if y_bar is None or x_bar is None:
            return
        
        #must be same dates
        if y_bar.date != x_bar.date:
            return

        # A MarketEvent may be generated once per ticker. This prevents the
        # pair from being evaluated twice on the same date.
        if y_bar.date == self.last_evaluated_date:
            return

        self.last_evaluated_date = y_bar.date

        if y_bar.close <= 0 or x_bar.close <= 0:
            return

        self.y_prices.append(float(y_bar.close))
        self.x_prices.append(float(x_bar.close))

        if len(self.y_prices) < self.lookback:
            return

        y_prices = np.asarray(self.y_prices, dtype=float)
        x_prices = np.asarray(self.x_prices, dtype=float)

        try:
            _ , beta, spread = self.estimate_spread(
                y_prices=y_prices,
                x_prices=x_prices,
            )
        except ValueError:
            return

        z_score = self.calculate_z_score(spread)

        if beta <= 0:
            # Most conventional pairs should have a positive relationship.
            return

        if self.state == "FLAT":
            if z_score <= -self.entry_z:
                self.generate_signal(
                    signal_date=y_bar.date,
                    action="OPEN_LONG_SPREAD",
                    hedge_ratio=beta,
                    z_score=z_score,
                )
                self.state = "LONG_SPREAD"

            elif z_score >= self.entry_z:
                self.generate_signal(
                    signal_date=y_bar.date,
                    action="OPEN_SHORT_SPREAD",
                    hedge_ratio=beta,
                    z_score=z_score,
                )
                self.state = "SHORT_SPREAD"

        elif self.state == "LONG_SPREAD":
            mean_reverted = z_score >= -self.exit_z
            stop_triggered = z_score <= -self.stop_z

            if mean_reverted or stop_triggered:
                self.generate_signal(
                    signal_date=y_bar.date,
                    action="CLOSE_PAIR",
                    hedge_ratio=beta,
                    z_score=z_score,
                )
                self.state = "FLAT"

        elif self.state == "SHORT_SPREAD":
            mean_reverted = z_score <= self.exit_z
            stop_triggered = z_score >= self.stop_z

            if mean_reverted or stop_triggered:
                self.generate_signal(
                    signal_date=y_bar.date,
                    action="CLOSE_PAIR",
                    hedge_ratio=beta,
                    z_score=z_score,
                )
                self.state = "FLAT"