from rest_framework import serializers

from .models import Devolucion, DetalleDevolucion


class ProductoDevolucionSerializer(serializers.Serializer):

    detalle_venta_id = serializers.UUIDField()

    cantidad = serializers.IntegerField(
        min_value=1
    )



class CrearDevolucionSerializer(serializers.Serializer):

    venta_id = serializers.UUIDField()
    
    metodo_pago_reembolso_id = serializers.UUIDField()

    tipo = serializers.ChoiceField(
        choices=[
            "NORMAL",
            "GARANTIA",
            "EXTRAORDINARIA"
        ]
    )

    motivo = serializers.CharField()


    productos = ProductoDevolucionSerializer(
        many=True
    )



class DetalleDevolucionSerializer(serializers.ModelSerializer):

    producto = serializers.CharField(
        source="detalle_venta.variante.producto.nombre"
    )

    variante = serializers.CharField(
        source="detalle_venta.variante.nombre"
    )
    
    metodo_pago_reembolso = serializers.CharField(
        source="metodo_pago_reembolso.nombre",
        allow_null=True
    )


    class Meta:

        model = DetalleDevolucion

        fields = [
            "id",
            "producto",
            "variante",
            "cantidad",
            "precio_original",
            "subtotal"
        ]



class DevolucionSerializer(serializers.ModelSerializer):

    venta = serializers.CharField(
        source="venta.folio"
    )


    usuario = serializers.CharField(
        source="usuario.nombre"
    )


    detalles = DetalleDevolucionSerializer(
        many=True
    )


    class Meta:

        model = Devolucion

        fields = [
            "id",
            "venta",
            "usuario",
            "metodo_pago_reembolso",
            "tipo",
            "motivo",
            "estado",
            "total_devuelto",
            "fecha",
            "detalles"
        ]