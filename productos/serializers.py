from rest_framework import serializers

from .models import Producto


class ProductoSerializer(
    serializers.ModelSerializer
):

    categoria_nombre = serializers.CharField(
        source="categoria.nombre",
        read_only=True
    )

    class Meta:

        model = Producto

        fields = [
            "id",
            "categoria",
            "categoria_nombre",
            "nombre",
            "descripcion",
            "activo",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

        read_only_fields = [
            "id",
            "categoria_nombre",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    # ==========================================================
    # VALIDAR CATEGORIA
    # ==========================================================

    def validate_categoria(
        self,
        value
    ):

        if not value.activo:

            raise serializers.ValidationError(
                "No se puede utilizar una categoría inactiva."
            )

        return value

    # ==========================================================
    # VALIDAR NOMBRE
    # ==========================================================

    def validate_nombre(
        self,
        value
    ):

        value = value.strip()

        if not value:

            raise serializers.ValidationError(
                "El nombre del producto es obligatorio."
            )

        queryset = Producto.objects.filter(
            nombre__iexact=value
        )

        if self.instance:

            queryset = queryset.exclude(
                pk=self.instance.pk
            )

        if queryset.exists():

            raise serializers.ValidationError(
                "Ya existe un producto con este nombre."
            )

        return value