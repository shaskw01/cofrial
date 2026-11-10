from django.contrib.auth import authenticate
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from crm.models import Cliente, Vendedor


def perfil_de(usuario) -> dict:
    """Datos de sesion que usa el frontend: rol y, si es cliente, su perfil comercial."""
    cliente = Cliente.objects.select_related("tipo").filter(usuario=usuario).first()
    vendedor = Vendedor.objects.filter(usuario=usuario).first()
    nombre = usuario.email
    if cliente:
        nombre = cliente.nombre_razon_social
    elif vendedor:
        nombre = vendedor.nombre
    return {
        "id_usuario": usuario.id_usuario,
        "email": usuario.email,
        "rol": usuario.rol.nombre,
        "nombre": nombre,
        "tipo_cliente": cliente.tipo.nombre if cliente else None,
        "id_cliente": cliente.id_cliente if cliente else None,
        "id_vendedor": vendedor.id_vendedor if vendedor else None,
        "direccion_despacho": cliente.direccion_despacho if cliente else None,
    }


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False)


class LoginView(APIView):
    """POST /api/auth/login  {email, password} -> {access, refresh, usuario}"""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        datos = LoginSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        usuario = authenticate(
            request,
            username=datos.validated_data["email"].strip().lower(),
            password=datos.validated_data["password"],
        )
        if usuario is None:
            return Response({"detail": "Correo o contraseña incorrectos."}, status=status.HTTP_401_UNAUTHORIZED)
        refresh = RefreshToken.for_user(usuario)
        return Response({"access": str(refresh.access_token), "refresh": str(refresh), "usuario": perfil_de(usuario)})


class MeView(APIView):
    """GET /api/auth/me -> rol y tipo de cliente del usuario logueado."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(perfil_de(request.user))
