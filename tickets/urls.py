from django.urls import path

from .views import TicketVentaView


urlpatterns = [

    path(
        "ventas/<uuid:id>/ticket/",
        TicketVentaView.as_view()
    ),

]