from django.urls import path

from .views import EmpresaView

urlpatterns = [
    path(
        "empresa",
        EmpresaView.as_view()
    ),
]