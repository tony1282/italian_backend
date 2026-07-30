from django.urls import path, include

from rest_framework.routers import DefaultRouter

from .views import CorteCajaViewSet


router = DefaultRouter()


router.register(
    "caja",
    CorteCajaViewSet
)


urlpatterns = [

    path(
        "",
        include(router.urls)
    )

]