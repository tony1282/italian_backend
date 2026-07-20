from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from rest_framework_simplejwt.views import TokenBlacklistView

from usuarios.views import LoginView, MeView

from usuarios.views import LoginView, MeView, LogoutView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    path("api/", include("usuarios.urls")),
    
    path(
        "api/auth/login/",
        LoginView.as_view(),
        name="token_login"   
    ),
    
    path(
        "api/auth/refresh/",
        TokenRefreshView.as_view(),
        name="token_obtain_pair"
    ),
    
    path(
        "api/auth/logout/",
        LogoutView.as_view(),
        name="logout"
    ),
    
    path(
        "api/auth/me/",
        MeView.as_view(),
        name="auth_me"
    )
]
