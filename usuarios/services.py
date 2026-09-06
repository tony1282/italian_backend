from django.db import transaction

from bitacora.services import registrar_bitacora
from config.exceptions import BusinessException

from .models import Usuario


# ==============================================================
# VALIDACIONES DE PERMISOS SOBRE USUARIOS
# ==============================================================

def validar_no_automodificacion(actor, objetivo, accion="modificarte"):
    if objetivo.id == actor.id:
        raise BusinessException(f"No puedes {accion}")


def validar_jerarquia(actor, objetivo):
    """
    Admin (rol=1) no puede operar sobre admins ni superadmins.
    Superadmin (rol=0) no puede operar sobre otros superadmins.
    """
    if actor.rol == 1 and objetivo.rol in (0, 1):
        raise BusinessException("No tienes permisos para operar sobre este usuario.")

    if actor.rol == 0 and objetivo.rol == 0:
        raise BusinessException("No puedes operar sobre otro superadministrador.")


# ==============================================================
# CREAR USUARIO
# ==============================================================

def crear_usuario(serializer, actor):
    with transaction.atomic():
        usuario = serializer.save()
        registrar_bitacora(
            usuario=actor,
            modulo="Usuarios",
            accion="CREAR_USUARIO",
            descripcion=(
                f"Usuario '{usuario.usuario}' creado correctamente por "
                f"{actor.nombre} {actor.apellido}."
            ),
        )
    return usuario


# ==============================================================
# CREAR ADMINISTRADOR
# ==============================================================

def crear_admin(serializer, actor):
    with transaction.atomic():
        usuario = serializer.save()
        registrar_bitacora(
            usuario=actor,
            modulo="Usuarios",
            accion="CREAR_ADMIN",
            descripcion=(
                f"Administrador '{usuario.usuario}' creado correctamente por "
                f"{actor.nombre} {actor.apellido}."
            ),
        )
    return usuario


# ==============================================================
# MODIFICAR USUARIO
# ==============================================================

def modificar_usuario(serializer, actor):
    with transaction.atomic():
        usuario = serializer.save()
        registrar_bitacora(
            usuario=actor,
            modulo="Usuarios",
            accion="MODIFICAR_USUARIO",
            descripcion=(
                f"Usuario '{usuario.usuario}' modificado correctamente por "
                f"{actor.nombre} {actor.apellido}."
            ),
        )
    return usuario


# ==============================================================
# DESACTIVAR USUARIO
# ==============================================================

def desactivar_usuario(usuario, actor):
    with transaction.atomic():
        usuario.activo = False
        usuario.save(update_fields=["activo", "fecha_actualizacion"])
        registrar_bitacora(
            usuario=actor,
            modulo="Usuarios",
            accion="DESACTIVAR_USUARIO",
            descripcion=(
                f"Usuario '{usuario.usuario}' desactivado correctamente por "
                f"{actor.nombre} {actor.apellido}."
            ),
        )


# ==============================================================
# ACTIVAR USUARIO
# ==============================================================

def activar_usuario(usuario, actor):
    if usuario.activo:
        raise BusinessException("El usuario ya está activo.")

    with transaction.atomic():
        usuario.activo = True
        usuario.save(update_fields=["activo", "fecha_actualizacion"])
        registrar_bitacora(
            usuario=actor,
            modulo="Usuarios",
            accion="ACTIVAR_USUARIO",
            descripcion=(
                f"Usuario '{usuario.usuario}' activado correctamente por "
                f"{actor.nombre} {actor.apellido}."
            ),
        )
