from rest_framework import serializers

from .models import Bitacora


class BitacoraSerializer(serializers.ModelSerializer):

    usuario = serializers.SerializerMethodField()

    class Meta:
        model = Bitacora
        fields = [
            "id",
            "modulo",
            "accion",
            "descripcion",
            "usuario",
            "fecha",
        ]

    def get_usuario(self, obj):
        return f"{obj.usuario.nombre} {obj.usuario.apellido}"