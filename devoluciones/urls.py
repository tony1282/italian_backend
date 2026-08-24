from django.urls import path

from .views import (
    DevolucionListCreateView,
    DevolucionDetailView,
    DevolucionAprobarView,
    DevolucionRechazarView
)


urlpatterns = [

    path(
        "devoluciones/",
        DevolucionListCreateView.as_view()
    ),

    path(
        "devoluciones/<uuid:id>/",
        DevolucionDetailView.as_view()
    ),

    path(
        "devoluciones/<uuid:id>/aprobar/",
        DevolucionAprobarView.as_view()
    ),

    path(
        "devoluciones/<uuid:id>/rechazar/",
        DevolucionRechazarView.as_view()
    ),

]