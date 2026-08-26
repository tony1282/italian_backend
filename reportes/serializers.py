from rest_framework import serializers


class ReporteVentaSerializer(
    serializers.Serializer
):

    id = serializers.UUIDField()

    folio = serializers.CharField()

    fecha = serializers.DateTimeField()

    usuario = serializers.CharField()

    metodo_pago = serializers.CharField()

    subtotal = serializers.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    descuento = serializers.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    iva = serializers.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    total = serializers.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    estado = serializers.CharField()


class ReporteProductoSerializer(
    serializers.Serializer
):

    producto = serializers.CharField()

    variante = serializers.CharField()

    cantidad_vendida = serializers.IntegerField()

    total_generado = serializers.DecimalField(
        max_digits=10,
        decimal_places=2
    )


class ReporteInventarioSerializer(
    serializers.Serializer
):

    id = serializers.UUIDField()

    producto = serializers.CharField()

    variante = serializers.CharField()

    sku = serializers.CharField()

    codigo_barras = serializers.CharField()

    stock_actual = serializers.IntegerField()

    stock_minimo = serializers.IntegerField()

    costo = serializers.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    precio_menudeo = serializers.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    precio_mayoreo = serializers.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    activo = serializers.BooleanField()


class ReporteStockBajoSerializer(
    serializers.Serializer
):

    id = serializers.UUIDField()

    producto = serializers.CharField()

    variante = serializers.CharField()

    stock_actual = serializers.IntegerField()

    stock_minimo = serializers.IntegerField()

    necesita_reposicion = serializers.BooleanField()


class ReporteCorteSerializer(
    serializers.Serializer
):

    id = serializers.UUIDField()

    caja = serializers.CharField()

    usuario = serializers.CharField()

    fecha_inicio = serializers.DateTimeField()

    fecha_fin = serializers.DateTimeField(
        allow_null=True
    )

    efectivo_inicial = serializers.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    efectivo_final = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        allow_null=True
    )

    diferencia = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        allow_null=True
    )


class ReporteDevolucionProductoSerializer(
    serializers.Serializer
):

    producto = serializers.CharField()

    variante = serializers.CharField()

    cantidad = serializers.IntegerField()

    subtotal = serializers.DecimalField(
        max_digits=10,
        decimal_places=2
    )


class ReporteDevolucionSerializer(
    serializers.Serializer
):

    id = serializers.UUIDField()

    venta_folio = serializers.CharField()

    usuario = serializers.CharField()

    tipo = serializers.CharField()

    motivo = serializers.CharField()

    estado = serializers.CharField()

    total_devuelto = serializers.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    productos = ReporteDevolucionProductoSerializer(
        many=True
    )

    fecha = serializers.DateTimeField()


class ReporteGarantiaSerializer(
    serializers.Serializer
):

    id = serializers.UUIDField()

    venta_folio = serializers.CharField()

    producto = serializers.CharField()

    variante = serializers.CharField()

    variante_nueva = serializers.CharField(
        allow_null=True
    )

    cantidad = serializers.IntegerField()

    usuario = serializers.CharField()

    motivo = serializers.CharField()

    estado = serializers.CharField()

    resolucion = serializers.CharField(
        allow_null=True
    )

    observaciones = serializers.CharField(
        allow_null=True
    )

    fecha = serializers.DateTimeField()

    fecha_actualizacion = serializers.DateTimeField()


class ReporteMovimientoSerializer(
    serializers.Serializer
):

    id = serializers.UUIDField()

    producto = serializers.CharField()

    variante = serializers.CharField()

    tipo = serializers.CharField()

    cantidad = serializers.IntegerField()

    observaciones = serializers.CharField(
        allow_null=True
    )

    usuario = serializers.CharField()

    fecha = serializers.DateTimeField()