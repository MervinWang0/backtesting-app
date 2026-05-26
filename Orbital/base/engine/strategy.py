from base.engine.events import SignalEvent
from base.engine.data_loader import DataLoader, Bar
from base.engine.execution import executionLoader
from queue import Queue


class MovingAverageCross:
    def __init__(self, data_loader: DataLoader, events: Queue, tickers: list[str], short_window, long_window, strength: float = 1.0):
        self.data_loader = data_loader
        self.events = events
        self.tickers = tickers
        self.short_window = short_window
        self.long_window = long_window
        self.strength = strength

    def calculate_SMA(self, bars: list[Bar]) -> float:
        closes = [bar.Close for bar in bars]
        return sum(closes) / len(closes)
    
    def generate_signal(self, ticker: str) -> SignalEvent:
        print("generating signal for ticker", ticker)
        try:
            long_window_bars = self.data_loader.get_latest_bars(ticker, self.long_window)
        except ValueError:
            print(f"Not enough bars yet for {ticker}. Need {self.long_window}.")
            return None
        short_window_bars = long_window_bars[-self.short_window:]
        long_SMA = self.calculate_SMA(long_window_bars)
        short_SMA = self.calculate_SMA(short_window_bars)

        current_datetime = self.data_loader.get_current_datetime()
        death_cross = short_SMA < long_SMA
        golden_cross = short_SMA > long_SMA

        if death_cross:
            print("now is death cross")
            return SignalEvent(
                ticker = ticker,
                datetime = current_datetime,
                signal_type = "SHORT",
                strength = self.strength
            )
        elif golden_cross:
            print("now is golden cross")
            return SignalEvent(
                ticker = ticker,
                datetime = current_datetime,
                signal_type = "LONG",
                strength = self.strength
            )
        else:
            return None