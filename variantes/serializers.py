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
            "activo",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

        extra_kwargs = {
            "sku": {
                "error_messages": {
                    "unique": "Ya existe una variante con este SKU."
                }
            },
            "codigo_barras": {
                "error_messages": {
                    "unique": (
                        "Ya existe una variante con "
                        "este código de barras."
                    )
                }
            },
        }

    # ==========================================================
    # VALIDAR COSTO Y PRECIOS (NO NEGATIVOS)
    # ==========================================================

    def validate_costo(
        self,
        value
    ):

        if value < 0:

            raise serializers.ValidationError(
                "El costo no puede ser negativo."
            )

        return value

    def validate_precio_menudeo(
        self,
        value
    ):

        if value < 0:

            raise serializers.ValidationError(
                "El precio menudeo no puede ser negativo."
            )

        return value

    def validate_precio_mayoreo(
        self,
        value
    ):

        if value < 0:

            raise serializers.ValidationError(
                "El precio mayoreo no puede ser negativo."
            )

        return value

    # ==========================================================
    # VALIDACIONES GENERALES
    # ==========================================================

    def validate(
        self,
        data
    ):

        # ------------------------------------------------------
        # ACTIVO ES DE SOLO LECTURA
        # ------------------------------------------------------

        if "activo" in self.initial_data:

            raise serializers.ValidationError(
                {
                    "activo": (
                        "El estado activo no puede modificarse "
                        "directamente. Utiliza los endpoints "
                        "activar/desactivar."
                    )
                }
            )

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
        # VALIDAR PRODUCTO ACTIVO — CREACIÓN
        # --------------------------------------------------
        # 'activo' ya no se puede enviar en el payload, así que
        # toda variante nueva queda activa por defecto (default
        # del modelo). Por lo tanto, si el producto está
        # inactivo, no se puede crear la variante.
        # ======================================================

        if self.instance is None:

            producto = data.get("producto")

            if producto is not None and not producto.activo:

                raise serializers.ValidationError(
                    {
                        "producto": (
                            "No se puede crear una variante "
                            "activa porque su producto está "
                            "inactivo."
                        )
                    }
                )

        # ======================================================
        # VALIDAR PRODUCTO ACTIVO — CAMBIO DE PRODUCTO
        # --------------------------------------------------
        # Si la variante ya está activa y se intenta moverla a
        # un producto inactivo, se bloquea el cambio.
        # ======================================================

        else:

            if (
                self.instance.activo
                and "producto" in data
                and not data["producto"].activo
            ):

                raise serializers.ValidationError(
                    {
                        "producto": (
                            "No se puede asociar una variante "
                            "activa a un producto inactivo."
                        )
                    }
                )

        return data