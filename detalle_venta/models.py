from django.db import models
import uuid

from django.db import models

from ventas.models import Venta
from variantes.models import Variante

class DetalleVenta(models.Model):
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        related_name="detalles"
    )
    
    variante = models.ForeignKey(
        Variante,
        on_delete=models.PROTECT,
        related_name="detalles_venta"
    )
    
    cantidad = models.PositiveBigIntegerField()
    
    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    
    descuento = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    
    class Meta:
        
        indexes = [
            models.Index(fields=["venta"]),
            models.Index(fields=["variante"]),
        ]
        
    def __str__(self):
        return f"{self.venta.folio} - {self.variante.nombre}"