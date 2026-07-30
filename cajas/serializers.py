from rest_framework import serializers

from .models import Caja


class CajaSerializer(serializers.ModelSerializer):

    class Meta:

        model = Caja

        fields = [
            "id",
            "nombre",
            "estado",
            "activa",
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