import uuid

from django.db import models


class Caja(models.Model):

    ESTADO_ABIERTA = "ABIERTA"
    ESTADO_CERRADA = "CERRADA"

    ESTADOS = [
        (ESTADO_ABIERTA, "Abierta"),
        (ESTADO_CERRADA, "Cerrada"),
    ]


    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    nombre = models.CharField(
        max_length=100,
        unique=True
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default=ESTADO_CERRADA
    )

    activa = models.BooleanField(
        default=True
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True
    )


    def __str__(self):
        return self.nombre