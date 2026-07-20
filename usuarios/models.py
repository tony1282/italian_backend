from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager

import uuid


class UsuarioManager(BaseUserManager):

    def create_user(self, usuario, email, password=None, nombre="", apellido="", rol=2, activo=True):

        if not usuario:
            raise ValueError("El usuario es obligatorio")

        if not email:
            raise ValueError("El correo es obligatorio")

        usuario = usuario.lower()
        email = self.normalize_email(email)

        user = self.model(
            nombre=nombre,
            apellido=apellido,
            usuario=usuario,
            email=email,
            rol=rol,
            activo=activo,
        )

        user.set_password(password)
        user.save(using=self._db)

        return user


    def create_superuser(self, usuario, email, password=None, nombre="", apellido=""):

        user = self.create_user(
            usuario=usuario,
            email=email,
            password=password,
            nombre=nombre,
            apellido=apellido,
            rol=1,
            activo=True
        )

        user.is_staff = True
        user.is_superuser = True

        user.save(using=self._db)

        return user



class Usuario(AbstractBaseUser, PermissionsMixin):

    # Configuración de autenticación Django
    objects = UsuarioManager()

    USERNAME_FIELD = "usuario"
    REQUIRED_FIELDS = ["email"]


    # Permisos Django
    is_staff = models.BooleanField(
        default=False
    )


    # Identificador
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )


    # Información personal
    nombre = models.CharField(
        max_length=100
    )

    apellido = models.CharField(
        max_length=100
    )


    # Datos de acceso
    usuario = models.CharField(
        unique=True,
        max_length=50
    )

    email = models.EmailField(
        unique=True,
        max_length=150
    )


    # Roles
    ROL_CHOICES = (
        (1, "admin"),
        (2, "empleado"),
    )

    rol = models.IntegerField(
        choices=ROL_CHOICES,
        default=2
    )


    # Estado del usuario (eliminación lógica)
    activo = models.BooleanField(
        default=True
    )


    @property
    def is_active(self):
        return self.activo


    @is_active.setter
    def is_active(self, value):
        self.activo = value


    # Auditoría
    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True
    )


    # Representación del objeto
    def __str__(self):
        return self.usuario