from django.db import models
import uuid

from variantes.models import Variante
from usuarios.models import Usuario


class MovimientoInventario(models.Model):

    TIPOS = [
        ("ENTRADA", "Entrada"),
        ("SALIDA", "Salida"),
        ("AJUSTE", "Ajuste"),
        ("DEVOLUCION", "Devolución"),
        ("GARANTIA", "Garantía"),
        ("CAMBIO_PRODUCTO", "Cambio de producto"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    variante = models.ForeignKey(
        Variante,
        on_delete=models.PROTECT,
        related_name="movimientos"
    )

    tipo = models.CharField(
        max_length=30,
        choices=TIPOS
    )

    cantidad = models.PositiveIntegerField()

    observaciones = models.TextField(
        blank=True,
        null=True
    )

    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name="movimientos_inventario"
    )

    fecha = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.tipo} - {self.variante.nombre}"