from rest_framework import viewsets, status
from rest_framework.response import Response

from rest_framework.permissions import IsAuthenticated

from .models import Categoria
from .serializers import CategoriaSerializer

class CategoriaViewSet(viewsets.ModelViewSet):
    
    queryset = Categoria.objects.filter(activo=True)
    
    serializer_class = CategoriaSerializer
    
    permission_classes = [IsAuthenticated]
    
    def destroy(self, request, *args, **kwargs):
        
        categoria = self.get_object()
        categoria.activo = False
        categoria.save()
        
        return Response(
            {
                "mensaje": "Categoría desactivada correctamente"
            },
            status=status.HTTP_200_OK
        )
        