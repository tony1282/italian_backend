import uuid

from django.db import models
from usuarios.models import Usuario


class Bitacora(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name="bitacora"
    )

    modulo = models.CharField(
        max_length=50
    )

    accion = models.CharField(
        max_length=50
    )

    descripcion = models.TextField()

    fecha = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        db_table = "bitacora"
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.modulo} - {self.accion}"