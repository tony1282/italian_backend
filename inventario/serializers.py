from rest_framework import serializers

from .models import MovimientoInventario


class MovimientoInventarioSerializer(
    serializers.ModelSerializer
):

    variante = serializers.CharField(
        source="variante.nombre",
        read_only=True
    )

    usuario = serializers.CharField(
        source="usuario.nombre",
        read_only=True
    )

    class Meta:

        model = MovimientoInventario

        fields = [
            "id",
            "variante",
            "tipo",
            "stock_anterior",
            "cantidad",
            "stock_nuevo",
            "observaciones",
            "usuario",
            "fecha",
        ]

        read_only_fields = [
            "id",
            "stock_anterior",
            "stock_nuevo",
            "usuario",
            "fecha",
        ]