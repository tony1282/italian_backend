from rest_framework import serializers

from .models import Usuario

from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer
)

from rest_framework.exceptions import (
    AuthenticationFailed
)


# ==========================================================
# USUARIO — LECTURA
# ==========================================================

class UsuarioReadSerializer(
    serializers.ModelSerializer
):

    rol_nombre = serializers.CharField(
        source="get_rol_display",
        read_only=True
    )

    class Meta:

        model = Usuario

        fields = [
            "id",
            "nombre",
            "apellido",
            "usuario",
            "email",
            "rol",
            "rol_nombre",
            "activo",
            "fecha_creacion",
            "fecha_actualizacion",
        ]


# ==========================================================
# USUARIO — ESCRITURA
# ==========================================================

class UsuarioSerializer(
    serializers.ModelSerializer
):

    class Meta:

        model = Usuario

        fields = [
            "nombre",
            "apellido",
            "usuario",
            "email",
            "password",
        ]

        extra_kwargs = {

            "password": {
                "write_only": True,
                "min_length": 8
            }

        }


    # ======================================================
    # VALIDAR USUARIO
    # ======================================================

    def validate_usuario(
        self,
        value
    ):

        value = value.strip().lower()

        if not value:

            raise serializers.ValidationError(
                "El nombre de usuario es obligatorio."
            )

        queryset = Usuario.objects.filter(
            usuario=value
        )

        if self.instance:

            queryset = queryset.exclude(
                pk=self.instance.pk
            )

        if queryset.exists():

            raise serializers.ValidationError(
                "Este nombre de usuario ya está registrado."
            )

        return value


    # ======================================================
    # VALIDAR EMAIL
    # ======================================================

    def validate_email(
        self,
        value
    ):

        value = value.strip().lower()

        if not value:

            raise serializers.ValidationError(
                "El correo electrónico es obligatorio."
            )

        queryset = Usuario.objects.filter(
            email=value
        )

        if self.instance:

            queryset = queryset.exclude(
                pk=self.instance.pk
            )

        if queryset.exists():

            raise serializers.ValidationError(
                "Este correo electrónico ya está registrado."
            )

        return value


    # ======================================================
    # CREAR USUARIO
    # ======================================================

    def create(
        self,
        validated_data
    ):

        password = validated_data.pop(
            "password"
        )

        return Usuario.objects.create_user(

            password=password,

            rol=2,

            activo=True,

            **validated_data
        )


    # ======================================================
    # MODIFICAR USUARIO
    # ======================================================

    def update(
        self,
        instance,
        validated_data
    ):

        password = validated_data.pop(
            "password",
            None
        )

        if password:

            instance.set_password(
                password
            )

        for attr, value in validated_data.items():

            setattr(
                instance,
                attr,
                value
            )

        instance.save()

        return instance


# ==========================================================
# CREAR ADMINISTRADOR
# ==========================================================

class CrearAdminSerializer(
    serializers.ModelSerializer
):

    class Meta:

        model = Usuario

        fields = [
            "nombre",
            "apellido",
            "usuario",
            "email",
            "password",
        ]

        extra_kwargs = {

            "password": {
                "write_only": True,
                "min_length": 8
            }

        }


    # ======================================================
    # VALIDAR USUARIO
    # ======================================================

    def validate_usuario(
        self,
        value
    ):

        value = value.strip().lower()

        if not value:

            raise serializers.ValidationError(
                "El nombre de usuario es obligatorio."
            )

        if Usuario.objects.filter(
            usuario=value
        ).exists():

            raise serializers.ValidationError(
                "Este nombre de usuario ya está registrado."
            )

        return value


    # ======================================================
    # VALIDAR EMAIL
    # ======================================================

    def validate_email(
        self,
        value
    ):

        value = value.strip().lower()

        if not value:

            raise serializers.ValidationError(
                "El correo electrónico es obligatorio."
            )

        if Usuario.objects.filter(
            email=value
        ).exists():

            raise serializers.ValidationError(
                "Este correo electrónico ya está registrado."
            )

        return value


    # ======================================================
    # CREAR ADMINISTRADOR
    # ======================================================

    def create(
        self,
        validated_data
    ):

        password = validated_data.pop(
            "password"
        )

        return Usuario.objects.create_superuser(

            password=password,

            **validated_data
        )


# ==========================================================
# LOGIN
# ==========================================================

class LoginSerializer(
    TokenObtainPairSerializer
):

    def validate(
        self,
        attrs
    ):

        # ------------------------------------------------------
        # BUSCAR USUARIO
        # ------------------------------------------------------

        usuario = Usuario.objects.filter(
            usuario=attrs.get("usuario")
        ).first()

        # ------------------------------------------------------
        # USUARIO NO EXISTE
        # ------------------------------------------------------

        if not usuario:

            raise AuthenticationFailed(
                "Usuario o contraseña incorrectos."
            )

        # ------------------------------------------------------
        # USUARIO INACTIVO
        # ------------------------------------------------------

        if not usuario.activo:

            raise AuthenticationFailed(
                "Este usuario está inactivo."
            )

        # ------------------------------------------------------
        # VALIDAR CREDENCIALES
        # ------------------------------------------------------

        data = super().validate(
            attrs
        )

        usuario = self.user

        # ------------------------------------------------------
        # SEGUNDA VALIDACIÓN DE SEGURIDAD
        # ------------------------------------------------------

        if not usuario.activo:

            raise AuthenticationFailed(
                "Este usuario está inactivo."
            )

        # ------------------------------------------------------
        # RESPUESTA
        # ------------------------------------------------------

        return {

            "success": True,

            "message": (
                "Inicio de sesión correcto."
            ),

            "data": {

                "access": data["access"],

                "refresh": data["refresh"],

                "usuario": {

                    "id": str(usuario.id),

                    "nombre": usuario.nombre,

                    "apellido": usuario.apellido,

                    "usuario": usuario.usuario,

                    "rol": usuario.rol,

                    "activo": usuario.activo

                }

            }

        }
        
# ==========================================================
# REFRESH TOKEN
# ==========================================================

class RefreshSerializer(
    TokenRefreshSerializer
):

    def validate(
        self,
        attrs
    ):
        data = super().validate(
            attrs
        )

        usuario = self.user

        # ------------------------------------------------------
        # VERIFICAR QUE EL USUARIO SIGA ACTIVO
        # ------------------------------------------------------

        if not usuario.activo:

            raise AuthenticationFailed(
                "Este usuario está inactivo."
            )

        response = {

            "success": True,

            "message": (
                "Token actualizado correctamente."
            ),

            "data": {

                "access": data["access"]

            }
        }

        if "refresh" in data:

            response["data"]["refresh"] = (
                data["refresh"]
            )

        return response