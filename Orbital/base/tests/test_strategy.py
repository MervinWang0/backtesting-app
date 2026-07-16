import numpy as np
import pandas as pd
from queue import Queue
from datetime import datetime
from base.engine.strategy import (Strategy, MovingAverageCross, MeanReversion,
)
from base.engine.data_loader import DatabaseDataLoader

# -----------------------------------------------------------------------------

                        # Initial Setup

# -----------------------------------------------------------------------------
start_date = datetime.fromisoformat("2021-05-24").date()
end_date = datetime.fromisoformat("2022-05-24").date()
sample_data_loader = DatabaseDataLoader(events=Queue(), tickers=['AAPL'],
                            start_date=start_date, end_date=end_date,
                            asset_type="STOCK")

mean_reversion = MeanReversion(data_loader=sample_data_loader)
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------

                        # Test rolling mean Passed

# -----------------------------------------------------------------------------
# n = 120
# # Increment by n days
# data_loader = mean_reversion.data_loader
# for i in range(n):
#     data_loader.next_day()
#     print(f"The current day is {i}")
#     rolling_mean = mean_reversion.get_rolling_mean(i, 'AAPL')
#     close_lst = [bar.close for bar in data_loader.get_past_bars('AAPL', i)]
#     theoretical_mean = sum(close_lst) / len(close_lst)
#     assert rolling_mean == theoretical_mean, \
#         "There is an error in the calculation of rolling mean"

# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------

                        # Test Rolling std Passed

# -----------------------------------------------------------------------------
# n = 120
# # Increment by n days
# data_loader = mean_reversion.data_loader
# for i in range(n):
#     data_loader.next_day()
#     print(f"The current day is {i}")
#     rolling_std = mean_reversion.get_rolling_std(i, 'AAPL')
#     close_lst = [bar.close for bar in data_loader.get_past_bars('AAPL', i)]
#     theoretical_std = np.std(close_lst)
#     assert rolling_std == theoretical_std, \
#         "There is an error in the calculation of rolling std"
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------

                        # Test Z Score Passed

# -----------------------------------------------------------------------------
# n = 120
# # Increment by n days
# data_loader = mean_reversion.data_loader
# data_loader.next_day()
# data_loader.next_day()
# for i in range(2, n):
#     data_loader.next_day()
#     print(f"The current day is {i}")

#     rolling_mean = mean_reversion.get_rolling_mean(i, 'AAPL')
#     rolling_std = mean_reversion.get_rolling_std(i, 'AAPL')
#     close_lst = [bar.close for bar in data_loader.get_past_bars('AAPL', i)]

#     theoretical_std = np.std(close_lst)
#     theoretical_mean = sum(close_lst) / len(close_lst)
#     current_close = data_loader.get_current_bar_value('AAPL', 'close')
#     print(f"This is the current close price {current_close}") 
#     print(f"This is the theoretical mean = {theoretical_mean}")
#     print(f"This is the theoretical std = {theoretical_std}")
#     z_score = mean_reversion.get_rolling_z_score(i, 'AAPL')
#     theoretical_z_score = (current_close - theoretical_mean) / theoretical_std

#     assert theoretical_z_score == z_score, \
#         "There is an error in the calculation of z score" \
#         f" theoretical = {theoretical_z_score}, acutal = {z_score}"
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------

                        # Test rsi calculation Tested that within bounds
                        # But not if calculation is correct

# -----------------------------------------------------------------------------
# result = []
# test = (0, 0, 0)
# for i in range(100):
#     if test is None:
#         test = (0, 0, 0)
#     mean_reversion.data_loader.next_day()
#     print(test)
#     test = mean_reversion.get_rsi(10, 'AAPL', prev_AG=test[1],
#                                   prev_AL=test[2])
#     if test is not None:
#         assert test[0] >= 0 and test[0] <= 100, "RSI must be [0, 100]"
#         result.append(test[0])

# print(f"This is the RSI {test}")
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------

                        # Test Bollinger Bands Passed some manual checks
                        # That diff between bands is correct

# -----------------------------------------------------------------------------
# result = []
# for i in range(100):
#     mean_reversion.data_loader.next_day()
#     bands = mean_reversion.get_bollinger_bands(20, 'AAPL')
#     print(bands)
#     if bands is not None:
#         result.append(bands)
# print(f"These are the Bollinger Bands {pd.DataFrame(result)}")
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