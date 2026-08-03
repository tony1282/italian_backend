from rest_framework import serializers
from .models import Usuario

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import AuthenticationFailed

from rest_framework.permissions import BasePermission

from rest_framework_simplejwt.serializers import TokenRefreshSerializer



class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = [
            "id",
            "nombre",
            "apellido",
            "usuario",
            "email",
            "password",
            "rol",
            "activo",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        extra_kwargs = {
            "password": {
                "write_only": True
            }
        }
    
        
    def create(self, validated_data):
        password = validated_data.pop("password")
        
        usuario = Usuario.objects.create_user(
            password=password,
            **validated_data
        )
        
        return usuario

class LoginSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
                
        data = super().validate(attrs)
        
        usuario = self.user
        
        
        if not usuario.activo:
            raise AuthenticationFailed(
                "Este usuario esta inactivo"
            )
            
        return {
            "success": True,
            "message": "Inicio de sesión correcto.",
            "data": {
                "access": data["access"],
                "refresh": data["refresh"],
                "usuario":{
                    "id": usuario.id,
                    "nombre": usuario.nombre,
                    "rol": usuario.rol,    
                    }
                }
            }

        
        
class RefreshSerializer(TokenRefreshSerializer):

    def validate(self, attrs):

        data = super().validate(attrs)

        response = {
            "success": True,
            "data": {
                "access": data["access"]
            }
        }

        if "refresh" in data:
            response["data"]["refresh"] = data["refresh"]

        return response