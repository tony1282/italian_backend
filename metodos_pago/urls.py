from django.urls import path

from .views import (
    MetodoPagoView,
    MetodoPagoActivoView
)


urlpatterns = [

    path(
        "metodos-pago/",
        MetodoPagoView.as_view()
    ),

    path(
        "metodos-pago/activos/",
        MetodoPagoActivoView.as_view()
    ),

    path(
        "metodos-pago/<uuid:id>/",
        MetodoPagoView.as_view()
    ),

]