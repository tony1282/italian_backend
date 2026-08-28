from rest_framework import serializers

from .models import CorteCaja, MovimientoCaja


class CorteCajaSerializer(
    serializers.ModelSerializer
):

    caja_nombre = serializers.CharField(
        source="caja.nombre",
        read_only=True
    )

    usuario_nombre = serializers.CharField(
        source="usuario.nombre",
        read_only=True
    )

    class Meta:

        model = CorteCaja

        fields = [
            "id",
            "caja",
            "caja_nombre",
            "usuario",
            "usuario_nombre",
            "fecha_inicio",
            "fecha_fin",
            "efectivo_inicial",
            "efectivo_final",
            "diferencia",
        ]

        read_only_fields = [
            "id",
            "caja_nombre",
            "usuario",
            "usuario_nombre",
            "fecha_inicio",
            "fecha_fin",
            "diferencia",
        ]

    def validate_efectivo_inicial(
        self,
        value
    ):

        if value < 0:

            raise serializers.ValidationError(
                "El efectivo inicial no puede ser negativo."
            )

        return value

    def validate_efectivo_final(
        self,
        value
    ):

        if value is not None and value < 0:

            raise serializers.ValidationError(
                "El efectivo final no puede ser negativo."
            )

        return value


class MovimientoCajaSerializer(
    serializers.ModelSerializer
):

    metodo_pago = serializers.CharField(
        source="metodo_pago.nombre",
        read_only=True
    )

    usuario = serializers.CharField(
        source="usuario.nombre",
        read_only=True
    )

    class Meta:

        model = MovimientoCaja

        fields = [
            "id",
            "corte_caja",
            "metodo_pago",
            "tipo",
            "monto",
            "devolucion",
            "observaciones",
            "usuario",
            "fecha",
        ]

        read_only_fields = [
            "id",
            "usuario",
            "fecha",
        ]