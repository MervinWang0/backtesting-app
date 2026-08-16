# PennyWise

> A browser-based quantitative trading sandbox for multi-asset backtesting, paper trading, and Monte Carlo strategy stress testing.

![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-6.0-092E20?logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-4169E1?logo=postgresql&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-Interactive_charts-3F4F75?logo=plotly&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)

PennyWise brings the strategy-research workflow into one web application. Users can explore stored market data, manage simulated portfolios, configure technical strategies, inspect backtest results, and challenge a completed strategy against synthetic market paths.

The project was created by NUS students for **NUS Orbital 2026**.

> [!IMPORTANT]
> PennyWise is an educational research project. It does not connect to a live brokerage, execute real trades, or provide financial advice.

## Table of contents

- [Core features](#core-features)
- [User workflow](#user-workflow)
- [How the backtesting engine works](#how-the-backtesting-engine-works)
- [How the Monte Carlo simulator works](#how-the-monte-carlo-simulator-works)
- [Included strategies](#included-strategies)
- [Performance analytics](#performance-analytics)
- [Architecture](#architecture)
- [Getting started](#getting-started)
- [Loading market data](#loading-market-data)
- [Using PennyWise](#using-pennywise)
- [Testing and diagnostics](#testing-and-diagnostics)
- [Current limitations](#current-limitations)
- [Deployment notes](#deployment-notes)
- [Acknowledgements](#acknowledgements)

## Core features

- **Multi-asset backtesting** across equities, foreign exchange, and futures using daily OHLCV data stored in PostgreSQL.
- **Seven configurable strategies**, covering trend following, momentum, breakout, and mean-reversion approaches.
- **Event-driven execution** built around market, signal, order, and fill events.
- **Portfolio accounting** for long and short positions, realised and unrealised P&L, cash, exposure, leverage, commissions, and slippage.
- **Continuous futures support** with configurable contract stitching, contract multipliers, and position rollover handling.
- **Monte Carlo stress testing** using geometric Brownian motion with optional fat-tailed shocks, jump diffusion, and volatility-regime switching.
- **Interactive research output** with Plotly equity curves, OHLC charts, benchmark comparisons, and empirical metric distributions.
- **Paper trading** with authenticated accounts, atomic order processing, position tracking, cash balances, and trade history.
- **Persistent run history** for backtest configuration, fills, daily equity, positions, and VOO benchmark records.
- **Deployment tooling** through Gunicorn, WhiteNoise, Docker, and a PostgreSQL-compatible `DATABASE_URL`.

## User workflow

The application supports two connected workflows: simulated portfolio management and strategy research. A completed backtest produces the `run_id` used to open the Monte Carlo simulator with the same strategy configuration.

```mermaid
flowchart TD
    A[Open PennyWise] --> B{Existing account?}
    B -- No --> C[Register]
    B -- Yes --> D[Log in]
    C --> E[Dashboard]
    D --> E

    E --> F{Choose a workflow}

    F -- Paper trading --> G[Create or select a paper account]
    G --> H[Search the stored stock universe]
    H --> I[Inspect price history and OHLC chart]
    I --> J[Submit a buy or sell order]
    J --> K[Review cash, positions, P&L, and trade history]
    K --> H

    F -- Strategy research --> L[Open the backtester]
    L --> M[Choose asset class and ticker]
    M --> N[Choose a strategy and its parameters]
    N --> O[Set dates, capital, signal strength, commission, and slippage]
    O --> P[Run the backtest]
    P --> Q[Inspect the equity curve, metrics, exposure, and benchmark]
    Q --> R{Stress-test this run?}
    R -- No --> N
    R -- Yes --> S[Open Monte Carlo simulator]
    S --> T[Choose simulation count and market components]
    T --> U[Compare simulated paths and metric percentiles]
    U --> T
```

## How the backtesting engine works

PennyWise uses a shared FIFO event queue to keep data access, signal generation, order creation, execution, and accounting separate. Each trading date is processed to completion before the engine advances its clock.

```mermaid
flowchart TD
    A[Backtest form POST] --> B[Validate and normalise parameters]
    B --> C[Create DatabaseDataLoader]
    C --> D[Load OHLCV bars and build a unified timeline]
    D --> E[Create strategy, execution handler, and portfolio]

    subgraph LOOP[Daily event loop]
        F[Advance to next trading date] --> G[Publish MarketEvent]
        G --> H{Futures roll day?}
        H -- Yes --> I[Close expiring contract and open next contract]
        H -- No --> J[Generate strategy signal]
        I --> J
        J --> K[SignalEvent]
        K --> L[Portfolio calculates target position]
        L --> M[OrderEvent]
        M --> N[Execution applies bar price, slippage, and commission]
        N --> O[FillEvent]
        O --> P[Update cash, holdings, average price, and realised P&L]
        P --> Q{Event queue empty?}
        Q -- No --> J
        Q -- Yes --> R[Record equity, positions, exposure, and benchmark]
    end

    E --> F
    R --> S{More dates?}
    S -- Yes --> F
    S -- No --> T[Build BacktestResult]
    T --> U[Calculate performance metrics and equity graph]
    T --> V[Bulk-persist fills, equity, positions, and benchmark records]
    U --> W[Return metrics, graph HTML, and run ID]
    V --> W
```

### Engine responsibilities

| Component | Responsibility |
| --- | --- |
| `DatabaseDataLoader` | Reads stock, forex, or continuous-futures bars from PostgreSQL and exposes a common timeline. |
| `Strategy` implementations | Convert the current and historical bars into `LONG`, `SHORT`, or `EXIT` signals. |
| `Portfolio` | Sizes positions, creates orders, converts currencies, and tracks cash, exposure, P&L, and holdings. |
| `ExecutionLoader` | Converts market orders into fills and applies proportional commission and slippage. |
| `DatabasePortfolio` | Saves completed backtest state and daily records in bulk. |
| `MCSPortfolio` | Reuses portfolio logic for simulations without writing every synthetic run to the database. |
| `ContinuousFuturesSeriesBuilder` | Stitches dated contracts and marks rollover transitions for futures simulations. |
| `BacktestResult` | Exposes the equity history, closed trades, Plotly chart, and performance metrics. |

## How the Monte Carlo simulator works

The simulator does more than shuffle historical returns. It calibrates a geometric Brownian motion process to historical log returns and can layer three market-behaviour components onto each synthetic path:

- **Student's t shocks** replace normal innovations with standardised fat-tailed draws.
- **Regime switching** fits a two-state Gaussian hidden Markov model and samples changing drift and volatility regimes.
- **Jump diffusion** adds Poisson-distributed jumps and applies the corresponding drift correction.

Each synthetic price history is passed through the same event-driven backtest used by the original run. This measures strategy robustness rather than only forecasting an asset's terminal price.

```mermaid
flowchart TD
    A[Completed BacktestRun ID] --> B[Restore dates, ticker, strategy, costs, and parameters]
    B --> C[Run the original backtest as the baseline]
    B --> D[Load historical close prices]
    D --> E[Calculate historical log-return drift and volatility]
    E --> F[Initialise GBM parameters]

    F --> G{Student's t enabled?}
    G -- Yes --> H[Replace normal shocks with scaled t shocks]
    G -- No --> I[Keep normal shocks]
    H --> J{Regime switching enabled?}
    I --> J
    J -- Yes --> K[Fit two-state Gaussian HMM and sample drift-volatility states]
    J -- No --> L[Keep static drift and volatility]
    K --> M{Jump diffusion enabled?}
    L --> M
    M -- Yes --> N[Sample Poisson jumps and jump sizes]
    M -- No --> O[Use zero jump contribution]
    N --> P[Generate a synthetic GBM close-price path]
    O --> P
    P --> Q[Reconstruct OHLC bars using historical relative spreads]
    Q --> R[Load bars through MCSDataLoader]
    R --> S[Run the same strategy through the backtest engine]
    S --> T[Collect return, risk, and trading metrics]
    T --> U{Requested simulations complete?}
    U -- No --> G
    U -- Yes --> V[Build empirical distributions for every metric]
    C --> V
    V --> W[Plot original and simulated equity paths]
    V --> X[Report original, mean, median, variance, range, and percentiles]
```

To keep the response and chart manageable, all simulations contribute to the metric distributions while the interface retains at most the first 100 synthetic equity paths, alongside the original run, for plotting.

## Included strategies

| Strategy | Signal logic | Main parameters |
| --- | --- | --- |
| Moving Average Crossover | Goes long or short when the short simple moving average crosses the long simple moving average. | `mac_short_window`, `mac_long_window` |
| Mean Reversion | Combines RSI, Bollinger Bands, and rolling z-score signals using majority or unanimous logic. | `rsi_window`, `bollinger_window`, `z_window`, RSI/z-score thresholds, `mean_reversion_logic` |
| MACD | Trades crossovers between the MACD line and its signal EMA. | `macd_short`, `macd_medium`, `macd_long` |
| Breakout | Trades closes outside lagged Donchian-channel support or resistance. | `donchian_window` |
| Momentum | Filters MACD crossover signals with RSI and a 21-period EMA trend check. | MACD windows, `rsi_window` |
| Rate of Change | Enters on a negative-to-positive ROC crossover with a moving-average filter and exits on reversal. | `roc_window` |
| Stochastic Oscillator | Trades transitions out of overbought or oversold `%K` states. | `stoc_window` |

All strategies accept a signal `strength` between 0 and 1. The portfolio combines that confidence with its risk budget, default stop distance, per-position exposure limit, and portfolio gross-leverage limit to calculate a target position.

## Performance analytics

Every `BacktestResult` calculates:

- Total return
- Mean daily return
- Compound annual growth rate (CAGR)
- Annualised volatility
- Sharpe ratio
- Maximum drawdown
- Closed-trade win rate

Database-backed runs additionally retain daily cash, holdings value, equity, realised and unrealised P&L, commission, gross and net exposure, leverage, per-ticker positions, fills, and a buy-and-hold **VOO** benchmark.

The Monte Carlo output turns each performance metric into an empirical distribution containing the original result, mean, median, variance, minimum, maximum, and the 10th, 25th, 50th, 75th, and 90th percentiles.

## Architecture

```text
backtesting-app/
├── README.md
└── Orbital/
    ├── manage.py
    ├── requirements.txt
    ├── Dockerfile
    ├── compose.yaml
    ├── Orbital/
    │   ├── settings.py              # Django, PostgreSQL, WhiteNoise
    │   └── urls.py                  # Project-level routing
    └── base/
        ├── engine/
        │   ├── backtest.py          # Event loop and BacktestResult
        │   ├── data_loader.py       # Database and in-memory loaders
        │   ├── strategy.py          # Seven strategy implementations
        │   ├── portfolio.py         # Sizing, accounting, and persistence
        │   ├── execution.py         # Fill, commission, and slippage model
        │   ├── events.py            # Market, signal, order, and fill events
        │   ├── performance.py       # Return and risk analytics
        │   ├── graph.py             # Plotly visualisations
        │   ├── distribution.py      # Empirical distribution statistics
        │   └── monte_carlo_simulation.py
        ├── futures/
        │   └── continuous_series.py # Contract stitching and roll metadata
        ├── management/commands/     # Yahoo Finance ingestion and futures build
        ├── services/                # Transactional paper-order service
        ├── views/                   # Dashboard, backtest, and Monte Carlo endpoints
        ├── templates/               # Django-rendered pages
        ├── static/                  # JavaScript, CSS, and strategy images
        ├── tests/                   # Automated and analytical checks
        ├── models.py                # Market, run, portfolio, and paper models
        └── urls.py                  # Application routes
```

### Technology stack

| Layer | Technology |
| --- | --- |
| Web application | Python 3.14, Django 6 |
| Data and statistics | pandas, NumPy, SciPy, scikit-learn, hmmlearn |
| Market data | yfinance and Yahoo Finance |
| Database | PostgreSQL via psycopg and `dj-database-url` |
| Front end | Django templates, vanilla JavaScript, HTML, CSS |
| Visualisation | Plotly |
| Serving and static files | Gunicorn and WhiteNoise |
| Packaging and deployment | Docker / Docker Compose |

### Primary data flow

1. Management commands ingest Yahoo Finance data into PostgreSQL.
2. Django views validate browser input and create the requested engine objects.
3. The data loader presents asset-specific rows as a shared `Bar` representation.
4. Strategies, portfolio logic, and execution communicate through event dataclasses.
5. Completed database backtests save their run, daily records, fills, positions, and benchmark.
6. Plotly figures and metric dictionaries are returned to the browser as JSON-rendered results.

## Getting started

### Prerequisites

- Git
- Python 3.14, matching the included Docker image
- PostgreSQL
- Optional: Docker Desktop or another Docker Engine installation

### 1. Clone the repository

```bash
git clone https://github.com/MervinWang0/backtesting-app.git
cd backtesting-app/Orbital
```

### 2. Create a virtual environment

macOS or Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Configure PostgreSQL

Create an empty PostgreSQL database, then add a `.env` file beside `manage.py`:

```dotenv
DATABASE_URL=postgresql://USER:PASSWORD@127.0.0.1:5432/DATABASE_NAME
```

Do not commit `.env` or real database credentials.

### 5. Initialise the application

```bash
python manage.py migrate
python manage.py createsuperuser
```

Creating a superuser is optional, but it provides access to `/admin/` for inspecting market and backtest records.

### 6. Seed the minimum stock data

The backtest results view expects VOO benchmark history for the selected date range. Load it together with at least one research ticker:

```bash
python manage.py load_stock_data --symbol VOO --period 10y --interval 1d
python manage.py load_stock_data --symbol AAPL --period 10y --interval 1d
```

### 7. Start the development server

```bash
python manage.py runserver 127.0.0.1:8000
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

### Docker

The included Compose file defines the web service but does not start PostgreSQL. Supply a reachable PostgreSQL `DATABASE_URL` when running the image:

```bash
docker build -t pennywise .
docker run --rm -e DATABASE_URL="postgresql://USER:PASSWORD@HOST:5432/DATABASE_NAME" pennywise python manage.py migrate
docker run --rm -p 8000:8000 -e DATABASE_URL="postgresql://USER:PASSWORD@HOST:5432/DATABASE_NAME" pennywise
```

If PostgreSQL runs on the Docker host, use the host address exposed by your Docker installation rather than `127.0.0.1` inside the container.

## Loading market data

Market data must exist in PostgreSQL before a backtest runs. The application includes these Django management commands:

| Asset | Example | Behaviour |
| --- | --- | --- |
| Single stock or ETF | `python manage.py load_stock_data --symbol AAPL --period 5y --interval 1d` | Downloads and upserts OHLCV history for one symbol. |
| S&P 500 universe | `python manage.py load_stock_data --period 1y --interval 1d` | Reads the current S&P 500 list and loads every constituent; this can take time. |
| Default forex universe | `python manage.py load_forex_data --period 5y --interval 1d` | Loads the ten configured major/cross currency pairs. |
| Single forex pair | `python manage.py load_forex_data --symbol EURUSD --period 5y --interval 1d` | Normalises the symbol to Yahoo Finance's `=X` convention. |
| Continuous futures source | `python manage.py load_futures_data --symbol MCL=F --period 5y --interval 1d` | Downloads a root future and stores dated contract segments with multipliers. |
| Specific futures contract | `python manage.py load_futures_data --symbol ESM26.CME --period 1y --interval 1d` | Parses the contract month code and stores its expiry and prices. |
| Stitched futures series | `python manage.py build_continuous_futures --root-symbol MCL --roll-days 5 --start 2023-01-01 --end 2025-01-01` | Builds the continuous series and roll metadata consumed by the futures loader. |

Yahoo Finance availability and retention rules vary by symbol and interval. If a requested date range returns no rows, try a shorter period or daily interval.

## Using PennyWise

### Paper trading

1. Register or log in.
2. Create a paper account with a name and starting balance.
3. Search the dashboard for a stored stock and open its detail page.
4. Select a paper account and submit a buy or sell quantity.
5. Review open positions, cash, realised P&L, and trade history in **Portfolio**.

Paper orders use the latest stored close price. Order creation, account balance changes, position updates, and trade creation are wrapped in a database transaction with row-level locks.

### Backtesting

1. Open **Backtest** from the navigation bar.
2. Select a strategy. Only that strategy's relevant parameters are displayed.
3. Choose `STOCK`, `FOREX`, or `FUTURES`, then select one or more available tickers.
4. Set the date range, starting capital, signal strength, commission percentage, and slippage.
5. Run the backtest and inspect the equity curve and metrics.
6. Use the generated run ID to inspect saved daily records or open the Monte Carlo simulator.

### Monte Carlo simulation

1. Complete a stock backtest first and choose **View Monte Carlo Simulation**.
2. Select the number of simulations.
3. Enable any combination of jump diffusion, regime switching, and Student's t shocks.
4. Configure the parameters revealed by those choices.
5. Run the simulation and compare the original equity curve with the synthetic paths.
6. Use the percentile table to assess how stable the strategy's return and risk metrics are across alternate market histories.

## Testing and diagnostics

The repository contains a mixture of pytest-style checks and analytical runner scripts for the engine, strategies, performance calculations, futures rollover, graphs, and Monte Carlo components.

Run test discovery from the Django project directory:

```bash
python -m pytest base/tests -v
```

Database-backed checks require `DATABASE_URL` and suitable seeded market history. The top-level `test.py`, `test_forex.py`, and `test_futures.py` files are diagnostic runners that can be executed directly when working on the corresponding engine paths.

## Current limitations

- The Monte Carlo implementation is currently designed around a **single stock ticker**. It does not model cross-asset correlations or multi-ticker covariance.
- Simulations run synchronously inside the web request; large simulation counts can reach the server timeout.
- Historical data is sourced from Yahoo Finance and is subject to upstream coverage, delay, and retention limits.
- Transaction costs use constant proportional commission and slippage rather than order-book liquidity, bid-ask spread, latency, or market impact.
- Paper trading currently executes equities against the latest stored close and does not connect to live quotes or a brokerage.
- Results are only as reliable as the stored data and model assumptions; synthetic paths are scenarios, not forecasts.
- Several test files are analytical development harnesses rather than isolated, database-free unit tests.

## Deployment notes

The Docker image serves Django with Gunicorn on port `8000` and collects static assets for WhiteNoise during the build.

Before deploying beyond a controlled demo environment:

- Move `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, and trusted-origin configuration to environment variables.
- Run `python manage.py check --deploy` and review every warning.
- Apply migrations before starting the web process.
- Use a managed PostgreSQL database with TLS, backups, and restricted credentials.
- Add request authentication/authorisation checks to every user-specific route.
- Move long-running Monte Carlo work to a background task queue if higher simulation counts are required.

## Acknowledgements

- [Django](https://www.djangoproject.com/) for the web framework and ORM.
- [Plotly](https://plotly.com/python/) for interactive financial and equity charts.
- [yfinance](https://github.com/ranaroussi/yfinance) and Yahoo Finance for historical market-data access.
- [hmmlearn](https://hmmlearn.readthedocs.io/) for Gaussian hidden Markov models.
- NUS Orbital for the project framework and milestone programme.

---

Built as an educational quantitative-finance project for **NUS Orbital 2026**.
