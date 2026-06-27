from django.urls import path

import base.views as views

urlpatterns = [
    # path("", views.home, name="home"),
    path("", views.dashboard, name="dashboard"),
    # path("run_backtest/", views.backtest_run, name = "run_backtest"),
    path("backtest_graph/", views.backtest_graph, name="backtest_graph"),
    # path("backtestrunrecords/", dashboard.backtest_run_records, name = "backtest_run_records"),
    path("backtest/", views.get_backtest, name="backtest"),
    path("backtest/monte_carlo_simulation/", views.monte_carlo_simulation,
         name="monte_carlo_simulation"),
    path("mcs_graph/", views.mcs_graph, name="mcs_graph"),

    path("backtestrunrecords/", views.backtest_run_records, name = "backtest_run_records"),
    path("stocks/", views.stock, name = "stock"),
    # #Authentication wrapped under accounts
    # path("accounts/Login/", views.Login, name = "Login"),
    # path("accounts/Logout/", views.Logout, name = "Logout"),
    # path("accounts/Register/", views.Register, name = "Register"),
    # path("accounts/Profile/", views.Profile, name = "Profile"),
    # path("accounts/settings/", views.Settings, name = "Settings"),
    # path("accounts/ChangePassword/", views.ChangePassword, name = "ChangePassword"),
    # path("accounts/DeleteAccount", views.DeleteAccount, name = "DeleteAccount"),

    # #Market data
    # path("stock_list/", views.stock_list, name = "stock_list"),
    # path("stock_detail/<str:ticker>/", views.stock_detail, name = "stock_detail"),

    # #backtesting
    # path("backtesting/", views.backtesting, name = "backtesting"),
    # path("backtesting/<str:backtest_id>/results", views.backtesting_result, name = "backtesting_result"),
]