import yfinance as yf

tickers = ["ESH26.CME",
"ESM26.CME",
"ESU26.CME",
"ESZ26.CME"]
for t in tickers:
    try:
        data = yf.download(t, period="5d", progress=False)
        print(f"{t}: {len(data)} rows")
    except Exception as e:
        print(f"{t}: FAILED")