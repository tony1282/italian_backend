from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Variante
from .serializers import VarianteSerializer

from rest_framework.decorators import action


class VarianteViewSet(viewsets.ModelViewSet):

    queryset = Variante.objects.filter(activo=True)

    serializer_class = VarianteSerializer

    permission_classes = [IsAuthenticated]

    def destroy(self, request, *args, **kwargs):

        variante = self.get_object()

        variante.activo = False
        variante.save()

        return Response(
            {
                "success": True,
                "message": "Variante desactivada correctamente."
            },
            status=status.HTTP_200_OK
        )
        
    @action(
        detail=False,
        methods=["get"],
        url_path=r"codigo/(?P<codigo>[^/.]+)"
    )
    
    def buscar_por_codigo(self, request, codigo=None):
        
        try:
            variante = Variante.objects.get(
                codigo_barras=codigo,
                activo=True
            )

            serializer = self.get_serializer(variante)
            
            return Response(serializer.data)
        except Variante.DoesNotExist:
            
            return Response(
                {
                    "success": False,
                    "message": "No existe una variante con ese codigo"
                },
                status=status.HTTP_404_NOT_FOUND
            )