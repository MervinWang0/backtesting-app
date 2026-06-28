from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # path("", views.home, name="home"),
    path("", auth_views.LoginView.as_view(template_name="base/login.html"), name="login"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("login/", auth_views.LoginView.as_view(template_name="base/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("register/", views.register_view, name="register"),
    path("run_backtest/", views.backtest_run, name = "run_backtest"),
    path("backtestrunrecords/", views.backtest_run_records, name = "backtest_run_records"),
    path("stocks/", views.stock, name = "stock"),
    path("stocks/<str:symbol>/order/", views.submit_paper_order, name= "submit_paper_order"),
    path("paper-accounts/create", views.create_paper_account, name="create_paper_account"),
    path("portfolio/", views.portfolio, name="portfolio"),

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