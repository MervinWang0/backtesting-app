from django.core.management.base import BaseCommand
from base.models import ForexPair, ForexPriceHistory
import yfinance as yf
from datetime import datetime
import pandas as pd
import requests
from io import StringIO

DEFAULT_FOREX_PAIRS = [
    ("EURUSD=X", "EUR/USD"),
    ("GBPUSD=X", "GBP/USD"),
    ("USDJPY=X", "USD/JPY"),
    ("USDCHF=X", "USD/CHF"),
    ("AUDUSD=X", "AUD/USD"),
    ("NZDUSD=X", "NZD/USD"),
    ("USDCAD=X", "USD/CAD"),
    ("EURGBP=X", "EUR/GBP"),
    ("EURJPY=X", "EUR/JPY"),
    ("GBPJPY=X", "GBP/JPY"),
]

class Command(BaseCommand):
    help = "Loads Historical forex data through yahoo finance"

    def add_arguments(self, parser):
        parser.add_argument(
            "--symbol",
            type=str,
            help = "enter a forex symbol, for example EURUSD, EUR/USD or EURUSD=X"
        )

        parser.add_argument(
            "--period",
            type=str,
            default= "1mo"
            help = "enter interval , eg 1mo, 6mo, 1y"
        )

        parser.add_argument(
            "--interval",
            type=str,
            default="1d",
            help="enter interval, eg 1d, 1h, 15m"
        )
    
    def handle(self, *args, **options):
        symbol = options.get("symbol")
        period = options.get("period")
        interval = options.get("interval")

        if symbol:
            forex_pairs = [self.fix_forex_symbol(symbol)]
        else:
            forex_pairs = DEFAULT_FOREX_PAIRS
        
        for yf_symbol, name in forex_pairs:
            forex_pair, created = ForexPair.objects.get_or_create(
                ticker = yf_symbol,
                defaults = {
                    "name" : name
                    
                 }
            )
        new

