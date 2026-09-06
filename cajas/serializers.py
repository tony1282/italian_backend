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

        read_only_fields = [
            "id",
            "estado",
            "activa",
            "fecha_creacion",
            "fecha_actualizacion"
        ]

    def validate(self, attrs):

        errores = {}

        if "activa" in self.initial_data:
            errores["activa"] = (
                "El estado activo no puede modificarse directamente. "
                "Utiliza los endpoints activar/desactivar."
            )

        if "estado" in self.initial_data:
            errores["estado"] = (
                "El estado de la caja no puede modificarse directamente. "
                "Se controla mediante la apertura y cierre de caja."
            )

        if errores:
            raise serializers.ValidationError(errores)

        return attrs

    def validate_nombre(self, value):

        nombre = value.strip()

        if not nombre:
            raise serializers.ValidationError(
                "El nombre es obligatorio."
            )

        queryset = Caja.objects.filter(
            nombre__iexact=nombre
        )

        if self.instance:
            queryset = queryset.exclude(
                pk=self.instance.pk
            )

        if queryset.exists():
            raise serializers.ValidationError(
                "Ya existe una caja con ese nombre."
            )

        return nombre