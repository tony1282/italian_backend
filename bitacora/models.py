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

        indexes = [
            # Filtrar por usuario ordenado por fecha (el caso
            # que se pidió: "ver la bitácora de un usuario").
            # El índice simple en 'usuario' ya lo crea Django
            # automáticamente por ser ForeignKey; este compuesto
            # cubre usuario+fecha juntos, que es como realmente
            # se va a consultar.
            models.Index(fields=["usuario", "-fecha"]),
            models.Index(fields=["modulo"]),
            models.Index(fields=["accion"]),
            models.Index(fields=["fecha"]),
        ]

    def __str__(self):
        return f"{self.modulo} - {self.accion}"