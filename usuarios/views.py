from django.db import IntegrityError

from rest_framework import viewsets, status 
from rest_framework.response import Response 
from rest_framework.decorators import action 
from rest_framework.permissions import IsAuthenticated 
from rest_framework.views import APIView 
from rest_framework.throttling import AnonRateThrottle 
 
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView 
from rest_framework_simplejwt.tokens import RefreshToken 
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken 
 
from .models import Usuario 
from .serializers import ( 
    UsuarioSerializer, 
    UsuarioReadSerializer, 
    CrearAdminSerializer, 
    LoginSerializer, 
    RefreshSerializer, 
) 
from .permissions import IsAdmin, IsSuperAdmin 
from .services import ( 
    crear_usuario, 
    crear_admin, 
    modificar_usuario, 
    desactivar_usuario, 
    activar_usuario, 
    validar_no_automodificacion, 
    validar_jerarquia, 
) 
from bitacora.services import registrar_bitacora 
from config.exceptions import BusinessException 
 
 
# ============================================================== 
# THROTTLE LOGIN 
# ============================================================== 
 
class LoginThrottle(AnonRateThrottle): 
    scope = "login" 
 
 
# ============================================================== 
# USUARIOS 
# ============================================================== 
 
class UsuarioViewSet(viewsets.ModelViewSet): 
 
    queryset = Usuario.objects.none() 
    serializer_class = UsuarioSerializer 
    permission_classes = [IsAuthenticated, IsAdmin] 

    # ----------------------------------------------------------
    # SIN DELETE: el ciclo de vida se maneja con
    # activar/desactivar, no con el método HTTP DELETE (mismo
    # criterio que Productos y Variantes).
    # ----------------------------------------------------------

    http_method_names = [
        "get",
        "post",
        "put",
        "patch",
        "head",
        "options"
    ]
 
    def get_queryset(self): 
        user = self.request.user 
 
        if user.rol == 0: 
            # SuperAdmin ve admins y empleados (no otros superadmins) 
            return Usuario.objects.filter(rol__in=(1, 2)) 
 
        if user.rol == 1: 
            # Admin en LIST y RETRIEVE solo ve empleados: no debe
            # poder consultar el detalle de otro Admin, aunque no
            # pueda modificarlo (evita fuga de información entre
            # administradores).
            if self.action in ("list", "retrieve"): 
                return Usuario.objects.filter(rol=2) 
 
            # Para operaciones de escritura (update, activar,
            # desactivar) sí puede encontrar admins y empleados,
            # para que se ejecuten las validaciones de jerarquía
            # y automodificación y respondan con el error correcto.
            return Usuario.objects.filter(rol__in=(1, 2)) 
 
        # Empleados no tienen acceso efectivo al ViewSet 
        return Usuario.objects.none() 
 
    def get_serializer_class(self): 
        if self.action in ("list", "retrieve"): 
            return UsuarioReadSerializer 
        return UsuarioSerializer 
 
    # ========================================================== 
    # CREAR USUARIO (empleado) 
    # ========================================================== 
 
    def create(self, request, *args, **kwargs): 
        serializer = self.get_serializer(data=request.data) 
 
        if not serializer.is_valid(): 
            return Response( 
                {"success": False, "message": "No se pudo registrar el usuario.", "data": serializer.errors}, 
                status=status.HTTP_400_BAD_REQUEST, 
            ) 
 
        try:
            crear_usuario(serializer, request.user)
        except IntegrityError:
            return Response(
                {"success": False, "message": "Ya existe un usuario con ese nombre de usuario o correo.", "data": None},
                status=status.HTTP_400_BAD_REQUEST,
            )
 
        return Response( 
            {"success": True, "message": "Usuario registrado correctamente.", "data": None}, 
            status=status.HTTP_201_CREATED, 
        ) 
 
    # ========================================================== 
    # CREAR ADMINISTRADOR 
    # ========================================================== 
 
    @action(detail=False, methods=["post"], url_path="crear-admin", permission_classes=[IsSuperAdmin]) 
    def crear_admin(self, request): 
        serializer = CrearAdminSerializer(data=request.data) 
 
        if not serializer.is_valid(): 
            return Response( 
                {"success": False, "message": "No se pudo crear el administrador.", "data": serializer.errors}, 
                status=status.HTTP_400_BAD_REQUEST, 
            ) 
 
        try:
            crear_admin(serializer, request.user)
        except IntegrityError:
            return Response(
                {"success": False, "message": "Ya existe un usuario con ese nombre de usuario o correo.", "data": None},
                status=status.HTTP_400_BAD_REQUEST,
            )
 
        return Response( 
            {"success": True, "message": "Administrador creado correctamente.", "data": None}, 
            status=status.HTTP_201_CREATED, 
        ) 
 
    # ========================================================== 
    # MODIFICAR USUARIO 
    # ========================================================== 
 
    def update(self, request, *args, **kwargs): 
        partial = kwargs.pop("partial", False) 
        instance = self.get_object() 
 
        try: 
            validar_no_automodificacion(request.user, instance, "modificarte") 
            validar_jerarquia(request.user, instance) 
        except BusinessException as e: 
            return Response( 
                {"success": False, "message": str(e), "data": None}, 
                status=status.HTTP_403_FORBIDDEN, 
            ) 
 
        serializer = self.get_serializer(instance, data=request.data, partial=partial) 
 
        if not serializer.is_valid(): 
            return Response( 
                {"success": False, "message": "No se pudo modificar el usuario.", "data": serializer.errors}, 
                status=status.HTTP_400_BAD_REQUEST, 
            ) 
 
        try:
            modificar_usuario(serializer, request.user)
        except IntegrityError:
            return Response(
                {"success": False, "message": "Ya existe un usuario con ese nombre de usuario o correo.", "data": None},
                status=status.HTTP_400_BAD_REQUEST,
            )
 
        return Response( 
            {"success": True, "message": "Usuario modificado correctamente.", "data": None}, 
            status=status.HTTP_200_OK, 
        ) 
 
    # ========================================================== 
    # ACTIVAR USUARIO 
    # ========================================================== 
 
    @action(detail=True, methods=["post"], url_path="activar") 
    def activar(self, request, pk=None): 
        usuario = self.get_object() 
 
        try: 
            validar_no_automodificacion(request.user, usuario, "activarte a ti mismo") 
            validar_jerarquia(request.user, usuario) 
        except BusinessException as e: 
            return Response( 
                {"success": False, "message": str(e), "data": None}, 
                status=status.HTTP_403_FORBIDDEN, 
            ) 

        try:
            activar_usuario(usuario, request.user)
        except BusinessException as e: 
            return Response( 
                {"success": False, "message": str(e), "data": None}, 
                status=status.HTTP_400_BAD_REQUEST, 
            ) 
 
        return Response( 
            {"success": True, "message": "Usuario activado correctamente.", "data": None}, 
            status=status.HTTP_200_OK, 
        ) 

    # ========================================================== 
    # DESACTIVAR USUARIO 
    # ========================================================== 

    @action(detail=True, methods=["post"], url_path="desactivar")
    def desactivar(self, request, pk=None):
        usuario = self.get_object()

        try:
            validar_no_automodificacion(request.user, usuario, "desactivar tu propio usuario")
            validar_jerarquia(request.user, usuario)
        except BusinessException as e:
            return Response(
                {"success": False, "message": str(e), "data": None},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            desactivar_usuario(usuario, request.user)
        except BusinessException as e:
            return Response(
                {"success": False, "message": str(e), "data": None},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"success": True, "message": "Usuario desactivado correctamente.", "data": None},
            status=status.HTTP_200_OK,
        )
 
 
# ============================================================== 
# LOGIN 
# ============================================================== 
 
class LoginView(TokenObtainPairView): 
 
    serializer_class = LoginSerializer 
    throttle_classes = [LoginThrottle] 
 
    def post(self, request, *args, **kwargs): 
        response = super().post(request, *args, **kwargs) 
 
        if response.status_code == status.HTTP_200_OK: 
            usuario_data = response.data.get("data", {}).get("usuario") 
            if usuario_data: 
                try: 
                    usuario = Usuario.objects.get(id=usuario_data["id"]) 
                    registrar_bitacora( 
                        usuario=usuario, 
                        modulo="Autenticación", 
                        accion="INICIO_SESION", 
                        descripcion=f"Inicio de sesión exitoso del usuario '{usuario.usuario}'.", 
                    ) 
                except Usuario.DoesNotExist: 
                    pass 
 
        return response 
 
 
# ============================================================== 
# LOGOUT 
# ============================================================== 
 
class LogoutView(APIView): 
 
    permission_classes = [IsAuthenticated] 
 
    def post(self, request): 
        refresh_token = request.data.get("refresh") 
 
        if not refresh_token: 
            return Response( 
                {"success": False, "message": "El refresh token es obligatorio.", "data": None}, 
                status=status.HTTP_400_BAD_REQUEST, 
            ) 
 
        try: 
            token = RefreshToken(refresh_token) 
 
            token_user_id = str(token.payload.get("user_id")) 
            if token_user_id != str(request.user.id): 
                return Response( 
                    {"success": False, "message": "El token no pertenece al usuario autenticado.", "data": None}, 
                    status=status.HTTP_403_FORBIDDEN, 
                ) 
 
            token.blacklist() 
 
            registrar_bitacora( 
                usuario=request.user, 
                modulo="Autenticación", 
                accion="CIERRE_SESION", 
                descripcion=f"El usuario '{request.user.usuario}' cerró sesión correctamente.", 
            ) 
 
            return Response( 
                {"success": True, "message": "Sesión cerrada correctamente.", "data": None}, 
                status=status.HTTP_200_OK, 
            ) 
        except (TokenError, InvalidToken): 
            return Response( 
                {"success": False, "message": "Token inválido o expirado.", "data": None}, 
                status=status.HTTP_400_BAD_REQUEST, 
            ) 
 
 
# ============================================================== 
# USUARIO AUTENTICADO 
# ============================================================== 
 
class MeView(APIView): 
 
    permission_classes = [IsAuthenticated] 
 
    def get(self, request): 
        u = request.user 
        return Response( 
            { 
                "success": True, 
                "message": "Usuario obtenido correctamente.", 
                "data": { 
                    "id": str(u.id), 
                    "nombre": u.nombre, 
                    "apellido": u.apellido, 
                    "usuario": u.usuario, 
                    "email": u.email, 
                    "rol": u.rol, 
                    "activo": u.activo, 
                }, 
            }, 
            status=status.HTTP_200_OK, 
        ) 
 
 
# ============================================================== 
# REFRESH TOKEN 
# ============================================================== 
 
class RefreshView(TokenRefreshView): 
    serializer_class = RefreshSerializer