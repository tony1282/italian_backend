from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import VarianteViewSet

router = DefaultRouter()

router.register(
    "variantes",
    VarianteViewSet
)

urlpatterns = [
    path("", include(router.urls)),
]