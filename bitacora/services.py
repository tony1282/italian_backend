from .models import Bitacora


def registrar_bitacora(
    usuario,
    modulo,
    accion,
    descripcion
):
    return Bitacora.objects.create(
        usuario=usuario,
        modulo=modulo,
        accion=accion,
        descripcion=descripcion
    )