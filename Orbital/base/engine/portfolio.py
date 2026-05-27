from math import floor
import pandas as pd
from base.engine import events
from base.engine.data_loader import DataLoader

class Portfolio:
    '''
    Features
    1. Default position sizing of 10%, each trade can use at most 10% of capital float of [0, 1]
    2. Generate order event from signal event (simple version for prototype)
    3. Update portfolio after fill event (updates holdings and equity)
    4. Tracks trading history (tracks)

    More advanced features
    1. risk factors 
    2. dynamic position sizing
    3. starting with holdings (currently assumes no holdings)

    Attributes
    1. data loader => the same data loader obj as initiated in Backtester
    2. current_holdings: dict{str: quantity} => stocks held at current day
    3. all_holdings: dict{datetime.date: dict{str: int}} => historical stocks held per day
    4. current_equity: float => cash + value of holidings at current day
    5. all_equity: dict{datetime.date: float} => histoical equity per day info
    6. cash: float => amt money the portfolio has on any day
    7. POSITION_SIZING: float => constant representing fixed max cash spent per trade
    8. trade_log: list[dict{}] => each element is a dict, makes it easy for conversion to dataframe

    Methods
    1. init
    2. update_from_fill
    3. generate_order
    4. update_trade_log (This is actually inside update_from_fill, more specifically
        inside construct current holdings. I should probably change this.)
    5. get_initial_capital
    6. get_risk_free_rate

    Notes
    1. Due to current holding's implementation,
    current being the start of a day before trading occurs,
    current holding of nth day = current holding of n-1th day combined with fill event of n-1th day.
    2. Potfolio does not contain a datetime because it is only initialized once
    '''
    def __init__(self, initial_capital: float, data_loader: DataLoader):
        self.data_loader = data_loader
        # initialize current holdings as {ticker: 0} for all tickers
        self.current_holdings = {ticker : 0 for ticker in self.data_loader.get_tickers()}
        # all holding is initialized with the first day's holdings
        self.all_holdings = {data_loader.get_current_date(): self.current_holdings.copy()}
        self.current_equity = initial_capital
        # all equity is initialized with first day's equity
        self.all_equity = {data_loader.get_current_date(): initial_capital}
        self.cash = initial_capital
        self.POSITION_SIZING = 0.1 # by default each trade uses a max of 10% cash
        self.trade_log = []

    def generate_order(self, signal: events.SignalEvent) -> events.OrderEvent:
        '''
        This function represents how the portfolio takes in a signal and generates an order.
        It currently only supports long-selling
        '''
        return events.OrderEvent(
            ticker=signal.ticker,
            datetime=signal.datetime,
            order_type="MKT",
            quantity=self.get_quantity(signal),
            direction=self.get_direction(signal)
        )

    def update_from_fill(self, fill: events.FillEvent) -> None:
        '''
        Description
        This function represents how the portfolio takes in a fill and updates its attributes
        '''
        current_date = self.data_loader.get_current_date()
        self.construct_current_holdings(fill)
        # all holdings {date = current_holdings}
        self.all_holdings[current_date] = self.current_holdings.copy()
        self.construct_current_equity()
        self.all_equity[current_date] = self.current_equity

    def history(self):
        '''
        Turns the trade log, a list of dictionaries to a trade_records_df, two columns date, pnl
        '''
        print(f"{self.trade_log}")
        return pd.DataFrame(self.trade_log)

    # The below are helper functions
    def construct_current_holdings(self, fill: events.FillEvent) -> None:
        '''
        Description
        1. maps self.current_holdings to nth day's holding before trading
        2. updates cash
        3. Tracks pnl to use to form trade_log
        4. updates trade_log
        Note
        1. This means before the function updates self.current_holding,
        current_holding refers to the previous day
        2. prev_holding combined with fill quantity = new current holdings
        3. This implementation of pnl simply looks at change in capital per trade
        '''
        # pnl tracking
        original_cash = self.cash
        # prev_holding is added here to make it clearer
        prev_holding = self.current_holdings
        if fill.direction == "BUY":
            # only has to update 1 entry in current holdings, bc only 1 stock traded
            self.current_holdings[fill.ticker] = prev_holding[fill.ticker] + fill.quantity
            # cash is reduced by quanttiy * unit price of stock and  comission
            self.cash -= ((fill.quantity * fill.fill_cost) + fill.commission)
        elif fill.direction == "SELL":
            self.current_holdings = prev_holding[fill.ticker] - fill.quantity
            self.cash += ((fill.quantity * fill.fill_cost) - fill.commission)
        pnl = self.cash - original_cash
        self.update_trade_log(pnl=pnl, fill=fill)

        #Error testing
        print(f"{self.trade_log}")

    def construct_current_equity(self) -> None:
        '''
        Description
        To get current equity add value of current holdings + capital
        '''
        current_holdings_value = 0
        for ticker in self.current_holdings:
            # add to current holdings, quantity * price per quantity
            current_holdings_value += (self.current_holdings[ticker] *
            self.data_loader.get_current_bar_value(ticker, "close"))
        self.current_equity = float(self.cash) + float(current_holdings_value) 
        # Handling float decimal.Decimal error

    def create_equity_curve(self)-> pd.DataFrame:
        '''
        Creates a pandas dataframe using all_holdings to represent an equity curve.
        Normalized using initial capital to be based on percentage
        '''

    def get_direction(self,signal: events.SignalEvent) -> events.DirectionType:
        '''
        This function is part of generate_order. It gets the direction. 
        '''
        if signal.signal_type == "LONG":
            return "BUY"
        if signal.signal_type == "SHORT":
            return "SELL"
        if signal.signal_type == "EXIT" and self.current_holdings[signal.ticker] >= 0:
            return "SELL"
        if signal.signal_type == "EXIT" and self.current_holdings[signal.ticker] < 0:
            return "BUY"
        raise ValueError("The signal type must be of LONG/SHORT/EXIT")

    def get_quantity(self, signal: events.SignalEvent) -> int:
        '''
        Description
        This function is part of generate_order. It gets the quantity.

        Note
        that if direction = "EXIT" signal strength does not matter.
        '''
        # If exit, quantity is the magnitude of the position offset
        # position offset is difference from current holding of a stock to 0
        if signal.signal_type == "EXIT":
            return abs(self.current_holdings[signal.ticker])

        # direction is needed because quantity differs for buy and sell
        direction = self.get_direction(signal)
        if direction == "BUY":
            # quantity = floor(money / unit price stock)
            allocated_capital = self.POSITION_SIZING * self.cash
            money = allocated_capital * signal.strength
            unit_price_stock = self.data_loader.get_current_bar_value(signal.ticker, "close")
            return floor(money / float(unit_price_stock)) # unit_price_stock is decimal.Decimal
            # causing an unsupported operand error

        if direction == "SELL":
            # quantity sold is just amount of stocks owned * strength
            return floor(self.current_holdings[signal.ticker] * signal.strength)

        raise ValueError("The direction should be either BUY or SELL")

    def update_trade_log(self, pnl: float, fill: events.FillEvent) -> None:
        self.trade_log.append({"pnl": pnl, "date": fill.datetime})