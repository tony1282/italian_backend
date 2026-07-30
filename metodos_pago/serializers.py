from rest_framework import serializers
from .models import MetodoPago


class MetodoPagoSerializer(serializers.ModelSerializer):

    class Meta:

        model = MetodoPago

        fields = [
            "id",
            "nombre",
            "activo",
            "fecha_creacion",
            "fecha_actualizacion"
        ]


    def validate_nombre(self, value):

        nombre = value.strip()

        if not nombre:
            raise serializers.ValidationError(
                "El nombre es obligatorio."
            )


        return nombre