from django.core.management.base import BaseCommand
from base.models import FuturesContract, FuturesPriceHistory
from datetime import datetime, date, timedelta
import pandas as pd
import yfinance as yf
import re
import calendar

class Command(BaseCommand):
    help = "Load future data through yahoo finance"

    FUTURES_MONTHS = {
        "F": 1, "G": 2, "H": 3, "J": 4, "K": 5, "M": 6,
        "N": 7, "Q": 8, "U": 9, "V": 10, "X": 11, "Z": 12,
    }

    DEFAULT_FUTURES = {
    "ES=F":  {"root_symbol": "ES"},
    "MES=F": {"root_symbol": "MES"},
    "NQ=F":  {"root_symbol": "NQ"},
    "MNQ=F": {"root_symbol": "MNQ"},
    "YM=F":  {"root_symbol": "YM"},
    "MYM=F": {"root_symbol": "MYM"},
    "RTY=F": {"root_symbol": "RTY"},
    "M2K=F": {"root_symbol": "M2K"},
    "CL=F":  {"root_symbol": "CL"},
    "MCL=F": {"root_symbol": "MCL"},
    "NG=F":  {"root_symbol": "NG"},
    "GC=F":  {"root_symbol": "GC"},
    "MGC=F": {"root_symbol": "MGC"},
    "SI=F":  {"root_symbol": "SI"},
    "SIL=F": {"root_symbol": "SIL"},
    "ZB=F":  {"root_symbol": "ZB"},
    "ZN=F":  {"root_symbol": "ZN"},
    "ZF=F":  {"root_symbol": "ZF"},
    "ZT=F":  {"root_symbol": "ZT"},
}

    FUTURES_MULTIPLIERS = {
        "ES": 50.0, "MES": 5.0, "NQ": 20.0, "MNQ": 2.0,
        "YM": 5.0, "MYM": 0.5, "RTY": 50.0, "M2K": 5.0,
        "CL": 1000.0, "MCL": 100.0, "NG": 10000.0,
        "GC": 100.0, "MGC": 10.0, "SI": 5000.0, "SIL": 1000.0,
        "ZB": 1000.0, "ZN": 1000.0, "ZF": 1000.0, "ZT": 2000.0,
    }

    def add_arguments(self, parser):
        parser.add_argument("--symbol",
                             type=str,
                             help="Enter futures symbol, e.g., ES=F or ESH26.CME")
        
        parser.add_argument("--root-symbol",
                             type=str, required=False,
                             help="Root futures symbol, e.g., ES")
        
        parser.add_argument("--expiry-date",
                            type=str, required=False,
                            help="Expiry date in YYYY-MM-DD format")
        
        parser.add_argument("--period",
                            type=str,
                            default="1d",
                            help="Enter desired period, e.g., 1yr, 6mo")
        
        parser.add_argument("--interval", type=str, default="1d", help="Enter desired interval, e.g., 1d, 1h")

    def handle(self, *args, **options):
        symbol = options.get("symbol")
        override_expiry = options.get("expiry_date")
        period = options.get("period")
        interval = options.get("interval")

        if symbol:
            symbol_to_process = [symbol.strip().upper()]
        else:
            symbol_to_process = list(self.DEFAULT_FUTURES.keys())

        for sym in symbol_to_process:
            if sym.endswith("=F"):
                self.process_continuous_contract(sym, period, interval)
            else:
                self.process_specific_contract(sym, period, interval, override_expiry)
                
        self.stdout.write(self.style.SUCCESS("Finished processing all symbols."))

    def process_continuous_contract(self, sym, period, interval):
        root_symbol = sym[:-2]
        multiplier = self.FUTURES_MULTIPLIERS.get(root_symbol, 1.0)
        
        self.stdout.write(f"Processing continuous contract {sym}")
        
        try:
            price_data = yf.download(
                sym, period=period, 
                interval=interval, 
                progress=False,
                auto_adjust=False, 
                group_by="column", 
                threads=False, 
                multi_level_index=False,
            )
        except Exception as error:
            self.stdout.write(self.style.ERROR(f"Failed to download {sym}: {error}"))
            return

        if isinstance(price_data.columns, pd.MultiIndex):
            price_data.columns = price_data.columns.get_level_values(0)
            
        if price_data.empty:
            self.stdout.write(f'No data for {sym}, continuing')
            return

        # ES expires in Mar, Jun, Sep, Dec
        exp_months = [3, 6, 9, 12]
        
        #To implement others
        if root_symbol in ["CL", "MCL", "NG"]:
            exp_months = list(range(1, 13))
        elif root_symbol in ["GC", "MGC", "SI", "SIL"]:
            exp_months = [2, 4, 6, 8, 10, 12] 

        start_date = price_data.index.min().date()
        end_date = price_data.index.max().date()

        years = range(start_date.year, end_date.year + 1)
        expiry_dates = []
        for year in years:
            for month in exp_months:
                exp_date = self.third_friday(year, month)
                if start_date <= exp_date <= end_date + timedelta(days=90):
                    expiry_dates.append(exp_date)
                    
        expiry_dates.sort()

        def get_expiry_for_date(day):
            for exp in expiry_dates:
                if day <= exp:
                    return exp
            year, month = day.year, day.month
            while True:
                if month in exp_months:
                    exp = self.third_friday(year, month)
                    if exp >= day:
                        return exp
                month += 1
                if month > 12:
                    month = 1
                    year += 1

        price_data['contract_expiry'] = [get_expiry_for_date(day.date()) for day in price_data.index]

        for exp_date, group in price_data.groupby('contract_expiry'):
            month, year = exp_date.month, exp_date.year
            month_code = {v: k for k, v in self.FUTURES_MONTHS.items()}.get(month)
            
            if not month_code:
                continue 
                
            contract_code = f"{root_symbol}{month_code}{str(year)[2:]}"
            
            future, created = FuturesContract.objects.update_or_create(
                contract_code=contract_code,
                defaults={
                    "root_symbol": root_symbol,
                    "name": f"{sym} section for {contract_code}",
                    "expiry_date": exp_date,
                    "tick_multiplier": multiplier,
                },
            )

            if created:
                self.stdout.write(f"Created continuous segment {contract_code} expiring on {exp_date}")

            count = 0
            for date, row in group.iterrows():
                FuturesPriceHistory.objects.update_or_create(
                    contract=future,
                    date=date.date(),
                    defaults={
                        'open_price': row['Open'],
                        'high_price': row['High'],
                        'low_price': row['Low'],
                        'close_price': row['Close'],
                        'volume': int(row['Volume']) if pd.notna(row['Volume']) else None,
                    }
                )
                count += 1
            self.stdout.write(f"{count} records updated for {contract_code}")

    #For specific contracts like ESM26.CME
    def process_specific_contract(self, sym, period, interval, override_expiry=None):
        try:
            root_symbol, month_code, year, month = self.parse_code(sym)
        except ValueError as e:
            self.stdout.write(self.style.ERROR(f"Error parsing {sym}: {e}"))
            return

        multiplier = self.FUTURES_MULTIPLIERS.get(root_symbol, 1.0)
        infered_expiry = self.get_expiry_dates(sym)
        
        if override_expiry:
            final_expiry = self.fix_expiry_date(override_expiry)
            if final_expiry and final_expiry != infered_expiry:
                self.stdout.write(self.style.WARNING("Mismatch in expiry dates"))
        else:
            final_expiry = infered_expiry

        try:
            price_data = yf.download(
                sym, period=period, interval=interval, progress=False,
                auto_adjust=False, group_by="column", threads=False, multi_level_index=False,
            )
        except Exception as error:
            self.stdout.write(self.style.ERROR(f"Failed to download {sym}: {error}"))
            return

        if isinstance(price_data.columns, pd.MultiIndex):
            price_data.columns = price_data.columns.get_level_values(0)
            
        if price_data.empty:
            self.stdout.write(f'No data for {sym}, continuing')
            return

        future, created = FuturesContract.objects.update_or_create(
            contract_code=sym,
            defaults={
                "root_symbol": root_symbol,
                "name": sym,
                "expiry_date": final_expiry,
                "tick_multiplier": multiplier,
            },
        )

        if created:
            self.stdout.write(f"Created new future {sym} expiring on {final_expiry}")

        count = 0
        for date, row in price_data.iterrows():
            FuturesPriceHistory.objects.update_or_create(
                contract=future,
                date=date.date(),
                defaults={
                    'open_price': row['Open'],
                    'high_price': row['High'],
                    'low_price': row['Low'],
                    'close_price': row['Close'],
                    'volume': int(row['Volume']) if pd.notna(row['Volume']) else None,
                }
            )
            count += 1
        self.stdout.write(f"{count} records updated for {sym}")

    @staticmethod
    def fix_expiry_date(value):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except Exception:
            print("Invalid date format. Use YYYY-MM-DD.")
            
    @classmethod
    def parse_code(cls, symbol):
        match = re.fullmatch(
            r"(?P<root>[A-Z]+)(?P<month>[FGHJKMNQUVXZ])(?P<year>\d{2})(?:\.CME)?",
            symbol.strip().upper()
        )
        if not match:
            raise ValueError(f"Invalid contract code: {symbol}")
        
        root_symbol = match.group("root")
        month_code = match.group("month")
        year = 2000 + int(match.group("year"))
        month = cls.FUTURES_MONTHS[month_code]
        
        return root_symbol, month_code, year, month

    @staticmethod
    def third_friday(year, month):
        friday_dates = [
            day for day in calendar.Calendar().itermonthdates(year, month)
            if day.month == month and day.weekday() == calendar.FRIDAY
        ]
        return friday_dates[2]

    @classmethod
    def get_expiry_dates(cls, symbol):
        root_symbol, month_code, year, month = cls.parse_code(symbol)
        if root_symbol == "ES":
            if month_code not in {"H", "M", "U", "Z"}:
                raise ValueError(f"Invalid month code for ES")
        return cls.third_friday(year, month)