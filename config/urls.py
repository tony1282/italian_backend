from django.contrib import admin
from django.urls import path, include
from usuarios.views import RefreshView

from usuarios.views import (
    LoginView,
    LogoutView,
    MeView,
    RefreshView
)



urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Modulos
    
    path("api/",
            include("usuarios.urls")),
    
    
    path("api/",
         include("categorias.urls")),
    
    path("api/",
         include("productos.urls")),
    
    path("api/",
        include("variantes.urls")
    ),
    
    path(
    "api/",
    include("inventario.urls")
    ),
    
    path(
        "api/",
        include("empresa.urls")
    ),
    
    path("api/",
         include("metodos_pago.urls")
    ),
    
    path("api/",
         include("cajas.urls")),
    
    path("api/",
         include("corte_caja.urls")),
    
    path("api/",
        include("ventas.urls")),
    
    path("api/",
        include("detalle_venta.urls")),
    
    path(
          "api/",
          include("tickets.urls")
      ),
    
    path(
         "api/",
         include("devoluciones.urls")
     ),

    path(
         "api/",
         include("garantias.urls")
     ),
    
    path(
        "api/",
        include("bitacora.urls")
    ),
    
    path(
        "api/reportes/",
        include("reportes.urls")
    ),
    
    
    # Autenticación
    
    path(
        "api/auth/login/",
        LoginView.as_view(),
        name="token_login"   
    ),
    
    path(
        "api/auth/refresh/",
        RefreshView.as_view(),
        name="token_refresh"
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
