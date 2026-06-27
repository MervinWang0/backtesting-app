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
            help = "enter a forex symbol, for example EURUSD, EUR/USD or EURUSD=X",
        )

        parser.add_argument(
            "--period",
            type=str,
            default= "1mo",
            help = "enter interval , eg 1mo, 6mo, 1y",
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
            base_currency = name[:3]
            quote_currency = name[4:7]
            forex_pair, created = ForexPair.objects.update_or_create(
                ticker = yf_symbol,
                defaults = {
                    "name" : name,
                    "base_currency" : base_currency,
                    "quote_currency" : quote_currency,
                 }
            )

            if created:
                print(f"Created new forex pair: {yf_symbol} - {name}")

            try:
                data = yf.download(
                    yf_symbol,
                    period = period,
                    interval = interval,
                    progress = False,
                    auto_adjust= False,
                    group_by= "column",
                    threads = False
                )
                
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = data.columns.get_level_values(0)
                
                if data.empty:
                    print(f"No data for {yf_symbol}")
                    continue

                count = 0

                for timestamp, row in data.iterrows():
                    if "Close" not in row or pd.isna(row["Close"]):
                        continue

                    candle_time = self.fix_timestamp(timestamp)

                    ForexPriceHistory.objects.update_or_create(
                        pair = forex_pair,
                        timestamp = candle_time,
                        defaults = {
                            "open_price": row["Open"],
                            "high_price": row["High"],
                            "low_price": row["Low"],
                            "close_price": row["Close"],
                            "volume": row["Volume"] if row["Volume"] else None,
                        },
                    )

                    count += 1

                print(f"{yf_symbol}: {count} records updated")
            
            except Exception as e:
                print(f"error fetching data for {yf_symbol}: {e}")
        print("finish")
        
    def fix_forex_symbol(self, symbol : str):
        '''
        converts user input to format needed for yahoo finance and into a name in the format USD/EUR
        '''
        symbol = symbol.strip().upper()
        symbol = symbol.replace("/", "").replace("-", "")

        if symbol.endswith("=X"):
            base_symbol = symbol.replace("=X", "")
            yf_symbol = symbol
        else:
            base_symbol = symbol
            yf_symbol = f"{symbol}=X"
        
        if len(base_symbol) == 6:
            name = f"{base_symbol[:3]}/{base_symbol[3:]}"
        else:
            name = base_symbol
        
        return yf_symbol, name
    
    def fix_timestamp(self, timestamp):
        ts = pd.Timestamp(timestamp)

        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        else:
            ts = ts.tz_convert("UTC")
        return ts.to_pydatetime()