from django.urls import path, include

from rest_framework.routers import DefaultRouter

from .views import CajaViewSet


router = DefaultRouter()

router.register(
    "cajas",
    CajaViewSet,
    basename="cajas"
)


urlpatterns = [
    path(
        "",
        include(router.urls)
    )
]