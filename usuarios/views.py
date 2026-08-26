from rest_framework import viewsets, status
from rest_framework.response import Response

from .models import Usuario
from .serializers import (
    UsuarioSerializer,
    LoginSerializer,
    RefreshSerializer
)

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView
)

from rest_framework.permissions import IsAuthenticated

from rest_framework.views import APIView

from rest_framework_simplejwt.tokens import RefreshToken

from .permissions import IsAdmin

from bitacora.services import registrar_bitacora


class UsuarioViewSet(viewsets.ModelViewSet):

    queryset = Usuario.objects.filter(
        activo=True
    )

    serializer_class = UsuarioSerializer

    permission_classes = [
        IsAuthenticated,
        IsAdmin
    ]


    # ==========================================================
    # CREAR USUARIO
    # ==========================================================

    def perform_create(self, serializer):

        usuario = serializer.save()

        registrar_bitacora(

            usuario=self.request.user,

            modulo="Usuarios",

            accion="CREAR_USUARIO",

            descripcion=(
                f"Usuario '{usuario.usuario}' "
                f"creado correctamente por "
                f"{self.request.user.nombre} "
                f"{self.request.user.apellido}."
            )

        )


    # ==========================================================
    # MODIFICAR USUARIO
    # ==========================================================

    def perform_update(self, serializer):

        usuario = serializer.save()

        registrar_bitacora(

            usuario=self.request.user,

            modulo="Usuarios",

            accion="MODIFICAR_USUARIO",

            descripcion=(
                f"Usuario '{usuario.usuario}' "
                f"modificado correctamente por "
                f"{self.request.user.nombre} "
                f"{self.request.user.apellido}."
            )

        )


    # ==========================================================
    # DESACTIVAR USUARIO
    # ==========================================================

    def destroy(
        self,
        request,
        *args,
        **kwargs
    ):

        usuario = self.get_object()

        usuario.activo = False
        usuario.save()

        registrar_bitacora(

            usuario=request.user,

            modulo="Usuarios",

            accion="DESACTIVAR_USUARIO",

            descripcion=(
                f"Usuario '{usuario.usuario}' "
                f"desactivado correctamente por "
                f"{request.user.nombre} "
                f"{request.user.apellido}."
            )

        )

        return Response(

            {
                "success": True,
                "message": (
                    "Usuario desactivado correctamente"
                )
            },

            status=status.HTTP_200_OK
        )


# ==============================================================
# LOGIN
# ==============================================================

class LoginView(TokenObtainPairView):

    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):

        response = super().post(
            request,
            *args,
            **kwargs
        )

        # Si el login fue exitoso
        if response.status_code == status.HTTP_200_OK:

            usuario_data = response.data.get(
                "data",
                {}
            ).get(
                "usuario"
            )

            if usuario_data:

                try:

                    usuario = Usuario.objects.get(
                        id=usuario_data["id"]
                    )

                    registrar_bitacora(

                        usuario=usuario,

                        modulo="Autenticación",

                        accion="INICIO_SESION",

                        descripcion=(
                            f"Inicio de sesión exitoso "
                            f"del usuario '{usuario.usuario}'."
                        )

                    )

                except Usuario.DoesNotExist:

                    pass

        return response


# ==============================================================
# LOGOUT
# ==============================================================

class LogoutView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def post(
        self,
        request
    ):

        try:

            refresh_token = request.data[
                "refresh"
            ]

            token = RefreshToken(
                refresh_token
            )

            token.blacklist()


            registrar_bitacora(

                usuario=request.user,

                modulo="Autenticación",

                accion="CIERRE_SESION",

                descripcion=(
                    f"El usuario "
                    f"'{request.user.usuario}' "
                    f"cerró sesión correctamente."
                )

            )


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


# ==============================================================
# USUARIO AUTENTICADO
# ==============================================================

class MeView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def get(
        self,
        request
    ):

        usuario = request.user

        return Response(

            {
                "success": True,

                "data": {

                    "id": usuario.id,

                    "nombre": usuario.nombre,

                    "apellido": usuario.apellido,

                    "usuario": usuario.usuario,

                    "email": usuario.email,

                    "rol": usuario.rol,

                    "activo": usuario.activo

                }
            },

            status=status.HTTP_200_OK
        )


# ==============================================================
# REFRESH TOKEN
# ==============================================================

class RefreshView(TokenRefreshView):

    serializer_class = RefreshSerializer