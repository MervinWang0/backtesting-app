from engine.performance import *
import pytest

@pytest.fixture
def sample_trades():
    return pd.DataFrame({
        'date': pd.to_datetime([
            '2023-01-01',
            '2023-01-02',
            '2023-01-03',
            '2023-01-04'
        ]),
        'pnl': [100.0, -50.0, 200.0, -50.0]
    })
 
INITIAL_CAPITAL = 1000.0
RISK_FREE_RATE = 0.0

# calculate_total_returns

def test_total_returns_basic(sample_trades):
    result = calculate_total_returns(sample_trades, INITIAL_CAPITAL)
    assert result == pytest.approx(0.2), f"Expected 0.2 but got {result}"

def test_total_returns_all_wins():
    trades = pd.DataFrame({
        'date': pd.to_datetime(['2023-01-01', '2023-01-02']),
        'pnl': [100.0, 200.0]
    })
    result = calculate_total_returns(trades, INITIAL_CAPITAL)
    assert result == pytest.approx(0.3)
 
def test_total_returns_all_losses():
    trades = pd.DataFrame({
        'date': pd.to_datetime(['2023-01-01', '2023-01-02']),
        'pnl': [-100.0, -200.0]
    })
    result = calculate_total_returns(trades, INITIAL_CAPITAL)
    assert result == pytest.approx(-0.3)

def test_total_returns_breakeven():
    trades = pd.DataFrame({
        'date': pd.to_datetime(['2023-01-01', '2023-01-02']),
        'pnl': [100.0, -100.0]
    })
    result = calculate_total_returns(trades, INITIAL_CAPITAL)
    assert result == pytest.approx(0.0)
 
# calculate_win_rate
 
def test_win_rate_basic(sample_trades):
    result = calculate_win_rate(sample_trades)
    assert result == pytest.approx(0.5), f"Expected 0.5 but got {result}"
 
def test_win_rate_all_wins():
    trades = pd.DataFrame({
        'date': pd.to_datetime(['2023-01-01', '2023-01-02']),
        'pnl': [100.0, 200.0]
    })
    result = calculate_win_rate(trades)
    assert result == pytest.approx(1.0)
 
def test_win_rate_all_losses():
    trades = pd.DataFrame({
        'date': pd.to_datetime(['2023-01-01', '2023-01-02']),
        'pnl': [-100.0, -200.0]
    })
    result = calculate_win_rate(trades)
    assert result == pytest.approx(0.0)
 
def test_win_rate_single_trade_win():
    trades = pd.DataFrame({
        'date': pd.to_datetime(['2023-01-01']),
        'pnl': [100.0]
    })
    result = calculate_win_rate(trades)
    assert result == pytest.approx(1.0)
 
 
# calculate_profit_factor
 
def test_profit_factor_basic(sample_trades):
    result = calculate_profit_factor(sample_trades)
    # gross_profit = 100 + 200 = 300
    # gross_loss   = abs(-50 + -50) = 100
    # profit_factor = 300 / 100 = 3.0
    assert result == pytest.approx(3.0), f"Expected 3.0 but got {result}"
 
def test_profit_factor_is_positive(sample_trades):
    result = calculate_profit_factor(sample_trades)
    assert result > 0, "Profit factor should always be positive"
 
def test_profit_factor_breakeven():
    trades = pd.DataFrame({
        'date': pd.to_datetime(['2023-01-01', '2023-01-02']),
        'pnl': [100.0, -100.0]
    })
    result = calculate_profit_factor(trades)
    assert result == pytest.approx(1.0)
 
 
# calculate_win_loss_ratio
 
def test_win_loss_ratio_basic(sample_trades):
    result = calculate_win_loss_ratio(sample_trades)
    # avg_win  = (100 + 200) / 2 = 150
    # avg_loss = (-50 + -50) / 2 = -50
    # ratio    = abs(150 / -50) = 3.0
    assert result == pytest.approx(3.0), f"Expected 3.0 but got {result}"
 
def test_win_loss_ratio_is_positive(sample_trades):
    result = calculate_win_loss_ratio(sample_trades)
    assert result > 0, "Win/loss ratio should always be positive"
 
 
# calculate_expectancy
 
def test_expectancy_basic(sample_trades):
    result = calculate_expectancy(sample_trades)
    # win_rate  = 0.5
    # loss_rate = 0.5
    # avg_win   = 150
    # avg_loss  = 50 (absolute)
    # expectancy = (0.5 * 150) - (0.5 * 50) = 75 - 25 = 50
    assert result == pytest.approx(50.0), f"Expected 50.0 but got {result}"
 
def test_expectancy_is_positive_for_good_strategy(sample_trades):
    result = calculate_expectancy(sample_trades)
    assert result > 0, "Expectancy should be positive for a profitable strategy"
 
 
# calculate_max_drawdown
 
def test_max_drawdown_basic(sample_trades):
    result = calculate_max_drawdown(sample_trades, INITIAL_CAPITAL)
    # equity_curve = [1100, 1050, 1250, 1200]
    # peak         = [1100, 1100, 1250, 1250]
    # drawdown     = [0, 50/1100, 0, 50/1250]
    # max_drawdown = 50/1100
    assert result == pytest.approx(50 / 1100, rel=1e-3), f"Expected {50/1100} but got {result}"
 
def test_max_drawdown_is_between_0_and_1(sample_trades):
    result = calculate_max_drawdown(sample_trades, INITIAL_CAPITAL)
    assert 0 <= result <= 1, "Max drawdown should always be between 0 and 1"
 
def test_max_drawdown_only_wins():
    # If equity only goes up, drawdown should be 0
    trades = pd.DataFrame({
        'date': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03']),
        'pnl': [100.0, 200.0, 300.0]
    })
    result = calculate_max_drawdown(trades, INITIAL_CAPITAL)
    assert result == pytest.approx(0.0)
 
 
# calculate_sharpe_ratio
 
def test_sharpe_ratio_basic(sample_trades):
    result = calculate_sharpe_ratio(sample_trades, INITIAL_CAPITAL, RISK_FREE_RATE)
    # daily_returns = [0.1, -0.05, 0.2, -0.05]
    # mean = 0.05, std ≈ 0.12247
    # sharpe = (0.05 / 0.12247) * sqrt(252) ≈ 6.48
    assert result == pytest.approx(6.48, rel=1e-2), f"Expected ~6.48 but got {result}"
 
def test_sharpe_ratio_higher_risk_free_rate_lowers_sharpe(sample_trades):
    sharpe_low_rf  = calculate_sharpe_ratio(sample_trades, INITIAL_CAPITAL, 0.0)
    sharpe_high_rf = calculate_sharpe_ratio(sample_trades, INITIAL_CAPITAL, 0.05)
    assert sharpe_low_rf > sharpe_high_rf, "Higher risk free rate should lower Sharpe ratio"
 
 
# calculate_sortino_ratio
 
def test_sortino_ratio_basic():
    # Use trades with varied negative returns so std is non-zero
    trades = pd.DataFrame({
        'date': pd.to_datetime([
            '2023-01-01', '2023-01-02', '2023-01-03',
            '2023-01-04', '2023-01-05'
        ]),
        'pnl': [200.0, -100.0, 300.0, -50.0, 150.0]
    })
    result = calculate_sortino_ratio(trades, INITIAL_CAPITAL, RISK_FREE_RATE)
    assert isinstance(result, float), "Sortino ratio should return a float"
 
def test_sortino_is_greater_than_sharpe_for_asymmetric_returns():
    # When losses are small relative to gains, Sortino > Sharpe
    trades = pd.DataFrame({
        'date': pd.to_datetime([
            '2023-01-01', '2023-01-02', '2023-01-03',
            '2023-01-04', '2023-01-05'
        ]),
        'pnl': [500.0, -10.0, 400.0, -10.0, 300.0]
    })
    sharpe  = calculate_sharpe_ratio(trades, INITIAL_CAPITAL, RISK_FREE_RATE)
    sortino = calculate_sortino_ratio(trades, INITIAL_CAPITAL, RISK_FREE_RATE)
    assert sortino > sharpe, "Sortino should be greater than Sharpe when downside volatility is low"
 
 
# calculate_calmar_ratio
 
def test_calmar_ratio_is_positive_for_profitable_strategy(sample_trades):
    result = calculate_calmar_ratio(sample_trades, INITIAL_CAPITAL)
    assert result > 0, "Calmar ratio should be positive for a profitable strategy"


# calculate_metrics

def test_empty_trades_calculate_metrics():
    trades = pd.DataFrame()
    with pytest.raises(AssertionError):
        calculate_metrics(trades, INITIAL_CAPITAL, RISK_FREE_RATE)



