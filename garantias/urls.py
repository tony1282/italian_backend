from django.urls import path

from .views import (
    GarantiaListCreateView,
    GarantiaDetailView,
    GarantiaAprobarView,
    GarantiaRechazarView,
    GarantiaFinalizarView,
)


urlpatterns = [

    path(
        "garantias/",
        GarantiaListCreateView.as_view()
    ),

    path(
        "garantias/<uuid:id>/",
        GarantiaDetailView.as_view()
    ),

    path(
        "garantias/<uuid:id>/aprobar/",
        GarantiaAprobarView.as_view()
    ),

    path(
        "garantias/<uuid:id>/rechazar/",
        GarantiaRechazarView.as_view()
    ),

    path(
        "garantias/<uuid:id>/finalizar/",
        GarantiaFinalizarView.as_view()
    ),

]
