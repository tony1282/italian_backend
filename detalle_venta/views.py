from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from .models import DetalleVenta
from .serializers import DetalleVentaSerializer
from .permissions import EsAdministrador


class DetalleVentaPagination(PageNumberPagination):

    page_size = 50

    max_page_size = 200


class DetalleVentaViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):

    queryset = DetalleVenta.objects.all()

    serializer_class = DetalleVentaSerializer

    permission_classes = [
        IsAuthenticated,
        EsAdministrador
    ]

    pagination_class = DetalleVentaPagination

    lookup_value_regex = (
        "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-"
        "[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
        "[0-9a-fA-F]{12}"
    )