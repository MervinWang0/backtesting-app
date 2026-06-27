from django.core.management.base import BaseCommand
from base.models import FuturesContract, FuturesPriceHistory
from datetime import datetime, date
import pandas as pd
import requests
from io import StringIO
import yfinance as yf
import re
import calendar



class Command(BaseCommand):
    help = "Load future data through yahoo finance"

    FUTURES_MONTHS = {
    "F": 1,   # January
    "G": 2,   # February
    "H": 3,   # March
    "J": 4,   # April
    "K": 5,   # May
    "M": 6,   # June
    "N": 7,   # July
    "Q": 8,   # August
    "U": 9,   # September
    "V": 10,  # October
    "X": 11,  # November
    "Z": 12,  # December
    }

    DEFAULT_FUTURES = {
        "ESM26.CME": {
            "root_symbol": "ES",
            "expiry_date": "2026-06-18",
        }
        # #Index futures
        # "ES=F": "E-mini S&P 100",
        # "NQ=F": "E-mini Nasdaq-100",
        # "YM=F": "Mini dow jones",
        # "RTY=F": "E-mini russell 2000",

        # #Energy futures
        # "CL=F": "Crude oil",
        # "BZ=F": "Brent crude oil",
        # "NG=F": "Natural gas",

        # #Metal futures
        # "GC=F": "Gold",
        # "SI=F": "Silver",
        # "HG=F": "Copper",

        # #Agriculture futures
        # "ZC=F": "Corn",
        # "ZW=F": "Wheat",
        # "ZS=F": "Soybean",

        # #Treasury futures
        # "ZB=F": "30-yr",
        # "ZN=F": "10-yr",
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "--symbol",
            type= str,
            help="Enter futures symbol, for example ESM26.CME",
        )

        parser.add_argument(
            "--root-symbol",
            type=str,
            required=False,
            help = "Root futures symbol, for example ES",
        )

        parser.add_argument(
            "--expiry-date",
            type=str,
            required=False,
            help="Expiry date in YYYY-MM-DD format",
        )

        parser.add_argument(
            "--period",
            type=str,
            default="1mo",
            help="Enter desired period, for example 1yr, 6mo",
        )

        parser.add_argument(
            "--interval",
            type=str,
            default="1d",
            help="Enter desired interval for example, 1d, 1h or 30m",
        )

    def handle(self, *args, **options):
        symbol = options.get("symbol")
        root_symbol = options.get("root_symbol")
        expiry_date = options.get("expiry_date")
        period = options.get("period")
        interval = options.get("interval")

        if symbol:
            symbol = symbol.strip().upper()

            root_symbol, _, _, _ = self.parse_code(symbol)
            infered_expiry = self.get_expiry_dates(symbol)
            if expiry_date:
                expiry_date = self.fix_expiry_date(expiry_date)

                if expiry_date != infered_expiry:
                    print("mismatch in expiry dates")
                    
                final_expiry = expiry_date
            else:
                final_expiry = infered_expiry
            futures = [(symbol, {"root_symbol" : root_symbol, "expiry_date": final_expiry,},)]
        else:
            futures = list(self.DEFAULT_FUTURES.items())

        for symbol, data in futures:
            expiry_date = data["expiry_date"]
            
            try:
                price_data = yf.download(
                    symbol,
                    period=period,
                    interval=interval,
                    progress=False,
                    auto_adjust = False,
                    group_by = "column",
                    threads = False,
                    multi_level_index=False,
                )
            except Exception as error:
                print(f"Failed to download {symbol}:{error}")
                continue
         
            if isinstance(price_data.columns, pd.MultiIndex):
                price_data.columns = price_data.columns.get_level_values(0)
            if price_data.empty:
                print(f'no data for {symbol}, continuing')
                continue

            future, created = FuturesContract.objects.update_or_create(
                contract_code=symbol,
                defaults={
                    "root_symbol": data["root_symbol"],
                    "name": symbol,
                    "expiry_date": expiry_date,
                },
            )

            if created:
                print(f"Created new future {symbol} expiring on {expiry_date}")

            count = 0

            for date, row in price_data.iterrows():
                FuturesPriceHistory.objects.update_or_create(
                    contract = future,
                    date = date.date(),
                    defaults = {
                        'open_price': row['Open'],
                        'high_price': row['High'],
                        'low_price': row['Low'],
                        'close_price': row['Close'],
                        'volume': int(row['Volume']) if pd.notna(row['Volume']) else None,
                    }
                )
                count += 1
            print(f"{count} records updated")
        print("finish")

    @staticmethod
    def fix_expiry_date(value):
        try:
            return datetime.strptime(
                    value,
                    "%Y-%m-%d",
                ).date()
        except Exception as error:
            print(f"invalid format")
            
    @classmethod
    def parse_code(cls, symbol):
        '''
        Example : ESH26.CME -> root=ES, month = 3, year = 2026
        '''
        match = re.fullmatch(
            r"(?P<root>[A-Z]+)"
            r"(?P<month>[FGHJKMNQUVXZ])"
            r"(?P<year>\d{2})"
            r"(?:\.CME)?",
            symbol.strip().upper()
        )

        if not match:
            print(f"Invalid contract code")
        
        root_symbol = match.group("root")
        month_code = match.group("month")
        year = 2000 + int(match.group("year"))
        month = cls.FUTURES_MONTHS[month_code]
        
        return root_symbol, month_code, year, month

    #contracts usually expire on the third friday of the month
    @staticmethod
    def third_friday(year, month):
        friday_dates = [
            day
            for day in calendar.Calendar().itermonthdates(year, month)
            if day.month == month and day.weekday() == calendar.FRIDAY
        ]

        return friday_dates[2]

    @classmethod
    def get_expiry_dates(cls, symbol):
        root_symbol, month_code, year, month = cls.parse_code(symbol)
        if root_symbol == "ES":
            if month_code not in {"H", "M","U", "Z"}:
                print(f"Invalid month code for ES")

            return cls.third_friday(year,month) 



