from decimal import (
    Decimal,
    InvalidOperation
)

import uuid

from rest_framework import (
    mixins,
    viewsets,
    status
)

from rest_framework.decorators import action

from rest_framework.response import Response

from rest_framework.permissions import IsAuthenticated

from rest_framework.pagination import PageNumberPagination

from django.utils import timezone

from django.db import transaction

from django.db.models import Sum

from ventas.models import Venta

from .models import (
    CorteCaja,
    MovimientoCaja
)

from .serializers import (
    CorteCajaSerializer,
    MovimientoCajaSerializer
)

from cajas.models import Caja

from bitacora.services import registrar_bitacora


class CorteCajaPagination(
    PageNumberPagination
):

    page_size = 50

    max_page_size = 200


class CorteCajaViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):

    queryset = CorteCaja.objects.none()

    serializer_class = CorteCajaSerializer

    def get_queryset(self):

        qs = (
            CorteCaja.objects
            .select_related(
                "caja",
                "usuario"
            )
            .order_by("-fecha_inicio")
        )

        if self.request.user.rol not in (0, 1):

            qs = qs.filter(
                usuario=self.request.user
            )

        return qs

    permission_classes = [
        IsAuthenticated
    ]

    pagination_class = CorteCajaPagination

    # ==========================================================
    # ABRIR CAJA
    # ==========================================================

    @action(
        detail=False,
        methods=["post"],
        url_path="abrir"
    )
    def abrir(self, request):

        caja_id = request.data.get(
            "caja_id"
        )

        efectivo_inicial = request.data.get(
            "efectivo_inicial"
        )

        if not caja_id:

            return Response(
                {
                    "success": False,
                    "message": (
                        "El parámetro caja_id "
                        "es obligatorio."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:

            uuid.UUID(
                str(caja_id)
            )

        except (
            TypeError,
            ValueError,
            AttributeError
        ):

            return Response(
                {
                    "success": False,
                    "message": (
                        "El identificador de la "
                        "caja no es un UUID válido."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if efectivo_inicial is None:

            return Response(
                {
                    "success": False,
                    "message": (
                        "El efectivo inicial "
                        "es obligatorio."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:

            efectivo_inicial = Decimal(
                str(efectivo_inicial)
            )

        except (
            InvalidOperation,
            ValueError,
            TypeError
        ):

            return Response(
                {
                    "success": False,
                    "message": (
                        "El efectivo inicial no es "
                        "un valor numérico válido."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if efectivo_inicial < 0:

            return Response(
                {
                    "success": False,
                    "message": (
                        "El efectivo inicial "
                        "no puede ser negativo."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():

            try:

                caja = (
                    Caja.objects
                    .select_for_update()
                    .get(
                        id=caja_id
                    )
                )

            except Caja.DoesNotExist:

                return Response(
                    {
                        "success": False,
                        "message": (
                            "La caja no existe."
                        )
                    },
                    status=status.HTTP_404_NOT_FOUND
                )

            corte_abierto = (
                CorteCaja.objects
                .filter(
                    caja=caja,
                    fecha_fin__isnull=True
                )
                .exists()
            )

            if corte_abierto:

                return Response(
                    {
                        "success": False,
                        "message": (
                            "Ya existe un corte abierto "
                            "para esta caja."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            corte = (
                CorteCaja.objects.create(
                    caja=caja,
                    usuario=request.user,
                    efectivo_inicial=efectivo_inicial
                )
            )

            caja.estado = "ABIERTA"

            caja.save(
                update_fields=["estado"]
            )

            registrar_bitacora(
                usuario=request.user,
                modulo="Caja",
                accion="APERTURA_CAJA",
                descripcion=(
                    f"Caja '{caja.nombre}' "
                    f"abierta correctamente por "
                    f"{request.user.nombre} "
                    f"{request.user.apellido}. "
                    f"Efectivo inicial: "
                    f"${efectivo_inicial}"
                )
            )

        return Response(
            {
                "success": True,
                "message": (
                    "Caja abierta correctamente."
                ),
                "data": {
                    "corte_id": corte.id,
                    "fecha_inicio": corte.fecha_inicio
                }
            },
            status=status.HTTP_201_CREATED
        )

    # ==========================================================
    # CERRAR CAJA
    # ==========================================================

    @action(
        detail=False,
        methods=["post"],
        url_path="cerrar"
    )
    def cerrar(self, request):

        caja_id = request.data.get(
            "caja_id"
        )

        efectivo_final = request.data.get(
            "efectivo_final"
        )

        if not caja_id:

            return Response(
                {
                    "success": False,
                    "message": (
                        "El parámetro caja_id "
                        "es obligatorio."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:

            uuid.UUID(
                str(caja_id)
            )

        except (
            TypeError,
            ValueError,
            AttributeError
        ):

            return Response(
                {
                    "success": False,
                    "message": (
                        "El identificador de la "
                        "caja no es un UUID válido."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if efectivo_final is None:

            return Response(
                {
                    "success": False,
                    "message": (
                        "El efectivo final "
                        "es obligatorio."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:

            efectivo_final = Decimal(
                str(efectivo_final)
            )

        except (
            InvalidOperation,
            ValueError,
            TypeError
        ):

            return Response(
                {
                    "success": False,
                    "message": (
                        "El efectivo final no es "
                        "un valor numérico válido."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if efectivo_final < 0:

            return Response(
                {
                    "success": False,
                    "message": (
                        "El efectivo final "
                        "no puede ser negativo."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():

            try:

                corte = (
                    CorteCaja.objects
                    .select_for_update()
                    .select_related("caja")
                    .get(
                        caja_id=caja_id,
                        fecha_fin__isnull=True
                    )
                )

            except CorteCaja.DoesNotExist:

                return Response(
                    {
                        "success": False,
                        "message": (
                            "No existe un corte "
                            "abierto."
                        )
                    },
                    status=status.HTTP_404_NOT_FOUND
                )

            # Solo el usuario que abrió el corte
            # o un administrador puede cerrarlo.

            if (
                request.user.rol not in (0, 1)
                and corte.usuario_id != request.user.id
            ):

                return Response(
                    {
                        "success": False,
                        "message": (
                            "Solo puedes cerrar "
                            "la caja que tú abriste."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN
                )

            total_ventas_efectivo = (
                Venta.objects
                .filter(
                    corte_caja=corte,
                    metodo_pago__nombre="EFECTIVO",
                    estado="COMPLETADA"
                )
                .aggregate(
                    total=Sum("total")
                )["total"]
                or Decimal("0.00")
            )

            total_reembolsos_efectivo = (
                MovimientoCaja.objects
                .filter(
                    corte_caja=corte,
                    metodo_pago__nombre="EFECTIVO",
                    tipo="REEMBOLSO"
                )
                .aggregate(
                    total=Sum("monto")
                )["total"]
                or Decimal("0.00")
            )

            efectivo_esperado = (
                corte.efectivo_inicial
                + total_ventas_efectivo
                - total_reembolsos_efectivo
            )

            diferencia = (
                efectivo_final
                - efectivo_esperado
            )

            corte.efectivo_final = (
                efectivo_final
            )

            corte.diferencia = diferencia

            corte.fecha_fin = timezone.now()

            corte.save(
                update_fields=[
                    "efectivo_final",
                    "diferencia",
                    "fecha_fin"
                ]
            )

            corte.caja.estado = "CERRADA"

            corte.caja.save(
                update_fields=["estado"]
            )

            registrar_bitacora(
                usuario=request.user,
                modulo="Caja",
                accion="CIERRE_CAJA",
                descripcion=(
                    f"Caja '{corte.caja.nombre}' "
                    f"cerrada correctamente por "
                    f"{request.user.nombre} "
                    f"{request.user.apellido}. "
                    f"Efectivo esperado: "
                    f"${efectivo_esperado}. "
                    f"Efectivo contado: "
                    f"${efectivo_final}. "
                    f"Diferencia: "
                    f"${diferencia}"
                )
            )

        return Response(
            {
                "success": True,
                "message": (
                    "Caja cerrada correctamente."
                ),
                "data": {
                    "corte_id": corte.id,
                    "efectivo_esperado":
                        efectivo_esperado,
                    "efectivo_contado":
                        efectivo_final,
                    "diferencia":
                        diferencia
                }
            },
            status=status.HTTP_200_OK
        )

    # ==========================================================
    # CORTE ACTIVO
    # ==========================================================

    @action(
        detail=False,
        methods=["get"],
        url_path="corte/activo"
    )
    def activo(self, request):

        caja_id = request.query_params.get(
            "caja_id"
        )

        if not caja_id:

            return Response(
                {
                    "success": False,
                    "message": (
                        "El parámetro caja_id "
                        "es obligatorio."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:

            uuid.UUID(
                str(caja_id)
            )

        except (
            ValueError,
            TypeError,
            AttributeError
        ):

            return Response(
                {
                    "success": False,
                    "message": (
                        "El parámetro caja_id "
                        "no es un UUID válido."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        corte = (
            self.get_queryset()
            .filter(
                caja_id=caja_id,
                fecha_fin__isnull=True
            )
            .first()
        )

        if not corte:

            return Response(
                {
                    "success": False,
                    "message": (
                        "No existe un corte abierto "
                        "para esta caja."
                    )
                },
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(
            corte
        )

        return Response(
            {
                "success": True,
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )

    # ==========================================================
    # HISTORIAL DE CORTES
    # ==========================================================

    @action(
        detail=False,
        methods=["get"],
        url_path=(
            r"cajas/(?P<caja_id>[^/.]+)/cortes"
        )
    )
    def historial(
        self,
        request,
        caja_id
    ):

        try:

            uuid.UUID(
                str(caja_id)
            )

        except (
            ValueError,
            TypeError,
            AttributeError
        ):

            return Response(
                {
                    "success": False,
                    "message": (
                        "El identificador de la "
                        "caja no es un UUID válido."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        cortes = (
            self.get_queryset()
            .filter(
                caja_id=caja_id
            )
        )

        paginator = CorteCajaPagination()

        pagina = paginator.paginate_queryset(
            cortes,
            request
        )

        serializer = self.get_serializer(
            pagina,
            many=True
        )

        return paginator.get_paginated_response(
            serializer.data
        )

    # ==========================================================
    # MOVIMIENTOS DE CAJA
    # ==========================================================

    @action(
        detail=True,
        methods=["get"],
        url_path="movimientos"
    )
    def movimiento(
        self,
        request,
        pk=None
    ):

        try:

            uuid.UUID(
                str(pk)
            )

        except (
            ValueError,
            TypeError,
            AttributeError
        ):

            return Response(
                {
                    "success": False,
                    "message": (
                        "El identificador del corte "
                        "no es un UUID válido."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        corte = self.get_object()

        movimientos = (
            MovimientoCaja.objects
            .select_related(
                "metodo_pago",
                "usuario",
                "devolucion"
            )
            .filter(
                corte_caja=corte
            )
            .order_by(
                "-fecha"
            )
        )

        serializer = (
            MovimientoCajaSerializer(
                movimientos,
                many=True
            )
        )

        return Response(
            {
                "success": True,
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )