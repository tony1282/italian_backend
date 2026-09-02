from rest_framework import serializers

from .models import Garantia


class CrearGarantiaSerializer(serializers.Serializer):

    venta_id = serializers.UUIDField()

    detalle_venta_id = serializers.UUIDField()

    variante_id = serializers.UUIDField()

    cantidad = serializers.IntegerField(
        min_value=1
    )

    motivo = serializers.CharField(
        allow_blank=False
    )


class AprobarGarantiaSerializer(serializers.Serializer):

    resolucion = serializers.ChoiceField(
        choices=[
            "REEMPLAZO",
            "CAMBIO_PRODUCTO",
            "REPARACION"
        ]
    )

    variante_nueva_id = serializers.UUIDField(
        required=False,
        allow_null=True
    )

    observaciones = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True
    )

    def validate(self, data):

        resolucion = data.get("resolucion")
        variante_nueva_id = data.get(
            "variante_nueva_id"
        )

        if (
            resolucion == "CAMBIO_PRODUCTO"
            and not variante_nueva_id
        ):
            raise serializers.ValidationError(
                "variante_nueva_id es obligatorio "
                "para CAMBIO_PRODUCTO."
            )

        if (
            resolucion != "CAMBIO_PRODUCTO"
            and variante_nueva_id
        ):
            raise serializers.ValidationError(
                "variante_nueva_id solo debe enviarse "
                "cuando la resolución sea CAMBIO_PRODUCTO."
            )

        return data


class RechazarGarantiaSerializer(serializers.Serializer):

    observaciones = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True
    )


class FinalizarGarantiaSerializer(serializers.Serializer):

    observaciones = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True
    )


class GarantiaSerializer(serializers.ModelSerializer):

    venta = serializers.CharField(
        source="venta.folio"
    )

    usuario = serializers.CharField(
        source="usuario.nombre"
    )

    variante = serializers.CharField(
        source="variante.nombre"
    )

    producto = serializers.CharField(
        source="variante.producto.nombre"
    )

    variante_nueva = serializers.CharField(
        source="variante_nueva.nombre",
        allow_null=True
    )

    garantia_meses = serializers.IntegerField(
        source="variante.garantia_meses"
    )

    class Meta:

        model = Garantia

        fields = [
            "id",
            "venta",
            "usuario",
            "producto",
            "variante",
            "variante_nueva",
            "cantidad",
            "garantia_meses",
            "motivo",
            "estado",
            "resolucion",
            "observaciones",
            "fecha",
            "fecha_actualizacion",
        ]