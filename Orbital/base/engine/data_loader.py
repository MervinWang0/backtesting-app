# First I'm going to get the data using yfinance
# Then I'm going to store the data into tables using the database
# THen I'm going to take the data from the tables and put them into backtest


import yfinance as yf 

data = yf.Ticker("AAPL")
print(data.history(period='1mo'))


