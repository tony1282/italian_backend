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