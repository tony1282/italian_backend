from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    UsuarioViewSet,
    LoginView,
    LogoutView,
    MeView,
    RefreshView
)


router = DefaultRouter()

router.register(
    "usuarios",
    UsuarioViewSet
)


urlpatterns = [

    path(
        "",
        include(router.urls)
    ),

    path(
        "login/",
        LoginView.as_view(),
        name="login"
    ),

    path(
        "logout/",
        LogoutView.as_view(),
        name="logout"
    ),

    path(
        "refresh/",
        RefreshView.as_view(),
        name="refresh"
    ),

    path(
        "me/",
        MeView.as_view(),
        name="me"
    ),

]