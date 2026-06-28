from django.urls import path
from django.contrib.auth import views as auth_views
import base.views as views

urlpatterns = [
    path("", auth_views.LoginView.as_view(template_name="base/login.html"), name="login"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("login/", auth_views.LoginView.as_view(template_name="base/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("register/", views.register_view, name="register"),
    path("backtestrunrecords/", views.backtest_run_records, name = "backtest_run_records"),
    path("stocks/", views.stock, name = "stock"),
    path("stocks/<str:symbol>/order/", views.submit_paper_order, name= "submit_paper_order"),
    path("paper-accounts/create", views.create_paper_account, name="create_paper_account"),
    path("portfolio/", views.portfolio, name="portfolio"),
    path("backtest_graph/", views.backtest_graph, name="backtest_graph"),
    path("backtest/", views.get_backtest, name="backtest"),
    path("backtest/monte_carlo_simulation/", views.monte_carlo_simulation,
         name="monte_carlo_simulation"),
    path("mcs_graph/", views.mcs_graph, name="mcs_graph"),
    path("backtestrunrecords/", views.backtest_run_records, name = "backtest_run_records"),
    path("stocks/", views.stock, name = "stock"),
    # #Market data
    # path("stock_list/", views.stock_list, name = "stock_list"),
    # path("stock_detail/<str:ticker>/", views.stock_detail, name = "stock_detail"),

    # #backtesting
    # path("backtesting/", views.backtesting, name = "backtesting"),
    # path("backtesting/<str:backtest_id>/results", views.backtesting_result, name = "backtesting_result"),
]