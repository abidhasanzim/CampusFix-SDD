from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    # NFR-10
    path("auth/login", views.login, name="login"),
    # NFR-10; AC-043
    path("auth/callback", views.login_callback, name="login_callback"),
]
