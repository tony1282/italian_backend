from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
    BaseUserManager
)

import uuid


class UsuarioManager(BaseUserManager):

    def create_user(
        self,
        usuario,
        email,
        password=None,
        nombre="",
        apellido="",
        rol=2,
        activo=True
    ):

        if not usuario:
            raise ValueError(
                "El usuario es obligatorio"
            )

        if not email:
            raise ValueError(
                "El correo es obligatorio"
            )

        usuario = usuario.strip().lower()
        email = self.normalize_email(email)

        user = self.model(
            nombre=nombre,
            apellido=apellido,
            usuario=usuario,
            email=email,
            rol=rol,
            activo=activo,
            is_staff=(rol in (0, 1)),
            is_superuser=(rol == 0),
        )

        user.set_password(password)

        user.save(
            using=self._db
        )

        return user


    def create_superuser(
        self,
        usuario,
        email,
        password=None,
        nombre="",
        apellido=""
    ):

        return self.create_user(
            usuario=usuario,
            email=email,
            password=password,
            nombre=nombre,
            apellido=apellido,
            rol=0,
            activo=True
        )


class Usuario(
    AbstractBaseUser,
    PermissionsMixin
):

    objects = UsuarioManager()

    USERNAME_FIELD = "usuario"

    REQUIRED_FIELDS = [
        "email"
    ]


    # ==========================================================
    # PERMISOS DJANGO
    # ==========================================================

    is_staff = models.BooleanField(
        default=False
    )


    # ==========================================================
    # IDENTIFICADOR
    # ==========================================================

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )


    # ==========================================================
    # INFORMACIÓN PERSONAL
    # ==========================================================

    nombre = models.CharField(
        max_length=100
    )

    apellido = models.CharField(
        max_length=100
    )


    # ==========================================================
    # DATOS DE ACCESO
    # ==========================================================

    usuario = models.CharField(
        unique=True,
        max_length=50
    )

    email = models.EmailField(
        unique=True,
        max_length=150
    )


    # ==========================================================
    # ROLES
    # ==========================================================

    ROL_CHOICES = (
        (0, "superadmin"),
        (1, "admin"),
        (2, "empleado"),
    )

    rol = models.IntegerField(
        choices=ROL_CHOICES,
        default=2
    )


    # ==========================================================
    # ESTADO
    # ==========================================================

    activo = models.BooleanField(
        default=True
    )


    @property
    def is_active(self):
        return self.activo


    @is_active.setter
    def is_active(self, value):
        self.activo = value


    # ==========================================================
    # AUDITORÍA
    # ==========================================================

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True
    )


    # ==========================================================
    # REPRESENTACIÓN
    # ==========================================================

    def __str__(self):
        return self.usuario