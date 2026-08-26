from django.urls import path

from .views import BitacoraView


urlpatterns = [

    path(
        "bitacora/",
        BitacoraView.as_view(),
        name="bitacora"
    ),

]