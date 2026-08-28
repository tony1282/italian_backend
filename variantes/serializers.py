from rest_framework import serializers

from .models import Variante


class VarianteSerializer(
    serializers.ModelSerializer
):

    class Meta:

        model = Variante

        fields = [
            "id",
            "producto",
            "codigo_barras",
            "sku",
            "nombre",

            "stock",
            "stock_defectuoso",
            "stock_minimo",

            "costo",
            "precio_menudeo",
            "precio_mayoreo",
            "garantia_meses",
            "activo",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

        read_only_fields = [
            "id",
            "stock",
            "stock_defectuoso",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    # ==========================================================
    # VALIDACIONES
    # ==========================================================

    def validate(
        self,
        data
    ):

        costo = data.get(
            "costo",
            self.instance.costo
            if self.instance
            else 0
        )

        precio_menudeo = data.get(
            "precio_menudeo",
            self.instance.precio_menudeo
            if self.instance
            else 0
        )

        precio_mayoreo = data.get(
            "precio_mayoreo",
            self.instance.precio_mayoreo
            if self.instance
            else 0
        )

        # ======================================================
        # VALIDAR PRECIOS
        # ======================================================

        if precio_menudeo < costo:

            raise serializers.ValidationError(
                {
                    "precio_menudeo": (
                        "El precio menudeo no puede "
                        "ser menor al costo."
                    )
                }
            )

        if precio_mayoreo < costo:

            raise serializers.ValidationError(
                {
                    "precio_mayoreo": (
                        "El precio mayoreo no puede "
                        "ser menor al costo."
                    )
                }
            )

        # ======================================================
        # VALIDAR ACTIVACIÓN
        # ======================================================

        if (
            self.instance
            and self.instance.activo is False
            and data.get("activo") is True
        ):

            producto = data.get(
                "producto",
                self.instance.producto
            )

            if not producto.activo:

                raise serializers.ValidationError(
                    {
                        "activo": (
                            "No se puede activar la variante "
                            "porque su producto está inactivo."
                        )
                    }
                )

        return data