# First I'm going to get the data using yfinance
# Then I'm going to store the data into tables using the database

import yfinance as yf 

data = yf.Ticker("AAPL")
print(data.history(period='1mo'))