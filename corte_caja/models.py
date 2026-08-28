import uuid

from django.db import models
from django.conf import settings

from cajas.models import Caja


class CorteCaja(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    caja = models.ForeignKey(
        Caja,
        on_delete=models.PROTECT,
        related_name="cortes"
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cortes"
    )

    fecha_inicio = models.DateTimeField(
        auto_now_add=True
    )

    fecha_fin = models.DateTimeField(
        null=True,
        blank=True
    )

    efectivo_inicial = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    efectivo_final = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    diferencia = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    class Meta:

        indexes = [
            models.Index(fields=["caja"]),
            models.Index(fields=["usuario"]),
            models.Index(fields=["fecha_inicio"]),
            models.Index(fields=["fecha_fin"]),
        ]

    def __str__(self):

        return f"Corte {self.id}"


class MovimientoCaja(models.Model):

    TIPOS = [
        ("REEMBOLSO", "Reembolso"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    corte_caja = models.ForeignKey(
        CorteCaja,
        on_delete=models.PROTECT,
        related_name="movimientos"
    )

    metodo_pago = models.ForeignKey(
        "metodos_pago.MetodoPago",
        on_delete=models.PROTECT,
        related_name="movimientos_caja"
    )

    tipo = models.CharField(
        max_length=30,
        choices=TIPOS
    )

    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    devolucion = models.OneToOneField(
        "devoluciones.Devolucion",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="movimiento_caja"
    )

    observaciones = models.TextField(
        blank=True,
        null=True
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="movimientos_caja"
    )

    fecha = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        indexes = [
            models.Index(fields=["corte_caja"]),
            models.Index(fields=["metodo_pago"]),
            models.Index(fields=["tipo"]),
            models.Index(fields=["fecha"]),
        ]

    def __str__(self):

        return f"{self.tipo} - ${self.monto}"