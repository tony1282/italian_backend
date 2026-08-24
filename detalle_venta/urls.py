from rest_framework.routers import DefaultRouter

from .views import DetalleVentaViewSet

router = DefaultRouter()

router.register(
    "detalle-venta",
    DetalleVentaViewSet,
    basename="detalle-venta"
)

urlpatterns = router.urls