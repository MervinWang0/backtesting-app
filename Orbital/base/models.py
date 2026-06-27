from django.db import models
# from django.contrib.auth.models import User
from django.conf import settings
from decimal import Decimal


#Time stamp model to track creation date/time and update date/time
class TimeStampedModel(models.Model):
    created_at = models.DateField(auto_now_add = True)
    updated_at = models.DateField(auto_now = True)

    class Meta:
        abstract = True


# # Create your models here.
# class UserProfile(models.Model):
#     user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="User_Profile")
#     cash_holdings = models.DecimalField(max_digits=20, decimal_places=2, default=100000.00)

#     def __str__(self) -> str:
#         return f"{self.user.username}'s profile with cash holdings: {self.cash_holdings}"
    
class Stock(models.Model):
    ticker = models.CharField(max_length=10, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    industry = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        if self.is_active:
            return f"[ACTIVE] {self.ticker} - {self.name} of {self.industry}"
        else:
            return f"[INACTIVE] {self.ticker} - {self.name} of {self.industry}"
    
class StockPriceHistory(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name="stock_price_history")
    date = models.DateField()

    open_price = models.DecimalField(max_digits= 20, decimal_places=2)
    high_price = models.DecimalField(max_digits= 20, decimal_places = 2)
    low_price = models.DecimalField(max_digits= 20, decimal_places = 2)
    volume = models.PositiveBigIntegerField(default= 0)
    close_price = models.DecimalField(max_digits= 20, decimal_places = 2)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["stock", "date"], name="unique_stock_date")]
        ordering=["date"]
        indexes = [models.Index(fields=["stock", "-date"], name = "Unique_stock_price_date")]
    
    def __str__(self) -> str:
        return f"{self.stock.ticker} price history on {self.date}: Open: {self.open_price}, High: {self.high_price}, Low: {self.low_price}, Close: {self.close_price}, Volume: {self.volume}"

class FuturesContract(models.Model):
    #Example
    # root_symbol = "ES"
    # contract_code = "ESZ23"
    # expiry_date = "2025-06-02"

    root_symbol = models.CharField(max_length = 10)
    contract_code = models.CharField(max_length = 50, unique=True)
    name = models.CharField(max_length = 100)

    exchange = models.CharField(max_length = 30, blank=True)
    currency = models.CharField(max_length = 10, default = "USD")
    expiry_date = models.DateField()

    tick_multiplier = models.DecimalField(max_digits = 20, decimal_places = 6, default = Decimal("1.0"))
    tick_size = models.DecimalField(max_digits = 20, decimal_places = 6, default = Decimal("0.01"))

    is_active = models.BooleanField(default = True)

    class Meta:
        ordering = ["root_symbol", "expiry_date"]
        indexes = [
            models.Index(fields = ["root_symbol", "expiry_date"])
        ]

    def __str__(self) -> str:
        return f"{self.contract_code} ({self.name}) expiring on {self.expiry_date}"

class FuturesPriceHistory(models.Model):
    contract = models.ForeignKey(FuturesContract, on_delete=models.CASCADE, related_name="futures_price_history")
    date = models.DateField()
    open_price = models.DecimalField(max_digits = 20, decimal_places=6)
    high_price = models.DecimalField(max_digits = 20, decimal_places=6)
    low_price = models.DecimalField(max_digits = 20, decimal_places=6)
    volume = models.PositiveBigIntegerField(default=0)
    close_price = models.DecimalField(max_digits = 20, decimal_places=6)

    #number of still active contracts 
    active_contracts = models.BigIntegerField(default = 0)

    class Meta:
        ordering = ["contract", "date"]
        constraints = [models.UniqueConstraint(fields=["contract", "date"], name="unique_contract_date")]

        indexes = [
            models.Index(fields = ["contract", "date"]),
            models.Index(fields = ["date"])
        ]

    def __str__(self) -> str:
        return f"{self.contract.contract_code} - {self.date} expiring on {self.contract.expiry_date}"
    
class ContinuousFuturesSeries(models.Model):

    #This defines what method to use to decide when to switch from one contract to the next
    '''
    Days_before_expiry : switch to the next contract when it is n days from the existing contract expiry date.
    Volume : Switch when the next contract has a higher trading volume than the current contract
    Active contracts : Switch when next contract has more contracts than current contract
    Manual : Decided on rollover dates yourself
    '''
    class RollOverRule(models.TextChoices):
        DAYS_BEFORE_EXPIRY = "DAYS_BEFORE_EXPIRY", "Days Before Expiry"
        VOLUME = "VOLUME", "Volume"
        ACTIVE_CONTRACTS = "ACTIVE_CONTRACTS", "Active Contracts"
        MANUAL = "MANUAL", "Manual"

    class AdjustmentMethod(models.TextChoices):
        NONE = "NONE", "No adjustment"
        BACK_ADJUSTED = "BACK_ADJUSTED","Back adjusted"
        RATIO_ADJUSTED = "RATIO_ADJUSTED", "Ratio adjusted"
    
    contract_symbol = models.CharField(max_length=20)
    #index stores where this contract is currently stitched into the entire series
    #eg: contract_index = 1 is the head of the series
    contract_index = models.PositiveSmallIntegerField(default=1)

    rollover_rule = models.CharField(max_length=30, choices=RollOverRule.choices, default=RollOverRule.DAYS_BEFORE_EXPIRY)
    roll_days = models.PositiveSmallIntegerField(default=5)

    adjustment_method = models.CharField(max_length=30, choices = AdjustmentMethod.choices, default=AdjustmentMethod.BACK_ADJUSTED)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now = True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields = [
                    "contract_symbol",
                    "contract_index",
                    "rollover_rule",
                    "roll_days",
                    "adjustment_method"
                ],
                name = "unique_continuous_futures_series",
            )
        ]
    def __str__(self):
        return f"{self.contract_symbol} at #{self.contract_index}"

class ContinuousFuturesPriceHistory(models.Model):
    series = models.ForeignKey(ContinuousFuturesSeries, on_delete=models.CASCADE, related_name="series")
    source_contract = models.ForeignKey(FuturesContract, on_delete=models.PROTECT, related_name="source_contract")

    date = models.DateTimeField()
    open_price = models.DecimalField(max_digits = 20, decimal_places=6)
    high_price = models.DecimalField(max_digits = 20, decimal_places=6)
    low_price = models.DecimalField(max_digits = 20, decimal_places=6)
    volume = models.PositiveBigIntegerField(default=0)
    close_price = models.DecimalField(max_digits = 20, decimal_places=6)

    active_contracts = models.BigIntegerField(default = 0)

    adjustment_val = models.DecimalField(max_digits = 20, decimal_places = 6, default = Decimal("0.0"))

    is_rolled = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields = ["series", "date"], name="Unique_continuous_series_date")]
        ordering = ["series", "date"]
    
    def __str__(self):
        return f"{self.series.contract_symbol} continuous from {self.date}"

class FuturesRollEvent(models.Model):
    series = models.ForeignKey(ContinuousFuturesSeries, on_delete=models.CASCADE, related_name= "roll_events")
    roll_date = models.DateTimeField()
    from_contract = models.ForeignKey(FuturesContract, on_delete=models.PROTECT, related_name="roll_from")
    to_contract = models.ForeignKey(FuturesContract, on_delete=models.PROTECT, related_name="roll_to")

    class Meta:
        constraints = [models.UniqueConstraint(fields = ["series", "roll_date"], name = "unique_futures_roll_event")]
        ordering = ["series", "roll_date"]

    def __str__(self):
        return (
            f"{self.series.contract_symbol} rolled on {self.roll_date}"
            f"{self.from_contract.contract_code} to {self.to_contract.contract_code}"
        )    
    
    
class ForexPair(models.Model):
    ticker = models.CharField(max_length=20, unique = True)
    #USDEUR

    name = models.CharField(max_length=20)

    base_currency = models.CharField(max_length=10)
    quote_currency = models.CharField(max_length=10)

    pip_value = models.FloatField(default = 0.0001)
    lot_size = models.IntegerField(default = 100000)

    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.ticker

class ForexPriceHistory(models.Model):
    pair = models.ForeignKey(ForexPair, on_delete=models.CASCADE, related_name="forex_price_history")
    timestamp = models.DateTimeField()

    open_price = models.DecimalField(max_digits = 20, decimal_places= 4)
    high_price = models.DecimalField(max_digits = 20, decimal_places= 4)
    low_price = models.DecimalField(max_digits = 20, decimal_places= 4)
    volume = models.PositiveBigIntegerField(default=0, null = True, blank= True)
    close_price = models.DecimalField(max_digits = 20, decimal_places= 4)

    class Meta:
        unique_together = ("pair", "timestamp")
        ordering = ["timestamp"]
        indexes = [
            models.Index(fields=["pair", "timestamp"], name="forex_pair_timestamp_idx")
        ]
    
    def __str__(self) -> str:
        return f"{self.pair.ticker} on {self.timestamp}"





#This is to store results of each backtest
#Backtest contains final result of a backtest run, mainly storing performance metrics

class BacktestRun(TimeStampedModel): 
    class AssetType(models.TextChoices):
        STOCK = "STOCK", "Stock"
        FUTURES = "FUTURES", "Futures"
        FOREX = "FOREX", "Forex"

    #name of backtest run
    run_name = models.CharField(max_length=255, blank=True)

    #strategy name
    strategy_name = models.CharField(max_length=100, blank=False)

    #Find out what is being traded (stock, futures etc..)
    asset_type = models.CharField(max_length=10, choices= AssetType.choices)

    fixed_quantity = models.DecimalField(max_digits=15, decimal_places= 2, default= 5)

    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, null=True, blank=True)
    futures = models.ForeignKey(FuturesContract, on_delete=models.CASCADE, null=True, blank= True)
    forex = models.ForeignKey(ForexPair, on_delete=models.CASCADE, null=True, blank=True)

    start_date = models.DateField()
    end_date = models.DateField()

    initial_capital = models.DecimalField(max_digits = 10, decimal_places=2)
    end_equity = models.DecimalField(max_digits = 15, decimal_places= 2)

    is_completed = models.BooleanField(default = False)
    completed_at = models.DateField(blank=True, null=True)

    #Stores list of tickers used in the backtest
    tickers = models.JSONField(default=list, blank=True)

    # #Trade performance metrics 
    # total_return = models.FloatField()
    # cagr = models.FloatField()
    # sharpe_ratio = models.FloatField()
    # sortino_ratio = models.FloatField()
    # drawdown = models.FloatField()

    # #portfolio performance metrics
    # total_trade = models.PositiveBigIntegerField(default = 0)
    # win_rate = models.FloatField(default = 0.0)
    # average_win = models.FloatField(default= 0.0)
    # average_loss = models.FloatField(default = 0.0)
    # profit_factor = models.FloatField(default = 0.0)

    def __str__(self):
        return f"BacktestRun {self.run_name} using {self.strategy_name}"


class PortfolioEquityRecord(TimeStampedModel):
    backtest_run = models.ForeignKey(BacktestRun, on_delete=models.CASCADE, related_name="equity_record")
    date = models.DateField()

    cash = models.DecimalField(max_digits=20, decimal_places=2)
    holdings_value = models.DecimalField(max_digits=20, decimal_places=2)
    equity = models.DecimalField(max_digits=20, decimal_places=2)
    realised_pnl = models.DecimalField(max_digits=20, decimal_places=2)
    unrealised_pnl =models.DecimalField(max_digits=20, decimal_places=2)
    total_commission = models.DecimalField(max_digits=20, decimal_places=2)
    gross_exposure = models.DecimalField(max_digits=20, decimal_places=2)
    net_exposure = models.DecimalField(max_digits=20, decimal_places=2)
    gross_exposure_leverage = models.DecimalField(max_digits=20, decimal_places=2)

    class Meta:
        constraints = [models.UniqueConstraint(fields = ["backtest_run", "date"],
                                                name = "unique_equity_record")]
        ordering = ["date"]

    def __str__(self):
        return f"{self.backtest_run} equity record on {self.date} : {self.equity}"
    
class PortfolioFillRecord(TimeStampedModel):
    class DirectionType(models.TextChoices):
        BUY = "BUY", "Buy"
        SELL = "SELL", "Sell"
    
    backtest_run = models.ForeignKey(BacktestRun, on_delete=models.CASCADE, related_name="fill_record")
    date = models.DateField()
    ticker = models.CharField(max_length = 20)
    quantity = models.DecimalField(max_digits = 20, decimal_places = 4)
    fill_price = models.DecimalField(max_digits = 20, decimal_places = 4)
    direction = models.CharField(max_length=10, choices= DirectionType)
    commission = models.DecimalField(max_digits = 20, decimal_places = 4)
    previous_quantity = models.DecimalField(max_digits = 20, decimal_places = 4)
    new_quantity = models.DecimalField(max_digits = 20, decimal_places = 4)
    realised_pnl_day = models.DecimalField(max_digits = 20, decimal_places = 4)

    class Meta:
        ordering = ["date"]
    
    def __str__(self):
        return f"{self.backtest_run} fill record"

class PortfolioPositionRecord(TimeStampedModel):
    backtest_run = models.ForeignKey(BacktestRun, on_delete=models.CASCADE, related_name="position_record")
    date = models.DateField()
    ticker = models.CharField(max_length=20)
    stock = models.ForeignKey(Stock, on_delete=models.SET_NULL, blank = True, null = True)
    forex = models.ForeignKey(ForexPair, on_delete= models.SET_NULL, blank = True, null = True)

    quantity = models.DecimalField(max_digits = 20, decimal_places = 4)
    avg_price = models.DecimalField(max_digits = 20, decimal_places = 4)
    market_price = models.DecimalField(max_digits = 20, decimal_places = 4)
    market_value = models.DecimalField(max_digits = 20, decimal_places = 4)
    unrealised_pnl = models.DecimalField(max_digits = 20, decimal_places = 4)
    
    class Meta:
        constraints = [models.UniqueConstraint(fields = ["backtest_run", "date", "ticker"],
                      name = "Unique_positions")]
        ordering = ["date", "ticker"]

    def __str__(self):
        return (f"{self.backtest_run}: "
                f"{self.ticker} : {self.quantity} on {self.date}" )
    
class BenchmarkRecord(TimeStampedModel):
    backtest_run = models.ForeignKey(BacktestRun, on_delete=models.CASCADE, related_name = "benchmark_record")
    date = models.DateField()
    ticker = models.CharField(max_length=20)
    close_price = models.DecimalField(max_digits = 20, decimal_places = 4)
    quantity = models.DecimalField(max_digits = 20, decimal_places = 4)
    market_value = models.DecimalField(max_digits = 20, decimal_places = 4)
    unrealised_pnl = models.DecimalField(max_digits = 20, decimal_places = 4)

    class Meta:
        constraints = [models.UniqueConstraint(fields = ["backtest_run", "date"],
                                                name = "unique_benchmark_record")]
        ordering = ["date"]
    
    def __str__(self):
        return (f"{self.backtest_run}: "
                f"{self.ticker} with market value {self.market_value} on {self.date}" )
    
#paper account 
class PaperAccount(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name = "paper_accounts",
    )

    name = models.CharField(max_length=10, default = "Paper Account",)
    base_currency = models.CharField(max_length=3, default = "USD",)
    initial_capital = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("100000"),)
    cash_balance = models.DecimalField(max_digits = 20, decimal_places=2, default=Decimal("100000"),)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields = ["user", "name"],
            name = "Unique_paper_account",
        )]
    
    def __str__(self):
        return f"{self.user} created"

class PaperPositions(models.Model):
    account = models.ForeignKey(PaperAccount, on_delete=models.CASCADE, related_name = "positions")
    stock = models.ForeignKey(Stock, on_delete=models.PROTECT, related_name="stock_positions", null=True, blank=True)
    forex = models.ForeignKey(ForexPair, on_delete=models.PROTECT, related_name = "forex_positions", null=True, blank=True)
    futures = models.ForeignKey(FuturesContract, on_delete=models.PROTECT, related_name="futures_positions", null=True, blank=True)

    #stock 
    stock_quantity = models.DecimalField(max_digits=10, decimal_places=4, default=Decimal("0"))
    avg_cost = models.DecimalField(max_digits = 20, decimal_places=4, default=Decimal("0"))
    #for short positions 
    accum_borrowed = models.DecimalField(max_digits=20, decimal_places=4, default=Decimal("0"))
    
    realised_pnl = models.DecimalField(max_digits=20, decimal_places=4, default=Decimal("0"))

    updated_at = models.DateTimeField(auto_now = True)

    class Meta:
        indexes = [
            models.Index(
                fields= ["account", "stock", "forex", "futures"],
                name = "paper_positions",
            )
        ]
    
    def __str__(self):
        return f"{self.account}"
    
class PaperOrder(models.Model):
    class Order(models.TextChoices):
        BUY = "BUY", "Buy"
        SELL = "SELL", "Sell"
    
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        FILLED = "FILLED", "Filled"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"

    class OrderType(models.TextChoices):
        MARKET = "MARKET", "Market"
        LMT = "LMT", "Limit"
    
    account = models.ForeignKey(PaperAccount, on_delete=models.CASCADE)
    stock = models.ForeignKey(Stock, on_delete=models.PROTECT, related_name="stock_order", null=True, blank=True)
    forex = models.ForeignKey(ForexPair, on_delete=models.PROTECT, related_name = "forex_order", null=True, blank=True)
    futures = models.ForeignKey(FuturesContract, on_delete=models.PROTECT, related_name="futures_order", null=True, blank=True)

    order = models.CharField(max_length=10, choices=Order.choices,)
    order_type = models.CharField(max_length=10, choices = OrderType.choices , default = OrderType.MARKET,)
    status = models.CharField(max_length=10, choices = Status.choices, default = Status.PENDING, db_index = True,)
    quantity = models.DecimalField(max_digits=20, decimal_places=4)
    
    submitted_at = models.DateTimeField(auto_now_add=True)
    filled_at = models.DateTimeField(null=True, blank=True,)
    updated_at = models.DateTimeField(auto_now = True)

    class Meta:
        ordering = ["-submitted_at"]
        indexes = [models.Index(
            fields = ["account", "status", "submitted_at"]
        )]

    def __str__(self):
        f"{self.account}"

class PaperTrade(models.Model):
    order = models.OneToOneField(PaperOrder, on_delete=models.PROTECT, related_name="trade",)
    date = models.DateField()
    fulfilled_price = models.DecimalField(max_digits = 20, decimal_places=4)
    quantity = models.DecimalField(max_digits = 20, decimal_places=4)

    closed_quantity = models.DecimalField(max_digits=20, decimal_places=4)
    opened_quantity = models.DecimalField(max_digits=20, decimal_places=4)

    gross_amount = models.DecimalField(max_digits=20, decimal_places=4)
    commission = models.DecimalField(max_digits=10, decimal_places=4)
    realised_pnl = models.DecimalField(max_digits=20, decimal_places=4)
    cash_change = models.DecimalField(max_digits=20, decimal_places=4)

    executed_at = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ["-executed_at"]
    
    def __str__(self):
        return f"{self.order.side} {self.quantity} fulfilled"




            





# #This is to store information of every trade made in the backtest run
# class BacktestTrade(models.Model):
#     class Signal(models.TextChoices):
#         LONG = "LONG", 'Long'       #Bullish 
#         SHORT = "SHORT", 'Short'    #Bearish

#     backtest = models.ForeignKey(Backtest, on_delete=models.CASCADE, related_name = "trades")

#     symbol = models.CharField(max_length = 20)
#     direction = models.CharField(max_length=10, choices=Signal.choices)

#     entry_time = models.DateTimeField()
#     exit_time = models.DateTimeField()

#     volume = models.DecimalField(max_digits = 20, decimal_places = 8)

#     entry_price = models.DecimalField(max_digits = 20, decimal_places = 8)
#     exit_price = models.DecimalField(max_digits = 20, decimal_places= 8)

#     pnl = models.DecimalField(max_digits = 20, decimal_places= 2)
#     pct = models.FloatField(default= 0.0)


# #This is to store portfolio information at every day 
# class EquityPoint(models.Model):
#     backtest = models.ForeignKey(Backtest, on_delete=models.CASCADE, related_name = "equity_point")
    
#     datetime = models.DateTimeField()

#     cash = models.DecimalField(max_digits = 20, decimal_places = 8)
#     holdings_value = models.DecimalField(max_digits=20, decimal_places= 8)
#     equity = models.DecimalField(max_digits = 20, decimal_places = 8)
#     pct = models.FloatField(default=0.0)
#     drawdown = models.FloatField(default=0.0)


