from django.urls import path

from .views import TicketVentaView


urlpatterns = [

    path(
        "ventas/<str:id>/ticket/",
        TicketVentaView.as_view()
    ),

]