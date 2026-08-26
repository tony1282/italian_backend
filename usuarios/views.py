from django.db import transaction

from rest_framework import (
    viewsets,
    status
)

from rest_framework.response import Response

from rest_framework.decorators import action

from rest_framework.permissions import (
    IsAuthenticated
)

from rest_framework.views import APIView

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView
)

from rest_framework_simplejwt.tokens import (
    RefreshToken
)

from rest_framework.throttling import (
    AnonRateThrottle
)

from .models import Usuario

from .serializers import (
    UsuarioSerializer,
    CrearAdminSerializer,
    LoginSerializer,
    RefreshSerializer
)

from .permissions import IsAdmin

from bitacora.services import (
    registrar_bitacora
)


# ==============================================================
# THROTTLE LOGIN
# ==============================================================

class LoginThrottle(AnonRateThrottle):

    scope = "login"


# ==============================================================
# USUARIOS
# ==============================================================

class UsuarioViewSet(
    viewsets.ModelViewSet
):

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

    def create(
        self,
        request,
        *args,
        **kwargs
    ):

        serializer = self.get_serializer(
            data=request.data
        )

        if not serializer.is_valid():

            return Response(

                {
                    "success": False,

                    "message": (
                        "No se pudo registrar el usuario."
                    ),

                    "data": serializer.errors
                },

                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():

            self.perform_create(
                serializer
            )

        return Response(

            {
                "success": True,

                "message": (
                    "Usuario registrado correctamente."
                ),

                "data": None
            },

            status=status.HTTP_201_CREATED
        )


    # ==========================================================
    # PERFORM CREATE
    # ==========================================================

    def perform_create(
        self,
        serializer
    ):

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
    # CREAR ADMINISTRADOR
    # ==========================================================

    @action(
        detail=False,
        methods=["post"],
        url_path="crear-admin"
    )
    def crear_admin(
        self,
        request
    ):

        serializer = CrearAdminSerializer(
            data=request.data
        )

        if not serializer.is_valid():

            return Response(

                {
                    "success": False,

                    "message": (
                        "No se pudo crear el administrador."
                    ),

                    "data": serializer.errors
                },

                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():

            usuario = serializer.save()

            registrar_bitacora(

                usuario=request.user,

                modulo="Usuarios",

                accion="CREAR_ADMIN",

                descripcion=(
                    f"Administrador '{usuario.usuario}' "
                    f"creado correctamente por "
                    f"{request.user.nombre} "
                    f"{request.user.apellido}."
                )

            )

        return Response(

            {
                "success": True,

                "message": (
                    "Administrador creado correctamente."
                ),

                "data": None
            },

            status=status.HTTP_201_CREATED
        )


    # ==========================================================
    # MODIFICAR USUARIO
    # ==========================================================

    def update(
        self,
        request,
        *args,
        **kwargs
    ):

        partial = kwargs.pop(
            "partial",
            False
        )

        instance = self.get_object()

        # ------------------------------------------------------
        # NO PERMITIR MODIFICAR ADMINISTRADORES
        # ------------------------------------------------------

        if instance.rol == 1:

            return Response(

                {
                    "success": False,

                    "message": (
                        "Los administradores "
                        "no pueden modificarse desde "
                        "este endpoint."
                    ),

                    "data": None
                },

                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(

            instance,

            data=request.data,

            partial=partial

        )

        if not serializer.is_valid():

            return Response(

                {
                    "success": False,

                    "message": (
                        "No se pudo modificar el usuario."
                    ),

                    "data": serializer.errors
                },

                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():

            self.perform_update(
                serializer
            )

        return Response(

            {
                "success": True,

                "message": (
                    "Usuario modificado correctamente."
                ),

                "data": None
            },

            status=status.HTTP_200_OK
        )


    # ==========================================================
    # PERFORM UPDATE
    # ==========================================================

    def perform_update(
        self,
        serializer
    ):

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

        # ------------------------------------------------------
        # AUTO-DESACTIVACIÓN
        # ------------------------------------------------------

        if usuario.id == request.user.id:

            return Response(

                {
                    "success": False,

                    "message": (
                        "No puedes desactivar "
                        "tu propio usuario."
                    ),

                    "data": None
                },

                status=status.HTTP_400_BAD_REQUEST
            )


        # ------------------------------------------------------
        # NO DESACTIVAR ADMINISTRADORES
        # ------------------------------------------------------

        if usuario.rol == 1:

            return Response(

                {
                    "success": False,

                    "message": (
                        "No puedes desactivar "
                        "un administrador."
                    ),

                    "data": None
                },

                status=status.HTTP_403_FORBIDDEN
            )


        # ------------------------------------------------------
        # DESACTIVACIÓN
        # ------------------------------------------------------

        with transaction.atomic():

            usuario.activo = False

            usuario.save(

                update_fields=[
                    "activo",
                    "fecha_actualizacion"
                ]

            )

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
                    "Usuario desactivado correctamente."
                ),

                "data": None
            },

            status=status.HTTP_200_OK
        )


# ==============================================================
# LOGIN
# ==============================================================

class LoginView(
    TokenObtainPairView
):

    serializer_class = LoginSerializer

    # ----------------------------------------------------------
    # PROTECCIÓN CONTRA FUERZA BRUTA
    # ----------------------------------------------------------

    throttle_classes = [
        LoginThrottle
    ]


    def post(
        self,
        request,
        *args,
        **kwargs
    ):

        response = super().post(
            request,
            *args,
            **kwargs
        )

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
                            f"del usuario "
                            f"'{usuario.usuario}'."
                        )

                    )

                except Usuario.DoesNotExist:

                    pass

        return response


# ==============================================================
# LOGOUT
# ==============================================================

class LogoutView(
    APIView
):

    permission_classes = [
        IsAuthenticated
    ]

    def post(
        self,
        request
    ):

        refresh_token = request.data.get(
            "refresh"
        )

        if not refresh_token:

            return Response(

                {
                    "success": False,

                    "message": (
                        "El refresh token es obligatorio."
                    ),

                    "data": None
                },

                status=status.HTTP_400_BAD_REQUEST
            )

        try:

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

                    "message": (
                        "Sesión cerrada correctamente."
                    ),

                    "data": None
                },

                status=status.HTTP_200_OK
            )

        except Exception:

            return Response(

                {
                    "success": False,

                    "message": (
                        "Token inválido."
                    ),

                    "data": None
                },

                status=status.HTTP_400_BAD_REQUEST
            )


# ==============================================================
# USUARIO AUTENTICADO
# ==============================================================

class MeView(
    APIView
):

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

                "message": (
                    "Usuario obtenido correctamente."
                ),

                "data": {

                    "id": str(usuario.id),

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

class RefreshView(
    TokenRefreshView
):

    serializer_class = RefreshSerializer