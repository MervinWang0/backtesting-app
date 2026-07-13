from django.core.management.base import BaseCommand, CommandError
from base.models import FuturesContract, FuturesPriceHistory, ContinuousFuturesPriceHistory, ContinuousFuturesSeries
from base.futures.continuous_series import ContinuousFuturesSeriesBuilder
from datetime import datetime
import pandas as pd
import requests
from io import StringIO
import yfinance as yf


class Command(BaseCommand):
    help = "Builds a continuous futures series"

    def add_arguments(self, parser):
        parser.add_argument(
            "--root-symbol",
            type=str,
            required=True,
            help="Enter root symbol for futures, eg ES"
        )

        parser.add_argument(
            "--roll-days",
            type=int,
            default=5,
            help="Add trading days before expiry to roll"
        )

        parser.add_argument(
            "--start",
            type=str,
            help="Enter start date in YYYY-MM-DD format"
        )

        parser.add_argument(
            "--end",
            type=str,
            help="Add end date in YYYY-MM-DD format"
        )

    def handle(self, *args, **options):
        root_symbol = options.get("root_symbol").strip().upper()
        roll_days = options.get("roll_days")
        start_date = self.fix_date(options.get("start"))
        end_date = self.fix_date(options.get("end"))

        series, created = (
            ContinuousFuturesSeries.objects.get_or_create(
                contract_symbol = root_symbol,
                contract_index = 1,
                rollover_rule = "DAYS_BEFORE_EXPIRY",
                roll_days = roll_days,
                adjustment_method = "BACK_ADJUSTED",
        ))

        if created:
            print(f"Creating continuous series for {root_symbol}")

        builder = ContinuousFuturesSeriesBuilder(series)

        try:
            price_count = builder.build(start_date=start_date, end_date=end_date)
        
        except RuntimeError as error:
            raise CommandError(f"error because of {error}") from error
        
        print(f"Success, build series for {root_symbol} with {price_count} price rows")

    @staticmethod
    def fix_date(value):
        try:
            return datetime.strptime(
                    value,
                    "%Y-%m-%d",
                ).date()
        except Exception as error:
            print(f"invalid format")

