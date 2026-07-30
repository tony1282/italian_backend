from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from .models import DetalleVenta
from .serializers import DetalleVentaSerializer


class DetalleVentaViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):

    queryset = DetalleVenta.objects.all()

    serializer_class = DetalleVentaSerializer

    permission_classes = [
        IsAuthenticated
    ]