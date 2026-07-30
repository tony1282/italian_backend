from rest_framework import serializers

from .models import DetalleVenta


class DetalleVentaSerializer(serializers.ModelSerializer):

    class Meta:

        model = DetalleVenta

        fields = "__all__"

        read_only_fields = (
            "id",
        )