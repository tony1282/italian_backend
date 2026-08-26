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
# USUARIO
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

        data = super().validate(
            attrs
        )

        usuario = self.user

        if not usuario.activo:

            raise AuthenticationFailed(
                "Este usuario está inactivo."
            )

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

                    "rol": usuario.rol

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