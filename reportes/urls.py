from django.urls import path

from .views import (
    ReporteResumenDiaView,
    ReporteVentasView,
    ReporteProductosView,
    ReporteInventarioView,
    ReporteStockBajoView,
    ReporteCortesView,
    ReporteDevolucionesView,
    ReporteGarantiasView,
    ReporteMovimientosView,
)


urlpatterns = [

    # ========================================================
    # RESUMEN
    # ========================================================

    path(
        "resumen-dia/",
        ReporteResumenDiaView.as_view(),
        name="reporte-resumen-dia"
    ),

    # ========================================================
    # VENTAS
    # ========================================================

    path(
        "ventas/",
        ReporteVentasView.as_view(),
        name="reporte-ventas"
    ),

    # ========================================================
    # PRODUCTOS
    # ========================================================

    path(
        "productos/",
        ReporteProductosView.as_view(),
        name="reporte-productos"
    ),

    # ========================================================
    # INVENTARIO
    # ========================================================

    path(
        "inventario/",
        ReporteInventarioView.as_view(),
        name="reporte-inventario"
    ),

    # ========================================================
    # STOCK BAJO
    # ========================================================

    path(
        "stock-bajo/",
        ReporteStockBajoView.as_view(),
        name="reporte-stock-bajo"
    ),

    # ========================================================
    # CORTES
    # ========================================================

    path(
        "cortes/",
        ReporteCortesView.as_view(),
        name="reporte-cortes"
    ),

    # ========================================================
    # DEVOLUCIONES
    # ========================================================

    path(
        "devoluciones/",
        ReporteDevolucionesView.as_view(),
        name="reporte-devoluciones"
    ),

    # ========================================================
    # GARANTÍAS
    # ========================================================

    path(
        "garantias/",
        ReporteGarantiasView.as_view(),
        name="reporte-garantias"
    ),

    # ========================================================
    # MOVIMIENTOS
    # ========================================================

    path(
        "movimientos/",
        ReporteMovimientosView.as_view(),
        name="reporte-movimientos"
    ),
]