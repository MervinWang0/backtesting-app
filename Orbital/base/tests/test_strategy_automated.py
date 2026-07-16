# import pytest
# from queue import Queue
# from datetime import datetime
# from base.engine.strategy import (Strategy, MovingAverageCross, MeanReversion,
# )
# from base.engine.data_loader import DatabaseDataLoader

# -----------------------------------------------------------------------------

                        # Initial Setup

# -----------------------------------------------------------------------------
# Initialize some dates
# start_date = datetime.fromisoformat("2021-05-24").date()
# end_date = datetime.fromisoformat("2022-05-24").date()
# @pytest.fixture 
# def sample_data_loader_single_stock():
#     '''
#     Creates a simple test case of a data loader, for one year for Apple
#     '''
#     return DatabaseDataLoader(events=Queue(), tickers=['AAPL'],
#                               start_date=start_date, end_date=end_date,
#                               asset_type="STOCK")

# @pytest.fixture 
# def sample_data_loader_multi_stock():
#     '''
#     Creates a simple test case of a data loader, for one year for Apple
#     and Google
#     '''
#     return DatabaseDataLoader(events=Queue(), tickers=['AAPL', 'GOOG'],
#                               start_date=start_date, end_date=end_date,
#                               asset_type="STOCK")

# @pytest.fixture 
# def sample_data_loader_single_forex():
#     '''
#     Creates a simple test case of a data loader, for one year for forex
#     '''
#     return DatabaseDataLoader(events=Queue(), tickers=['USDEUR=X'],
#                               start_date=start_date, end_date=end_date,
#                               asset_type="FOREX")

# @pytest.fixture
# def sample_mean_reversion_strategy():
#     return MeanReversion(sample_data_loader_single_stock)
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------

                        # Strategy, Mean Reversion initialization

# -----------------------------------------------------------------------------
# def test_initialize_mean_reversion(sample_data_loader_single_stock):
#     assert isinstance(MeanReversion(sample_data_loader_single_stock),
#                       Strategy), \
#                           "Mean Reversion is not subclass of Strategy. " \
#                           "Initialization may have failed with single stock"


# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------

                        # Test Calculation of Z Score
# def test_get_z_score():
#     assert mean_reversion_strategy.get_rolling_z_score(10, 'AAPL')
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------

                        # Test getting rolling mean

# def test_rolling_mean(sample_mean_reversion_strategy):
#     n = 5
#     # Increment by n days
#     data_loader = sample_mean_reversion_strategy.data_loader
#     for _ in range(n):
#         data_loader.next_day()
#         rolling_mean = sample_mean_reversion_strategy.get_rolling_mean(n, 'AAPL')
#         close_lst = [bar.close for bar in data_loader.get_past_bars('AAPL', n)]
#         theoretical_mean = sum(close_lst) / len(close_lst)
#         assert rolling_mean == theoretical_mean, \
#             "There is an error in the calculation of rolling mean"
    


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------

                        # Test Name

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------

                        # Test Name

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

                        # Test Name

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------