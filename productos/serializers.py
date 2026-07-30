from rest_framework import serializers

from .models import Producto

class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        
        fields = [
            "id",
            "categoria",
            "nombre",
            "descripcion",
            "activo",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        