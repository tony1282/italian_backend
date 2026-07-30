from rest_framework import viewsets, status
from rest_framework.response import Response

from rest_framework.permissions import IsAuthenticated

from .models import Producto
from .serializers import ProductoSerializer

class ProductoViewSet(viewsets.ModelViewSet):
    
    queryset = Producto.objects.filter(activo=True)
    
    serializer_class = ProductoSerializer
    
    permission_classes = [IsAuthenticated]
    
    def destroy(self, request, *args, **kwargs):
        
        producto = self.get_object()
        producto.activo = False
        producto.save()
        
        return Response(
            {
                "mensaje": "Producto desactivado correctamente"
            },
            status=status.HTTP_200_OK
        ) 
