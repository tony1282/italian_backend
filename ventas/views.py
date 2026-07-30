from decimal import Decimal

from django.db import transaction
from django.db.models import Max

from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action

from .models import Venta
from .serializers import VentaSerializer

from detalle_venta.models import DetalleVenta

from variantes.models import Variante
from metodos_pago.models import MetodoPago
from empresa.models import Empresa
from cajas.models import Caja
from corte_caja.models import CorteCaja
from inventario.models import MovimientoInventario



class VentaViewSet(viewsets.ModelViewSet):

    queryset = Venta.objects.all()

    serializer_class = VentaSerializer

    permission_classes = [
        IsAuthenticated
    ]


    def create(self, request):

        caja_id = request.data.get("caja_id")

        metodo_pago_id = request.data.get("metodo_pago_id")

        descuento = Decimal(
            request.data.get("descuento", 0)
        )

        productos = request.data.get("productos", [])


        try:

            caja = Caja.objects.get(
                id=caja_id
            )

        except Caja.DoesNotExist:

            return Response(
                {
                    "success": False,
                    "message": "La caja no existe."
                },
                status=status.HTTP_404_NOT_FOUND
            )


        try:

            corte = CorteCaja.objects.get(
                caja=caja,
                fecha_fin__isnull=True
            )

        except CorteCaja.DoesNotExist:

            return Response(
                {
                    "success": False,
                    "message": "La caja no tiene un corte abierto."
                },
                status=status.HTTP_400_BAD_REQUEST
            )


        try:

            metodo_pago = MetodoPago.objects.get(
                id=metodo_pago_id,
                activo=True
            )

        except MetodoPago.DoesNotExist:

            return Response(
                {
                    "success": False,
                    "message": "El método de pago no existe o está inactivo."
                },
                status=status.HTTP_404_NOT_FOUND
            )


        if not productos:

            return Response(
                {
                    "success": False,
                    "message": "Debe agregar al menos un producto."
                },
                status=status.HTTP_400_BAD_REQUEST
            )


        empresa = Empresa.objects.first()

        if not empresa:

            return Response(
                {
                    "success": False,
                    "message": "No hay configuración de empresa."
                },
                status=status.HTTP_400_BAD_REQUEST
            )


        iva_porcentaje = empresa.iva


        subtotal = Decimal("0.00")

        iva = Decimal("0.00")

        total = Decimal("0.00")


        ultima = Venta.objects.aggregate(
            Max("folio")
        )["folio__max"]


        if ultima:

            numero = int(
                ultima.split("-")[1]
            ) + 1

        else:

            numero = 1


        folio = f"V-{numero:07d}"
        
        with transaction.atomic():
            
            venta = Venta.objects.create(
                folio=folio,
                usuario=request.user,
                corte_caja=corte,
                metodo_pago=metodo_pago,
                subtotal=0,
                descuento=descuento,
                iva=0,
                total=0,
            )
            
            for item in productos:
                variante_id=item.get("variante_id")
                
                cantidad = int(item.get("cantidad"))
                
                try: 
                    variante = Variante.objects.get(
                        id=variante_id
                    )
                except Variante.DoesNotExist:
                    transaction.set_rollback(True)
            
                    return Response(
                        {
                            "success": False,
                            "message": "La variante no existe."
                        },
                        status=status.HTTP_404_NOT_FOUND
                    )
            
                if not variante.activo:
            
                    transaction.set_rollback(True)
                    
                    return Response(
                        {
                            "success": False,
                            "message": "La variante está inactiva."
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                    
                if not variante.producto.activo:
                    
                    transaction.set_rollback(True)
                    
                    return Response(
                        {
                            "success": False,
                            "message": "El producto esta inactivo."
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                    
            
                if variante.stock < cantidad:
                    transaction.set_rollback(True)
                    
                    return Response(
                        {
                            "success": False,
                            "message": "Stock insuficiente."
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
        
                precio_unitario = variante.precio_menudeo
        
                subtotal_linea = (
                    precio_unitario * cantidad
                )
        
                subtotal += subtotal_linea
            
                DetalleVenta.objects.create(
                    venta=venta,

                    variante=variante,

                    cantidad=cantidad,

                    precio_unitario=precio_unitario,

                    descuento=0,

                    subtotal=subtotal_linea
                )
                
                MovimientoInventario.objects.create(
                    
                    variante=variante,
                    
                    tipo="SALIDA",
                    
                    cantidad=cantidad,
                    observaciones=f"Venta {folio}",
                    
                    usuario=request.user
                )
                
                variante.stock -= cantidad
                
                variante.save()
                
            subtotal -= descuento
            
            iva = subtotal * (
                iva_porcentaje / Decimal("100")
            )
            
            total = subtotal + iva
            
            venta.subtotal = subtotal
            
            venta.iva = iva 
            
            venta.total = total
            
            venta.save()
            
            return Response (
                {
                    "success": True,
                    "folio": venta.folio,
                    "venta_id": venta.id,
                    "message": "Venta registrada correctamente."
                },
                status=status.HTTP_201_CREATED
            )
            
    def list(self, request):
        
        ventas = Venta.objects.all()
        
        data = []
        
        for venta in ventas:
            
            data.append(
                {
                    "id": venta.id,
                    "folio": venta.folio,
                    "fecha": venta.fecha,
                    "usuario": venta.usuario.nombre,
                    "total": venta.total,
                    "estado": venta.estado,
                }
            )       
        
        return Response(
            {
                "success": True,
                "data": data
            }
        )
        
        
    def retrieve(self, request, pk=None):
        
        try:
            venta = Venta.objects.get(
                pk=pk
            )
            
        except Venta.DoesNotExist:
            
            return Response(
                {
                    "success": False,
                    "message": "La venta no existe."
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        productos = []
        
        for detalle in venta.detalles.all():
            
            productos.append(
                {
                    "producto": detalle.variante.producto.nombre,
                    "variante": detalle.variante.nombre,
                    "cantidad": detalle.cantidad,
                    "precio_unitario": detalle.precio_unitario,
                    "subtotal": detalle.subtotal
                }
            )
            
        return Response({
            
            "success": True,

            "data": {
                "id": venta.id,

                "folio": venta.folio,

                "fecha": venta.fecha,

                "usuario": venta.usuario.nombre,

                "metodo_pago": venta.metodo_pago.nombre,

                "caja": venta.corte_caja.caja.nombre,

                "subtotal": venta.subtotal,

                "iva": venta.iva,

                "total": venta.total,

                "estado": venta.estado,

                "productos": productos

                }
            })
    
    
                
    @action(
        detail=True,
        methods=["post"],
        url_path="cancelar"
    )
    def cancelar(self, request, pk=None):
        try:
            venta = Venta.objects.get(
                id=pk
            )
        
        except Venta.DoesNotExist:
            
            return Response(
                {
                    "success": False,
                    "message": "La venta no existe"
                },
                status=status.HTTP_404_NOT_FOUND
            )
        if request.user.rol != 1:
            
            return Response(
                {
                    "success": False,
                    "message": "No tiene permisos para cancelar ventas"
                },
                status=status.HTTP_403_FORBIDDEN
            )
        if venta.estado == "CANCELADA":
            
            return Response(
                {
                    "success": False,
                    "message": "La venta ya esta cancelada"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        with transaction.atomic():
            detalles = venta.detalles.all()
            
            for detalle in detalles:
                variante = detalle.variante
                variante.stock += detalle.cantidad
                variante.save()
                
                MovimientoInventario.objects.create(
                    variante=variante,
                    tipo="ENTRADA",
                    cantidad=detalle.cantidad,
                    observaciones=f"Cancelación {venta.folio}",
                    usuario=request.user
                )
            venta.estado = "CANCELADA"
            venta.save()
            
        return Response(
            {
                "success": True,
                "message": "Venta cancelada Correctamente."
            },
            status=status.HTTP_200_OK
        )