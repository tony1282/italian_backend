from django.db import models

import uuid

class Categoria(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    nombre = models.CharField(
        max_length=100,
        unique=True
    )
    
    descripcion = models.TextField(
        blank=True,
        null=True
    )
    
    activo = models.BooleanField(
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