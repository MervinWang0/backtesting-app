from django.core.management.base import BaseCommand
from base.models import Stock, StockPriceHistory
import yfinance as yf
from datetime import datetime
import pandas as pd
import requests
from io import StringIO


class Command(BaseCommand):
    
    help = 'Loads historical data for a list of stocks through yfinance'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--symbol',
            type=str,
            help='Enter a specific symbol'
        )
        parser.add_argument(
            '--period',
            type=str,
            default='1mo',
            help='Specify historical period(eg, 1y, 6mo)'
        )
        parser.add_argument(
            '--interval',
            type=str,
            default='1d',
            help='Specify interval period'
        )

    def handle(self, *args, **options):
        symbol = options.get('symbol')
        period = options.get('period')
        interval = options.get('interval')

        stocks = [] 
        
        if symbol:
            stocks.append((symbol.upper(),symbol.upper()))
        else:
            url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
            headers = {'User-Agent': 'Mozilla/5.0'}
            try:
                response = requests.get(url, headers=headers, timeout=20)
                response.raise_for_status()
                df = pd.read_html(StringIO(response.text))[0]
                stocks = [(row['Symbol'].replace('.','-'),row['Security']) for _,row in df.iterrows()]
            except Exception as e:
                print(f'error loading {e}')
                return
        
        for symbol,name in stocks:
            stock, created = Stock.objects.get_or_create(ticker =symbol,defaults ={'name':name})
            if created:
                print(f'created new stock: {symbol} - {name}')
            try:
                #data = yf.download(symbol, period=period, interval=interval,progress=False)
                data = yf.download(
                    symbol,
                    period=period,
                    interval=interval,
                    progress=False,
                    auto_adjust=False,
                    group_by='column'
                )

                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = data.columns.get_level_values(0)
                if data.empty:
                    print(f'no data for {symbol}, continuing')
                    continue

                count = 0

                for date, row in data.iterrows():
                    StockPriceHistory.objects.update_or_create(
                        stock=stock,
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
                print(f'{symbol}: {count} records updated')
            except Exception as e:
                print(f'error fetching data for {symbol} : {e}')
        print('finish')