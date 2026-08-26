from django.urls import path

from .views import (
    ReporteVentasView,
    ReporteInventarioView,
    ReporteStockBajoView,
    ReporteCortesView,
    ReporteProductosView,
    ReporteDevolucionesView,
    ReporteGarantiasView,
    ReporteMovimientosView,
)


urlpatterns = [

    path(
        "reportes/ventas",
        ReporteVentasView.as_view(),
        name="reporte-ventas"
    ),

    path(
        "reportes/inventario",
        ReporteInventarioView.as_view(),
        name="reporte-inventario"
    ),

    path(
        "reportes/stock-bajo",
        ReporteStockBajoView.as_view(),
        name="reporte-stock-bajo"
    ),

    path(
        "reportes/cortes",
        ReporteCortesView.as_view(),
        name="reporte-cortes"
    ),

    path(
        "reportes/productos",
        ReporteProductosView.as_view(),
        name="reporte-productos"
    ),

    path(
        "reportes/devoluciones",
        ReporteDevolucionesView.as_view(),
        name="reporte-devoluciones"
    ),

    path(
        "reportes/garantias",
        ReporteGarantiasView.as_view(),
        name="reporte-garantias"
    ),

    path(
        "reportes/movimientos",
        ReporteMovimientosView.as_view(),
        name="reporte-movimientos"
    ),

]