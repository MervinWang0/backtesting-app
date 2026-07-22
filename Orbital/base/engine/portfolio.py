import math
from base.engine.data_loader import DataLoader
from decimal import Decimal
from datetime import datetime
from base.engine.events import AssetType, SignalEvent, OrderEvent, FillEvent
from queue import Queue
from base.models import BacktestRun, BenchmarkRecord, PortfolioEquityRecord, PortfolioPositionRecord, PortfolioFillRecord, Stock, StockPriceHistory, ForexPair, ForexPriceHistory, FuturesContract, FuturesPriceHistory


def to_decimal(val) -> Decimal:
    return Decimal(str(val))


class Portfolio:
    def __init__(self, data_loader: DataLoader,
                 events: Queue, 
                 run_name: str, 
                 strategy_name: str, 
                 start_date: datetime, 
                 end_date: datetime,
                 initial_capital: float =  100000.0, 
                 quantity =  5, 
                 current_equity : Decimal = 0.0, 
                 asset_cache: dict = None, 
                 benchmark_prices: dict = None,
                risk_per_trade: float = 0.01,
                max_position_pct: float = 0.20,
                max_gross_leverage: float = 1.0,
                default_stop_pct: float = 0.02,
                forex_lot_size: int = 1000,):#, User = None):
        self.data_loader = data_loader
        self.events = events
        self.initial_capital = initial_capital
        self.account_currency = "USD"
        self.cash_reserves: dict[str, float] = {
            self.account_currency: initial_capital
        }
        self.current_capital = initial_capital
        self.current_equity = current_equity

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
        #self.equity_record: list[dict] = []
        self.avg_price: dict[str, float] = {ticker: 0.0 for ticker in self.data_loader.tickers}
        self.realised_pnl = 0.0

        #Stores what happened on each fill/trade, Date ticker direction quantity fill_price commission previous_quantity new_quantity realised_pnl_day
        self.fill_record: list[dict] = []

        #Stores portfolio state for each day
        self.equity_record = {}
        self.position_records = {}
        self.benchmark_records = {}
        
        self.asset_cache: dict[str, object] = asset_cache
        self.benchmark_prices: dict[str , float] = benchmark_prices


        #Stores benchmark record for each day
        self.benchmark_ticker = "VOO"
        self.benchmark_quantity = None
        self.benchmark_initial_price = 0.0

        #Position sizing
        self.risk_per_trade = risk_per_trade
        self.max_position_pct = max_position_pct
        self.max_gross_leverage = max_gross_leverage
        self.default_stop_pct = default_stop_pct
        self.forex_lot_size = forex_lot_size


        #creates database for this backtest run when portfolio is intialised 
        # self.backtest_run = BacktestRun.objects.create(
        #     #user = User,
        #     run_name = run_name,
        #     strategy_name= strategy_name,
        #     asset_type = getattr(self.data_loader, "asset_type", AssetType.STOCK),
        #     start_date = start_date,
        #     end_date = end_date,
        #     initial_capital = to_decimal(self.initial_capital),
        #     end_equity = to_decimal(self.initial_capital),
        #     fixed_quantity = self.fixed_quantity,
        #     tickers = list(self.data_loader.tickers),
        # )

        # self._load_caches()


    # def _load_caches(self) -> None:
    #     for ticker in self.data_loader.tickers:
    #         asset_type = self.asset_type_by_ticker.get(ticker)
    #         if asset_type == AssetType.STOCK:
    #             self.asset_cache[ticker] = Stock.objects.filter(ticker=ticker).first()
    #         elif asset_type == AssetType.FOREX:
    #             self.asset_cache[ticker] = ForexPair.objects.filter(ticker=ticker).first()
    #         elif asset_type == AssetType.FUTURES:
    #             self.asset_cache[ticker] = FuturesContract.objects.filter(contract_code=ticker).first()
            
    #         benchmark = StockPriceHistory.objects.filter(stock__ticker=self.benchmark_ticker, date__gte=self.backtest_run.start_date, date__lte=self.backtest_run.end_date)

    #         for record in benchmark:
    #             self.benchmark_prices[record.date] = float(record.close_price)
    
    def complete_bt(self, backtest_run : BacktestRun) -> None:
        PortfolioEquityRecord.objects.filter(backtest_run=backtest_run).delete()
        PortfolioPositionRecord.objects.filter(backtest_run=backtest_run).delete()
        PortfolioFillRecord.objects.filter(backtest_run=backtest_run).delete()
        BenchmarkRecord.objects.filter(backtest_run=backtest_run).delete()
        
        equity_records = list(self.equity_record.values())
        position_records = list(self.position_records.values())
        benchmark_records = list(self.benchmark_records.values())

        print(f"Saving {len(self.fill_record)} fill records to database")
        fill_obj = [
            PortfolioFillRecord(
                backtest_run = backtest_run,
                date = record["date"],
                ticker = record["ticker"],
                source_contract_code = record["source_contract_code"],
                quantity = to_decimal(record["quantity"]),
                fill_price = to_decimal(record["fill_price"]),
                direction = record["direction"],
                commission = to_decimal(record["commission"]),
                previous_quantity = to_decimal(record["previous_quantity"]),
                new_quantity = to_decimal(record["new_quantity"]),
                realised_pnl_day = to_decimal(record["realised_pnl_day"]),
            ) for record in self.fill_record
        ]
        PortfolioFillRecord.objects.bulk_create(fill_obj, batch_size=1000)

        print(f"Saving {len(self.equity_record)} equity records to database")
        equity_obj = [
            PortfolioEquityRecord(
                backtest_run = backtest_run,
                date = record["date"],
                cash = to_decimal(record["cash"]),
                holdings_value = to_decimal(record["holdings_value"]),
                equity = to_decimal(record["equity"]),
                realised_pnl = to_decimal(record["realised_pnl"]),
                unrealised_pnl = to_decimal(record["unrealised_pnl"]),
                total_commission = to_decimal(record["total_commission"]),
                gross_exposure = to_decimal(record["gross_exposure"]),
                net_exposure = to_decimal(record["net_exposure"]),
                gross_exposure_leverage = to_decimal(record["gross_exposure_leverage"]),
            ) for record in equity_records
        ]
        PortfolioEquityRecord.objects.bulk_create(equity_obj, batch_size=1000)

        print(f"Saving {len(self.position_records)} position records to database")
        position_obj = [
            PortfolioPositionRecord(
                backtest_run = backtest_run,
                date = record["date"],
                ticker = record["ticker"],
                stock = record["stock"],
                forex = record["forex"],
                future = record["future"],
                quantity = to_decimal(record["quantity"]),
                avg_price = to_decimal(record["avg_price"]),
                market_price = to_decimal(record["market_price"]),
                market_value = to_decimal(record["market_value"]),
                unrealised_pnl = to_decimal(record["unrealised_pnl"]),
                multiplier = to_decimal(record["multiplier"]),
            ) for record in position_records
        ]
        PortfolioPositionRecord.objects.bulk_create(position_obj, batch_size=1000)

        print(f"Saving{len(self.benchmark_records)} benchmark records to database")
        benchmark_obj = [
            BenchmarkRecord(
                backtest_run = backtest_run,
                date = record["date"],
                ticker= record["ticker"],
                close_price = to_decimal(record["close_price"]),
                quantity = to_decimal(record["quantity"]),
                market_value = to_decimal(record["market_value"]),
                unrealised_pnl = to_decimal(record["unrealised_pnl"]),
            ) for record in benchmark_records
        ]
        BenchmarkRecord.objects.bulk_create(benchmark_obj, batch_size = 1000)

        backtest_run.is_completed = True
        backtest_run.completed_at = self.data_loader.get_current_datetime()
        backtest_run.end_equity = to_decimal(self.current_equity)
        backtest_run.save(update_fields=["is_completed", "completed_at", "end_equity"])

        print("Database save completed")
    

    def get_unit_exposure(self, ticker:str, price:float):
        asset_type = self.asset_type_by_ticker.get(ticker)

        if asset_type == AssetType.FUTURES:
            multiplier = float(self.get_contract_multiplier(ticker))
            return price * multiplier

        if asset_type == AssetType.FOREX:
            bar = self.data_loader.get_current_bar(ticker)

            if bar is None:
                raise ValueError(
                    f"No current forex bar available for {ticker}."
                )

            return self.convert_to_account_currency(
                price,
                bar.quote_currency,
            )

        return price
    
    def calculate_gross_exposure_excluding(
        self,
        excluded_ticker: str,):

        gross_exposure = 0.0

        for ticker, quantity in self.holdings.items():
            if ticker == excluded_ticker or quantity == 0:
                continue

            price = float(self.get_latest_price(ticker))
            unit_exposure = self.get_unit_exposure(ticker, price)

            gross_exposure += abs(quantity) * unit_exposure

        return gross_exposure
    
    #Calculate how much account-currency PnL is lose per unit if stop is reached
    def calculate_unit_risk(self, ticker: str, stop_distance: float,):
        asset_type = self.asset_type_by_ticker.get(ticker)

        if asset_type == AssetType.FUTURES:
            multiplier = float(self.get_contract_multiplier(ticker))
            return stop_distance * multiplier

        if asset_type == AssetType.FOREX:
            bar = self.data_loader.get_current_bar(ticker)

            if bar is None:
                raise ValueError(
                    f"No current forex bar available for {ticker}."
                )

            return self.convert_to_account_currency(
                stop_distance, 
                bar.quote_currency,
            )

        return stop_distance
    
    def calculate_target_quantity(self, signal: SignalEvent):
        ticker = signal.ticker
        current_price = float(self.get_latest_price(ticker))

        equity = float(self.end_equity())

        if equity <= 0:
            return 0.0

        confidence = max(0.0, min(float(signal.strength), 1.0))

        if confidence == 0:
            return 0.0

        stop_price = getattr(signal, "stop_price", None)

        if stop_price is not None:
            stop_price = float(stop_price)

            if signal.signal_type == "LONG" and stop_price >= current_price:
                raise ValueError(
                    f"LONG stop price {stop_price} must be below "
                    f"current price {current_price}."
                )

            if signal.signal_type == "SHORT" and stop_price <= current_price:
                raise ValueError(
                    f"SHORT stop price {stop_price} must be above "
                    f"current price {current_price}."
                )

            stop_distance = abs(current_price - stop_price)

        else:
            # Fall back to a percentage stop when the strategy does not provide a specific stop
            stop_distance = current_price * self.default_stop_pct

        if stop_distance <= 0:
            return 0.0

        #for example 100,000 equity * 1% risk * 80% confidence = $800 risk.
        risk_budget = equity * self.risk_per_trade * confidence

        unit_risk = self.calculate_unit_risk(
            ticker=ticker,
            stop_distance=stop_distance,
        )

        if unit_risk <= 0:
            return 0.0

        quantity_by_risk = risk_budget / unit_risk

        # Limit exposure for one ticker.
        unit_exposure = self.get_unit_exposure(
            ticker=ticker,
            price=current_price,
        )

        if unit_exposure <= 0:
            return 0.0

        maximum_ticker_exposure = equity * self.max_position_pct
        quantity_by_ticker_limit = (maximum_ticker_exposure / unit_exposure)

        # Limit total portfolio exposure.
        existing_other_exposure = (self.calculate_gross_exposure_excluding(ticker))

        maximum_portfolio_exposure = (equity * self.max_gross_leverage)

        available_portfolio_exposure = max(0.0,maximum_portfolio_exposure - existing_other_exposure)

        quantity_by_portfolio_limit = (available_portfolio_exposure / unit_exposure)

        target_quantity = min(
            quantity_by_risk,
            quantity_by_ticker_limit,
            quantity_by_portfolio_limit,
        )

        return target_quantity

    def get_contract_multiplier(self, ticker: str) -> float:
        bar = self.data_loader.get_current_bar(ticker)
        if bar is None:
            raise ValueError(f"No price data available for {ticker}")
        return bar.contract_multiplier if bar.contract_multiplier is not None else 1.0

    def get_source_contract_code(self, ticker: str) -> str:
        bar = self.data_loader.get_current_bar(ticker)
        if bar is None:
            raise ValueError(f"No price data available for {ticker}")
        return bar.source_contract_code
    
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
            asset_type = self.asset_type_by_ticker.get(ticker)
            if asset_type == AssetType.FUTURES:
                continue
            total_unrealised_pnl += self.calculate_unrealised_pnl_ticker(ticker)
        return total_unrealised_pnl
    
    def calculate_unrealised_pnl_ticker(self, ticker: str) -> float:
        curr_quantity = self.holdings[ticker]

        if curr_quantity == 0:
            return 0.0
        
        current_price = self.get_latest_price(ticker)
        avg_price = self.avg_price[ticker]
        multiplier = self.get_contract_multiplier(ticker) if self.asset_type_by_ticker.get(ticker) == AssetType.FUTURES else 1.0

        if curr_quantity > 0:
            pnl = curr_quantity * (current_price - avg_price) * multiplier
        else:
            #short position
            pnl = abs(curr_quantity) * (avg_price - current_price) * multiplier
        
        asset_type = self.asset_type_by_ticker.get(ticker)
        if asset_type == AssetType.FOREX:
            bar = self.data_loader.get_current_bar(ticker)
            if bar is None:
                raise ValueError(f"No price data available for ticker {ticker} at the time of unrealised PnL calculation.")
            #For forex, unrealised PnL is converted to account currency using the current exchange rate
            return self.convert_to_account_currency(pnl, bar.quote_currency)
        
        return pnl

    def calculate_futures_unrealised_pnl(self, ticker: str) -> float:
        quantity = self.holdings.get(ticker, 0)
        if quantity == 0:
            return 0.0
        curr_price = float(self.get_latest_price(ticker))
        avg_price = float(self.avg_price.get(ticker, 0.0))
        bar = self.data_loader.get_current_bar(ticker)
        if bar is None:
            return 0.0
        multiplier = float(bar.contract_multiplier)
        return (curr_price - avg_price) * quantity * multiplier

    def  calculate_total_futures_unrealised_pnl(self) -> float:
        total = 0.0
        for ticker, quantity in self.holdings.items():
            if quantity == 0:
                continue
            asset_type = self.asset_type_by_ticker.get(ticker)
            if asset_type != AssetType.FUTURES:
                continue

            curr_price = self.get_latest_price(ticker)
            avg_price = self.avg_price.get(ticker, 0.0)

            bar = self.data_loader.get_current_bar(ticker)
            if bar is None:
                continue
            multiplier = float(bar.contract_multiplier)
            total += (curr_price - avg_price) * quantity * multiplier
        return total
    
    def calculate_holdings_value(self) -> float:
        total_value = 0.0
        for ticker, quantity in self.holdings.items():
            asset_type = self.asset_type_by_ticker.get(ticker)
            if asset_type == AssetType.FUTURES:
                continue
            if quantity == 0:
                continue
            price = self.data_loader.bar_lookup[ticker][self.data_loader.curr_datetime].close
            position_value = quantity * price
            if asset_type == AssetType.FOREX:
                bar = self.data_loader.get_current_bar(ticker)
                if bar is None:
                    raise ValueError(f"No price data available for ticker {ticker} at the time of holdings value calculation.")
                position_value = self.convert_to_account_currency(position_value, bar.quote_currency)
            total_value += position_value
        return total_value
    

    # def generate_order(self, signal: SignalEvent) -> OrderEvent:
    #     ticker = signal.ticker
    #     signal_type = signal.signal_type
    #     stock_quantity = self.holdings[ticker]
    #     order_quantity = self.fixed_quantity * signal.strength

    #     if order_quantity <= 0:
    #         raise ValueError(f"Invalid order quantity {order_quantity} generated from signal strength {signal.strength}. Order quantity must be positive.")
        
    #     if signal_type == 'LONG':
    #         return self.generate_long_order(ticker, stock_quantity, order_quantity, signal.datetime)
        
    #     elif signal_type == 'SHORT':
    #         return self.generate_short_order(ticker, stock_quantity, order_quantity,signal.datetime)
        
    #     elif signal_type == 'EXIT':
    #         return self.generate_exit_order(ticker, stock_quantity, exit_frac = signal.strength, dt = signal.datetime)
       
    #     else:
    #         raise ValueError(f"Invalid signal type {signal_type} in signal event. Expected 'LONG', 'SHORT', or 'EXIT'.")
    
    def generate_order(self, signal: SignalEvent):
        ticker = signal.ticker
        signal_type = signal.signal_type
        current_quantity = self.holdings[ticker]

        if signal_type == "EXIT":
            return self.generate_exit_order(ticker, current_quantity, exit_frac=signal.strength, dt = signal.datetime)
        
        if signal_type not in {"LONG", "SHORT"}:
            raise ValueError(
                f"Invalid signal type {signal_type}"
                "Expected 'LONG', 'SHORT', or 'EXIT'"
            )       
        
        target_qty = self.calculate_target_quantity(signal)

        if target_qty <= 0:
            raise ValueError(f"Invalid quantity {target_qty}")
        
        if signal_type == "LONG":
            target_qty = target_qty
        else:
            target_qty = -target_qty

        order_qty = target_qty - current_quantity

        direction = "BUY" if order_qty >= 0 else "SELL"

        return OrderEvent(
            ticker=ticker,
            asset_type=self.asset_type_by_ticker.get(ticker),
            datetime=signal.datetime,
            order_type="MKT",
            quantity= abs(order_qty),
            direction=direction,
        )

    def generate_long_order(self, ticker: str, stock_quantity: int, order_quantity: int, dt: datetime) -> OrderEvent:
        if stock_quantity >= 0:
            #If current position is flat or long, buy more
            buy_quantity = order_quantity
        else:
            #If current position is short, buy to cover existing short position and open a new long position
            buy_quantity = abs(stock_quantity) + order_quantity
        return OrderEvent(
            ticker = ticker,
            asset_type = self.asset_type_by_ticker.get(ticker),
            datetime = dt,
            order_type = "MKT",
            quantity = buy_quantity,
            direction = "BUY"
        )
    
    def generate_short_order(self, ticker: str, stock_quantity: int, order_quantity: int, dt: datetime) -> OrderEvent:
        if stock_quantity <= 0:
            #If current position is flat or short, sell more
            sell_quantity = order_quantity
        else:
            #If current position is long, sell to reduce the existing long position
            sell_quantity = stock_quantity + order_quantity
        return OrderEvent(
            ticker = ticker,
            asset_type = self.asset_type_by_ticker.get(ticker),
            datetime = dt,
            order_type = "MKT",
            quantity = sell_quantity,
            direction = "SELL"
        )

    def generate_exit_order(self, ticker: str, stock_quantity: int, exit_frac: float, dt: datetime) -> OrderEvent:
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
            asset_type = self.asset_type_by_ticker.get(ticker),
            datetime = dt,
            order_type = "MKT",
            quantity = buy_or_sell_quantity,
            direction = direction
        )
    

    def generate_exit_order(self, ticker: str, current_quantity: float, exit_frac: float, dt: datetime):
        if current_quantity == 0:
            return None

        if not 0 < exit_frac <= 1:
            raise ValueError(
                f"Invalid exit fraction {exit_frac}"
            )

        if exit_frac == 1.0:
            exit_quantity = abs(current_quantity)

        if exit_quantity <= 0:
            return None

        direction = "SELL" if current_quantity > 0 else "BUY"

        return OrderEvent(
            ticker=ticker,
            asset_type=self.asset_type_by_ticker.get(ticker),
            datetime=dt,
            order_type="MKT",
            quantity=exit_quantity,
            direction=direction,
        )


    def update_fill(self, event: FillEvent) -> None:
        if event.type != "FILL":
            raise ValueError(f"Invalid event type {event.type} in fill update. Expected 'FILL'.")
        
        ticker = event.ticker

        curr_quantity = self.holdings.get(ticker, 0)
        trade_quantity = event.quantity if event.direction == "BUY" else -event.quantity
        new_quantity = curr_quantity + trade_quantity
        multiplier = self.get_contract_multiplier(ticker)
        print(f"fill cost = {event.fill_cost}, multiplier = {multiplier}")

        net_realised_pnl = self.update_position_tracker(
                                ticker, 
                                curr_quantity,
                                trade_quantity, 
                                event.fill_cost, 
                                event.commission, 
                                multiplier = multiplier,
        )

        self.update_cash(event, net_realised_pnl)

        self.holdings[ticker] = new_quantity
        print(f"Updated holdings for {ticker}: {curr_quantity} -> {new_quantity}")
        print(f"Current capital after fill: {self.current_capital}")
        self.realised_pnl += net_realised_pnl
        print(f"Realized PnL after fill: {self.realised_pnl}")

        self.update_fill_records(event,
                            curr_quantity,
                            new_quantity,
                            realised_pnl_day= net_realised_pnl)
        self.end_equity()

    

    def update_cash(self, fill: FillEvent, realised_pnl_day: float) -> None:
        fill_cost = fill.quantity * fill.fill_cost
        if fill.asset_type == AssetType.FUTURES:
            cash_chng = realised_pnl_day
        else:
            if fill.direction == "BUY":
                cash_chng = -(fill_cost + fill.commission)
            elif fill.direction == "SELL":
                cash_chng = (fill_cost - fill.commission)
            else:
                raise ValueError(f"Invalid fill direction {fill.direction} in cash update. Expected 'BUY' or 'SELL'.")
        self.cash_reserves[self.account_currency] += cash_chng
        self.current_capital = self.cash_reserves[self.account_currency]
        self.total_commission += fill.commission
    
    def end_equity(self):
        cash_value = self.calculate_cash_value()
        current_holdings = self.calculate_holdings_value()
        futures_unrealised_pnl = self.calculate_total_futures_unrealised_pnl()
        #end_equity = current_holdings + self.current_capital + futures_unrealised_pnl
        self.current_equity = current_holdings + self.current_capital + futures_unrealised_pnl
        return self.current_equity

        #backtest_run.end_equity = end_equity



    #Updates average price and realized PnL for the ticker based on the new fill
    #Note: Returns -commission as a negative cost to the trade
    def update_position_tracker(self, ticker: str, curr_quantity: float, fill_quantity: float, fill_price: float, commission: float, multiplier: float) -> float:
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
            self.avg_price[ticker] = (old_position_value + additional_position_value) / abs(new_quantity)
            return -commission

        #Opposite direction trade: reducing, exiting or position reversal
        closing_quantity = min(abs(curr_quantity), abs(fill_quantity))
        if curr_quantity > 0:
            #Close long position by selling
            realised_pnl_day = closing_quantity * (fill_price - curr_avg_price) * multiplier
        else:
            #Close short position by buying
            realised_pnl_day = closing_quantity * (curr_avg_price - fill_price) * multiplier
        
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
    

    def update_fill_records(self, fill: FillEvent, prev_quantity: float, new_quantity: float, realised_pnl_day: float) -> None:
        record = {
                "date": fill.datetime,
                "ticker": fill.ticker,
                "source_contract_code" : self.get_source_contract_code(fill.ticker) if fill.asset_type == AssetType.FUTURES else None,
                "quantity": fill.quantity,
                "fill_price": fill.fill_cost,
                "direction": fill.direction,
                "commission": fill.commission,
                "previous_quantity": prev_quantity,
                "new_quantity": new_quantity,
                "realised_pnl_day": realised_pnl_day,
            }
        self.fill_record.append(record)

        # PortfolioFillRecord.objects.create(
        #     backtest_run = self.backtest_run,
        #     date = fill.datetime,
        #     ticker = fill.ticker,
        #     quantity = to_decimal(fill.quantity),
        #     fill_price = to_decimal(fill.fill_cost),
        #     direction = fill.direction,
        #     commission = to_decimal(fill.commission),
        #     previous_quantity = to_decimal(prev_quantity),
        #     new_quantity = to_decimal(new_quantity),
        #     realised_pnl_day = to_decimal(realised_pnl_day),
        # )


    #Updates equity record for each day, should be called whenever .next_day() is called
    def update_equity_record(self) -> None:
        date = self.data_loader.get_current_datetime()

        holdings_value = self.calculate_holdings_value()
        futures_unrealised_pnl = self.calculate_total_futures_unrealised_pnl()
        unrealised_pnl = self.calculate_unrealised_pnl()
        cash_value = self.calculate_cash_value()
        total_equity = cash_value + holdings_value + futures_unrealised_pnl

        #calculates all investments long + short
        gross_exposure = 0.0

        #calculates long - short investments
        net_exposure = 0.0

        for ticker, quantity in self.holdings.items():
            price = self.get_latest_price(ticker)
            exposure = price * quantity

            asset_type = self.asset_type_by_ticker.get(ticker)

            if asset_type == AssetType.FUTURES:
                bar = self.data_loader.get_current_bar(ticker)
                if bar is None:
                    continue
                multiplier = float(bar.contract_multiplier)
                exposure = price * quantity * multiplier

            elif asset_type == AssetType.FOREX:
                bar = self.data_loader.get_current_bar(ticker)
                if bar is None:
                    continue
                exposure = self.convert_to_account_currency(exposure, bar.quote_currency)
            
            gross_exposure += abs(exposure)
            net_exposure += exposure
        
        #Higher ratio = more risk, lower ratio = less risk
        gross_exposure_leverage = gross_exposure / total_equity if total_equity != 0 else 0.0

        other_unrealised_pnl = self.calculate_unrealised_pnl()
        total_unrealised_pnl = futures_unrealised_pnl + other_unrealised_pnl

        record = {
                "date": date,
                "cash": self.current_capital,
                "holdings_value": holdings_value,
                "equity": total_equity,
                "realised_pnl" : self.realised_pnl,
                "unrealised_pnl": unrealised_pnl,
                "futures_unrealised_pnl": futures_unrealised_pnl,
                "total_commission" : self.total_commission,
                "gross_exposure": gross_exposure,
                "net_exposure" : net_exposure,
                "gross_exposure_leverage" : gross_exposure_leverage
            }

        self.equity_record[date] = record
        
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
        self.update_position_record(date)
    
    def update_position_record(self, date: datetime) -> None:
        for ticker, quantity in self.holdings.items():
            multiplier = self.get_contract_multiplier(ticker)
            market_price = self.get_latest_price(ticker)
            market_value = market_price * quantity * multiplier
            unrealised_pnl = self.calculate_unrealised_pnl_ticker(ticker)

            asset_type = self.asset_type_by_ticker.get(ticker)
            asset_obj = self.asset_cache.get(ticker)
            stock = asset_obj if asset_type == AssetType.STOCK else None
            forex = asset_obj if asset_type == AssetType.FOREX else None
            future = asset_obj if asset_type == AssetType.FUTURES else None

            record = {
                "date": date,
                "ticker": ticker,
                "stock": stock,
                "forex": forex,
                "future": future,
                "quantity": quantity,
                "avg_price": self.avg_price[ticker],
                "market_price": market_price,
                "market_value": market_value,
                "unrealised_pnl": unrealised_pnl,
                "multiplier": multiplier,
            }

            self.position_records[(date, ticker)] = record
            
            # PortfolioPositionRecord.objects.update_or_create(
            #     backtest_run = self.backtest_run,
            #     date = date,
            #     ticker = ticker,
            #     defaults = {
            #         "stock": stock,
            #         "forex": forex,
            #         "future": future,
            #         "quantity": to_decimal(quantity),
            #         "avg_price": to_decimal(self.avg_price[ticker]),
            #         "market_price": to_decimal(market_price),
            #         "market_value": to_decimal(market_value),
            #         "unrealised_pnl": to_decimal(unrealised_pnl),
            #     },
            # )


    
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

        record = {
            "date": date,
            "ticker": self.benchmark_ticker,
            "close_price": benchmark_price,
            "quantity": self.benchmark_quantity,
            "market_value": market_value,
            "unrealised_pnl": benchmark_unrealised_pnl,
        }

        self.benchmark_records[date] = record
        # BenchmarkRecord.objects.update_or_create(
        #     backtest_run = self.backtest_run,
        #     date = date,
        #     defaults = {
        #         "ticker": self.benchmark_ticker,
        #         "close_price": to_decimal(benchmark_price),
        #         "quantity": to_decimal(self.benchmark_quantity),
        #         "market_value": to_decimal(market_value),
        #         "unrealised_pnl": to_decimal(benchmark_unrealised_pnl),
        #     }
        # )
        #print(f"Updated benchmark record for {self.benchmark_ticker} on {date}: price {benchmark_price}, quantity {self.benchmark_quantity}, market value {market_value}, unrealised PnL {benchmark_unrealised_pnl}")


        

        





        
    
