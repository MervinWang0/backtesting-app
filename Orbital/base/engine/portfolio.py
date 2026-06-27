from queue import Queue
from datetime import datetime
from decimal import Decimal

from base.engine.data_loader import DataLoader
from base.engine.events import SignalEvent, OrderEvent, FillEvent, AssetType
from base.models import (BacktestRun, PortfolioEquityRecord,
PortfolioPositionRecord, PortfolioFillRecord, Stock, BenchmarkRecord, StockPriceHistory)

def to_decimal(val) -> Decimal:
    '''
    converts a float to a decimal type
    '''
    return Decimal(str(val))


class Portfolio:
    def __init__(self, data_loader: DataLoader, events: Queue, 
                 run_name: str, strategy_name: str, start_date: datetime, end_date: datetime,
                 btr_model: BacktestRun, initial_capital: float =  100000.0, quantity =  5,):#, User = None):
        self.data_loader = data_loader
        self.events = events
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.account_currency = "USD"
        self.cash_reserves: dict[str, float] = {
            self.account_currency: initial_capital
        }
        self.fixed_quantity = quantity

        self.holdings : dict[str, float] = {
            ticker: 0 for ticker in self.data_loader.tickers
        }

        self.asset_type_by_ticker :dict[str, AssetType] = {
            ticker : getattr(self.data_loader, "asset_type", AssetType.STOCK) for ticker in self.data_loader.tickers
        }
        self.commission = 0.0
        self.total_commission = 0.0

        #store equity data for every time step
        self.equity_record: list[dict] = []
        self.avg_price: dict[str, float] = {ticker: 0.0 for ticker in self.data_loader.tickers}
        self.realised_pnl = 0.0

        #Stores what happened on each fill/trade, Date ticker direction quantity
        #fill_price commission previous_quantity new_quantity realised_pnl_day
        self.fill_record: list[dict] = []

        #Stores portfolio state for each day
        self.equity_record: list[dict] = []

        #Stores benchmark record for each day
        self.benchmark_ticker = "VOO"
        self.benchmark_quantity = None
        self.benchmark_initial_price = 0.0
        self.benchmark_record: list[dict] = []
        
        # Adds backtest run model instance as attribute
        self.btr_model = btr_model

        #creates database for this backtest run when portfolio is intialised
        #  I did this creation in backtest
        # self.backtest_run = BacktestRun.objects.create(
        #     #user = User,
        #     run_name = run_name,
        #     strategy_name= strategy_name,
        #     start_date = start_date,
        #     end_date = end_date,
        #     initial_capital = to_decimal(self.initial_capital),
        #     end_equity = to_decimal(self.initial_capital),
        #     fixed_quantity = self.fixed_quantity,
        #     tickers = list(self.data_loader.tickers),
        # )

    def complete_bt(self) -> None:
        BacktestRun.objects.filter(BacktestRun = self.backtest_run).update(
            is_completed = True,
            completed_at = self.data_loader.get_current_datetime()
        )

    def add_cash(self, amount: float, currency: str) -> None:
        if currency not in self.cash_reserves:
            self.cash_reserves[currency] = 0.0
        self.cash_reserves[currency] += amount
        self.current_capital = self.cash_reserves.get(self.account_currency, 0.0)
    
    def convert_currency(self, amount: float, from_currency: str, to_currency: str) -> float:
        '''
        Example:
        Direct conversion: USD -> EUR using USDEUR price
        Inverse conversion: EUR -> USD using USDEUR price by taking reciprocal
        '''
        direct_conversion = f"{from_currency}{to_currency}=X"
        inverse_conversion = f"{to_currency}{from_currency}=X"

        try: 
            direct_price = self.data_loader.get_current_bar_value(direct_conversion, "close")
            return amount * direct_price
        except KeyError:
            pass

        try:
            inverse_price = self.data_loader.get_current_bar_value(inverse_conversion, "close")
            return amount / inverse_price
        except KeyError:
            pass

        raise ValueError(f"No exchange rate data available for {from_currency} to {to_currency} conversion.")

    def convert_to_account_currency(self, amount: float, currency: str) -> float:
        if currency == self.account_currency:
            return amount
        return self.convert_currency(amount, from_currency=currency, to_currency=self.account_currency)   

    def calculate_cash_value(self) -> float:
        '''
        converts all cash balance into account currency
        ''' 
        cash_value= 0.0
        for curreny, amount in self.cash_reserves.items():
            cash_value += self.convert_to_account_currency(amount, curreny)
        return cash_value




    def get_latest_price(self, ticker: str) -> float:
        curr_date = self.data_loader.get_current_datetime()
        return self.data_loader.bar_lookup[ticker][curr_date].close

    def calculate_unrealised_pnl(self) -> float:
        total_unrealised_pnl = 0.0
        for ticker in self.holdings:
            total_unrealised_pnl += self.calculate_unrealised_pnl_ticker(ticker)
        return total_unrealised_pnl

    def calculate_unrealised_pnl_ticker(self, ticker: str) -> float:
        curr_quantity = self.holdings[ticker]

        if curr_quantity == 0:
            return 0.0

        current_price = self.get_latest_price(ticker)
        avg_price = self.avg_price[ticker]
        if curr_quantity > 0:
            return curr_quantity * (current_price - avg_price)
        else:
            #short position
            return abs(curr_quantity) * (avg_price - current_price)

    def calculate_holdings_value(self) -> float:
        total_value = 0.0
        for ticker, quantity in self.holdings.items():
            price = self.data_loader.bar_lookup[ticker][self.data_loader.curr_datetime].close
            total_value += quantity * price
        return total_value

    def generate_order(self, signal: SignalEvent) -> OrderEvent:
        ticker = signal.ticker
        signal_type = signal.signal_type
        stock_quantity = self.holdings[ticker]
        order_quantity = self.fixed_quantity * signal.strength

        if order_quantity <= 0:
            raise ValueError(f"Invalid order quantity {order_quantity} "
                             f"generated from signal strength {signal.strength}. "
                             f"Order quantity must be positive.")

        if signal_type == 'LONG':
            return self.generate_long_order(ticker, stock_quantity, order_quantity, signal.datetime)

        elif signal_type == 'SHORT':
            return self.generate_short_order(ticker, stock_quantity, order_quantity,signal.datetime)

        elif signal_type == 'EXIT':
            return self.generate_exit_order(ticker, stock_quantity,
                                            exit_frac=signal.strength, dt=signal.datetime)

        else:
            raise ValueError(f"Invalid signal type {signal_type} in signal event."
                             f" Expected 'LONG', 'SHORT', or 'EXIT'.")

    def generate_long_order(self, ticker: str, stock_quantity: int,
                            order_quantity: int, dt: datetime) -> OrderEvent:
        if stock_quantity >= 0:
            #If current position is flat or long, buy more
            buy_quantity = order_quantity
        else:
            #If current position is short,
            #buy to cover existing short position and open a new long position
            buy_quantity = abs(stock_quantity) + order_quantity
        return OrderEvent(
            ticker = ticker,
            datetime = dt,
            order_type = "MKT",
            quantity = buy_quantity,
            direction = "BUY"
        )

    def generate_short_order(self, ticker: str, stock_quantity: int,
                             order_quantity: int, dt: datetime) -> OrderEvent:
        if stock_quantity <= 0:
            #If current position is flat or short, sell more
            sell_quantity = order_quantity
        else:
            #If current position is long, sell to reduce the existing long position
            sell_quantity = stock_quantity + order_quantity
        return OrderEvent(
            ticker = ticker,
            datetime = dt,
            order_type = "MKT",
            quantity = sell_quantity,
            direction = "SELL"
        )

    def generate_exit_order(self, ticker: str, stock_quantity: int,
                            exit_frac: float, dt: datetime) -> OrderEvent:
        if stock_quantity == 0:
            raise ValueError(f"No existing position in {ticker} to exit.")
        if exit_frac < 0 or exit_frac > 1:
            raise ValueError(f"Invalid exit fraction {exit_frac}. Must be between 0 and 1.")
        buy_or_sell_quantity = abs(stock_quantity) * exit_frac

        if stock_quantity > 0:
            direction = "SELL"
        else:
            direction = "BUY"

        return OrderEvent(
            ticker = ticker,
            datetime = dt,
            order_type = "MKT",
            quantity = buy_or_sell_quantity,
            direction = direction
        )


    def update_fill(self, event: FillEvent) -> None:
        if event.type != "FILL":
            raise ValueError(f"Invalid event type {event.type} in fill update. Expected 'FILL'.")

        ticker = event.ticker

        curr_quantity = self.holdings.get(ticker, 0)
        trade_quantity = event.quantity if event.direction == "BUY" else -event.quantity
        new_quantity = curr_quantity + trade_quantity

        realised_pnl_day = self.update_position_tracker(
                                ticker,
                                curr_quantity,
                                trade_quantity,
                                event.fill_cost,
                                event.commission
        )

        self.update_cash(event)

        self.holdings[ticker] = new_quantity
        self.realised_pnl += realised_pnl_day

        self.update_fill_records(event,
                            curr_quantity,
                            new_quantity,
                            realised_pnl_day= realised_pnl_day)

    def update_cash(self, fill: FillEvent) -> None:
        fill_cost = fill.quantity * fill.fill_cost
        if fill.direction == "BUY":
            self.current_capital -= fill_cost + fill.commission
        elif fill.direction == "SELL":
            self.current_capital += fill_cost - fill.commission
        else:
            raise ValueError(f"Invalid fill direction {fill.direction} "
                             f"in cash update. Expected 'BUY' or 'SELL'.")
        self.total_commission += fill.commission

    #Updates average price and realized PnL for the ticker based on the new fill
    #Note: Returns -commission as a negative cost to the trade
    def update_position_tracker(self, ticker: str, curr_quantity: float,
                                fill_quantity: float, fill_price: float,
                                commission: float) -> float:
        curr_avg_price = self.avg_price.get(ticker, 0.0)
        new_quantity = curr_quantity + fill_quantity

        #No existing position, so open a new position
        if curr_quantity == 0:
            self.avg_price[ticker] = fill_price 
            return -commission

        #Same direction trade: Long add more to long, short add more to short
        if curr_quantity * fill_quantity > 0:
            old_position_value = abs(curr_quantity) * curr_avg_price
            additional_position_value = abs(fill_quantity) * fill_price
            self.avg_price[ticker] = ((old_position_value + additional_position_value)
                                      / abs(new_quantity))
            return -commission

        #Opposite direction trade: reducing, exiting or position reversal
        closing_quantity = min(abs(curr_quantity), abs(fill_quantity))
        if curr_quantity > 0:
            #Close long position by selling
            realised_pnl_day = closing_quantity * (fill_price - curr_avg_price)
        else:
            #Close short position by buying
            realised_pnl_day = closing_quantity * (curr_avg_price - fill_price)

        realised_pnl_day -= commission

        #position fully closed
        if new_quantity == 0:
            self.avg_price[ticker] = 0.0

        #Position reduced but not closed and not reversed
        elif curr_quantity * new_quantity > 0:
            self.avg_price[ticker] = curr_avg_price

        #Position reversed
        else:
            self.avg_price[ticker] = fill_price

        return realised_pnl_day

    def update_fill_records(self, fill: FillEvent, prev_quantity: float,
                            new_quantity: float, realised_pnl_day: float) -> None:
        record = {
                "date": fill.datetime,
                "ticker": fill.ticker,
                "quantity": fill.quantity,
                "fill_price": fill.fill_cost,
                "direction": fill.direction,
                "commission": fill.commission,
                "previous_quantity": prev_quantity,
                "new_quantity": new_quantity,
                "realised_pnl_day": realised_pnl_day,
            }
        # print(record)
        self.fill_record.append(record)
        # stock = Stock.objects.filter(ticker = fill.ticker).first()

        # PortfolioFillRecord.objects.create(
        #     backtest_run = self.backtest_run,
        #     date = fill.datetime,
        #     ticker = fill.ticker,
        #     quantity = to_decimal(fill.quantity),
        #     fill_price = to_decimal(fill.fill_cost),
        #     direction = fill.direction,
        #     commission = to_decimal(self.commission),
        #     previous_quantity = to_decimal(prev_quantity),
        #     new_quantity = to_decimal(new_quantity),
        #     realised_pnl_day = to_decimal(realised_pnl_day),
        # )


    #Updates equity record for each day, should be called whenever .next_day() is called
    def update_equity_record(self) -> None:
        date = self.data_loader.get_current_datetime()

        holdings_value = self.calculate_holdings_value()
        unrealised_pnl = self.calculate_unrealised_pnl()
        total_equity = self.current_capital + holdings_value

        #calculates all investments long + short
        gross_exposure = sum(abs(self.holdings[ticker] * self.get_latest_price(ticker))
                            for ticker in self.holdings)

        #calculates long - short investments
        net_exposure = sum(self.holdings[ticker] * self.get_latest_price(ticker)
                            for ticker in self.holdings)

        #Higher ratio = more risk, lower ratio = less risk
        gross_exposure_leverage = gross_exposure / total_equity if total_equity != 0 else 0.0

        record = {
                "date": date,
                "cash": self.current_capital,
                "holdings_value": holdings_value,
                "equity": total_equity,
                "realised_pnl" : self.realised_pnl,
                "unrealised_pnl": unrealised_pnl,
                "total_commission" : self.total_commission,
                "gross_exposure": gross_exposure,
                "net_exposure" : net_exposure,
                "gross_exposure_leverage" : gross_exposure_leverage
            }

        self.equity_record.append(record)

        # PortfolioEquityRecord.objects.update_or_create(
        #     backtest_run = self.backtest_run,
        #     date = date,
        #     defaults = {
        #         "cash": to_decimal(self.current_capital),  
        #         "holdings_value": to_decimal(holdings_value),
        #         "equity": to_decimal(total_equity),
        #         "realised_pnl": to_decimal(self.realised_pnl),
        #         "unrealised_pnl": to_decimal(unrealised_pnl),
        #         "total_commission": to_decimal(self.total_commission),
        #         "gross_exposure": to_decimal(gross_exposure),
        #         "net_exposure": to_decimal(net_exposure),
        #         "gross_exposure_leverage": to_decimal(gross_exposure_leverage),
        #     }
        # )

        # for ticker, quantity in self.holdings.items():
        #     market_price = self.get_latest_price(ticker)
        #     market_value = market_price * quantity
        #     unrealised_pnl = self.calculate_unrealised_pnl_ticker(ticker)

        #     stock = Stock.objects.filter(ticker=ticker).first()

        #     PortfolioPositionRecord.objects.update_or_create(
        #         backtest_run = self.backtest_run,
        #         date = date,
        #         ticker = ticker,
        #         defaults = {
        #             "stock": stock,
        #             "quantity": to_decimal(quantity),
        #             "avg_price": to_decimal(self.avg_price[ticker]),
        #             "market_price": to_decimal(market_price),
        #             "market_value": to_decimal(market_value),
        #             "unrealised_pnl": to_decimal(unrealised_pnl),
        #         }
        #     )

    def get_fill_records(self):
        return self.fill_record

    def get_equity_records(self):
        return self.equity_record
    
    def update_benchmark_record(self) -> None:
        date = self.data_loader.get_current_datetime()
        benchmark_price = (StockPriceHistory.objects.filter(stock__ticker=self.benchmark_ticker, date__lte=date).order_by("-date").first()).close_price
        if benchmark_price is None:
            raise ValueError(f"No price data available for benchmark ticker {self.benchmark_ticker} on date {date}.")
        if self.benchmark_quantity is None:
            self.benchmark_initial_price = benchmark_price
            self.benchmark_quantity = to_decimal(self.initial_capital) / to_decimal(self.benchmark_initial_price)
        benchmark_unrealised_pnl = self.benchmark_quantity * (benchmark_price - self.benchmark_initial_price)
        market_value = self.benchmark_quantity * benchmark_price
        BenchmarkRecord.objects.update_or_create(
            backtest_run = self.btr_model,
            date = date,
            defaults = {
                "ticker": self.benchmark_ticker,
                "close_price": to_decimal(benchmark_price),
                "quantity": to_decimal(self.benchmark_quantity),
                "market_value": to_decimal(market_value),
                "unrealised_pnl": to_decimal(benchmark_unrealised_pnl),
            }
        )
        #print(f"Updated benchmark record for {self.benchmark_ticker} on {date}: price {benchmark_price}, quantity {self.benchmark_quantity}, market value {market_value}, unrealised PnL {benchmark_unrealised_pnl}")

