import re

from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from crm.models import Cliente, Interaccion
from cuentas.permisos import EsCliente

from .cliente import SIN_CLASIFICAR, clasificar

PREFIJO_WEB = "Mensaje web del cliente:"
_RE_CLASIFICACION = re.compile(r"^Clasificación IA: (\w+)(?: \(prioridad (\w+)\))?$", re.MULTILINE)

# Tipo de interaccion (catalogo del CRM) segun la categoria que entrega la IA
TIPO_POR_CATEGORIA = {
    "reclamo_temperatura": "reclamo",
    "reclamo_entrega": "reclamo",
    "cotizacion": "cotización",
}


def armar_detalle(texto: str, c: dict) -> str:
    """Texto que queda en interacciones.detalle (el modelo de datos no tiene columnas propias para la IA)."""
    lineas = [f"{PREFIJO_WEB} {texto}", "---"]
    if c["clasificado"]:
        lineas.append(f"Clasificación IA: {c['categoria']} (prioridad {c['prioridad']})")
        if c["resumen"]:
            lineas.append(f"Resumen: {c['resumen']}")
        lineas.append(f"Respuesta sugerida: {c['respuesta_sugerida']}")
    else:
        lineas.append(f"Clasificación IA: {SIN_CLASIFICAR}")
    return "\n".join(lineas)


def leer_clasificacion(detalle: str) -> dict | None:
    """Recupera {categoria, prioridad} de una interaccion creada desde el formulario web; None si no lo es."""
    if not detalle.startswith(PREFIJO_WEB):
        return None
    m = _RE_CLASIFICACION.search(detalle)
    if not m:
        return {"categoria": SIN_CLASIFICAR, "prioridad": None}
    return {"categoria": m.group(1), "prioridad": m.group(2)}


class TextoSerializer(serializers.Serializer):
    texto = serializers.CharField(min_length=5, max_length=2000)


class ClasificarView(APIView):
    """POST /api/ia/clasificar {texto} -> {categoria, prioridad, resumen, respuesta_sugerida}"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        datos = TextoSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        return Response(clasificar(datos.validated_data["texto"]))


class ContactoView(APIView):
    """
    POST /api/contacto {texto}  (formulario "Ayuda" de la tienda)
    Clasifica con IA y crea la interaccion ligada al cliente. Si la IA falla, queda "sin clasificar".
    """

    permission_classes = [EsCliente]

    def post(self, request):
        datos = TextoSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        cliente = Cliente.objects.filter(usuario=request.user).first()
        if cliente is None:
            raise PermissionDenied("Tu cuenta no tiene un perfil de cliente asociado.")

        texto = datos.validated_data["texto"].strip()
        c = clasificar(texto)
        interaccion = Interaccion.objects.create(
            cliente=cliente,
            tipo=TIPO_POR_CATEGORIA.get(c["categoria"], "correo"),
            detalle=armar_detalle(texto, c),
        )
        return Response(
            {
                "id_interaccion": interaccion.id_interaccion,
                "clasificado": c["clasificado"],
                "categoria": c["categoria"],
                "prioridad": c["prioridad"],
                "resumen": c["resumen"],
                "respuesta_sugerida": c["respuesta_sugerida"],
            },
            status=status.HTTP_201_CREATED,
        )
