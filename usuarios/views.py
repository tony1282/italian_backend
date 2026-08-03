from rest_framework import viewsets, status
from rest_framework.response import Response

from .models import Usuario
from .serializers import (
    UsuarioSerializer,
    LoginSerializer,
    RefreshSerializer
)


from rest_framework_simplejwt.views import TokenObtainPairView

from rest_framework.permissions import IsAuthenticated

from rest_framework.views import APIView

from rest_framework_simplejwt.tokens import RefreshToken

from rest_framework_simplejwt.views import TokenRefreshView


from .permissions import IsAdmin



class UsuarioViewSet(viewsets.ModelViewSet):

    queryset = Usuario.objects.filter(activo=True)

    serializer_class = UsuarioSerializer

    permission_classes = [
        IsAuthenticated,
        IsAdmin
    ]

    def destroy(self, request, *args, **kwargs):

        usuario = self.get_object()

        usuario.activo = False
        usuario.save()

        return Response(
            {
                "success": True,
                "message": "Usuario desactivado correctamente"
            },
            status=status.HTTP_200_OK
        )
        
    
        
class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    
class LogoutView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        try:
            refresh_token = request.data["refresh"]

            token = RefreshToken(refresh_token)

            token.blacklist()

            return Response(
                {
                    "success": True,
                    "message": "Sesión cerrada."
                },
                status=status.HTTP_200_OK
            )

        except Exception:

            return Response(
                {
                    "success": False,
                    "message": "Token inválido."
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
class MeView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        usuario = request.user
        
        return  Response (
            {
                "success": True,
                "data": {
                    "id": usuario.id,
                    "nombre": usuario.nombre,
                    "rol": usuario.rol,
                }
            },
            status=status.HTTP_200_OK            
        ) 
        
class RefreshView(TokenRefreshView):
    serializer_class = RefreshSerializer