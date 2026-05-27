from django.db import models
# from django.contrib.auth.models import User
from django.conf import settings

#Time stamp model to track creation date/time and update date/time
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add = True)
    updated_at = models.DateTimeField(auto_now = True)

    class Meta:
        abstract = True


# # Create your models here.
# class UserProfile(models.Model):
#     user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="User_Profile")
#     cash_holdings = models.DecimalField(max_digits=20, decimal_places=2, default=100000.00)

#     def __str__(self) -> str:
#         return f"{self.user.username}'s profile with cash holdings: {self.cash_holdings}"
    
class Stock(models.Model):
    ticker = models.CharField(max_length=10, unique=True)
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
    
    def __str__(self) -> str:
        return f"{self.stock.ticker} price history on {self.date}: Open: {self.open_price}, High: {self.high_price}, Low: {self.low_price}, Close: {self.close_price}, Volume: {self.volume}"

class FuturesContract(models.Model):
    #Example
    # root_symbol = "ES"
    # contract_code = "ESZ23"
    # expiry_date = "2025-06-02"

    root_symbol = models.CharField(max_length=10)
    contract_code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    expiry_date = models.DateField()

    def __str__(self) -> str:
        return f"{self.contract_code} ({self.name}) expiring on {self.expiry_date}"

class FuturesPriceHistory(models.Model):
    contracts = models.ForeignKey(FuturesContract, on_delete=models.CASCADE, related_name="futures_price_history")
    date = models.DateField()
    open_price = models.DecimalField(max_digits = 20, decimal_places=2)
    High_price = models.DecimalField(max_digits = 20, decimal_places=2)
    low_price = models.DecimalField(max_digits = 20, decimal_places=2)
    volume = models.PositiveBigIntegerField(default=0)
    close_price = models.DecimalField(max_digits = 20, decimal_places=2)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["contracts", "date"], name="unique_contract_date")]

    def __str__(self) -> str:
        return f"{self.contracts.contract_code} - {self.date} expiring on {self.contracts.expiry_date}"
    

#This is to store results of each backtest
#Backtest contains final result of a backtest run, mainly storing performance metrics

class Backtest(TimeStampedModel): 
    class AssetType(models.TextChoices):
        STOCK = "STOCK", "Stock"
        FUTURES = "FUTURES", "Futures"

    #name of backtest run
    name = models.CharField(max_length=255, blank=True)

    #strategy name
    strategy_name = models.CharField(max_length=100, blank=False)

    #Find out what is being traded (stock, futures etc..)
    asset_type = models.CharField(max_length=10, choices= AssetType.choices)

    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, null=True, blank=True)
    futures = models.ForeignKey(FuturesContract, on_delete=models.CASCADE, null=True, blank= True)

    start_date = models.DateField()
    end_date = models.DateField()

    starting_capital = models.DecimalField(max_digits = 10, decimal_places=2)
    end_equity = models.DecimalField(max_digits = 15, decimal_places= 2)

    #Trade performance metrics 
    total_return = models.FloatField()
    cagr = models.FloatField()
    sharpe_ratio = models.FloatField()
    sortino_ratio = models.FloatField()
    drawdown = models.FloatField()

    #portfolio performance metrics
    total_trade = models.PositiveBigIntegerField(default = 0)
    win_rate = models.FloatField(default = 0.0)
    average_win = models.FloatField(default= 0.0)
    average_loss = models.FloatField(default = 0.0)
    profit_factor = models.FloatField(default = 0.0)


#This is to store information of every trade made in the backtest run
class BacktestTrade(models.Model):
    class Signal(models.TextChoices):
        LONG = "LONG", 'Long'       #Bullish 
        SHORT = "SHORT", 'Short'    #Bearish

    backtest = models.ForeignKey(Backtest, on_delete=models.CASCADE, related_name="trades")

    symbol = models.CharField(max_length = 20)
    direction = models.CharField(max_length=10, choices=Signal.choices)

    entry_time = models.DateTimeField()
    exit_time = models.DateTimeField()

    volume = models.DecimalField(max_digits = 20, decimal_places = 8)

    entry_price = models.DecimalField(max_digits = 20, decimal_places = 8)
    exit_price = models.DecimalField(max_digits = 20, decimal_places= 8)

    pnl = models.DecimalField(max_digits = 20, decimal_places= 2)
    pct = models.FloatField(default= 0.0)


#This is to store portfolio information at every day 
class EquityPoint(models.Model):
    backtest = models.ForeignKey(Backtest, on_delete=models.CASCADE, related_name="equity_point")\
    
    datetime = models.DateTimeField()

    cash = models.DecimalField(max_digits = 20, decimal_places = 8)
    holdings_value = models.DecimalField(max_digits=20, decimal_places= 8)
    equity = models.DecimalField(max_digits = 20, decimal_places = 8)
    pct = models.FloatField(default=0.0)
    drawdown = models.FloatField(default=0.0)


