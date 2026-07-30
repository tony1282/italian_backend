from rest_framework import serializers

from .models import Venta


class VentaSerializer(serializers.ModelSerializer):

    class Meta:

        model = Venta

        fields = "__all__"

        read_only_fields = [
            "id",
            "folio",
            "fecha",
            "fecha_creacion"
        ]