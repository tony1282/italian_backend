from django.db import models

import uuid 

from usuarios.models import Usuario
from corte_caja.models import CorteCaja
from metodos_pago.models import MetodoPago

class Venta(models.Model):
    
    ESTADOS = [
        ("COMPLETADA", "COMPLETADA"),
        ("CANCELADA", "CANCELADA"),
        ("DEVUELTA", "DEVUELTA")
    ]
    
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    folio = models.CharField(
        max_length=30,
        unique=True
    )
    
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name="ventas"
    )
    
    corte_caja = models.ForeignKey(
        CorteCaja,
        on_delete=models.PROTECT,
        related_name="ventas"
    )
    
    metodo_pago = models.ForeignKey(
        MetodoPago,
        on_delete=models.PROTECT,
        related_name="ventas"
    )
    
    fecha = models.DateTimeField(
        auto_now_add=True
    )
    
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    
    descuento = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    
    iva = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default="COMPLETADA"
    )
    
    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )
    
    class Meta:
        
        ordering = [
            "-fecha"
        ]
        
        indexes = [
            models.Index(fields=["folio"]),
            models.Index(fields=["usuario"]),
            models.Index(fields=["corte_caja"]),
            models.Index(fields=["fecha"]),
            models.Index(fields=["estado"]),   
        ]
        
    def __str__(self):
        return self.folio