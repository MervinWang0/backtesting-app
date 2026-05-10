from django.db import models
from django.contrib.auth.models import User
from Orbital.Orbital import settings

# Create your models here.
class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="User_Profile")
    cash_holdings = models.DecimalField(max_digits=20, decimal_places=2, default=100000.00)

    def __str__(self) -> str:
        return f"{self.user.username}'s profile with cash holdings: {self.cash_holdings}"
    
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
    
class Backtest(TimeStampedModel): 