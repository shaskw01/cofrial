from django.db import transaction
from rest_framework import serializers

from tienda.models import TIPO_B2B, TipoCliente

from .models import ETAPA_PROSPECTO, Cliente, EtapaPipeline, Interaccion, Oportunidad, Prospecto, Vendedor
from .servicios import actualizar_oportunidad, crear_usuario_cliente

TIPOS_INTERACCION = ("llamada", "correo", "reunión", "cotización", "reclamo")


class VendedorSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="usuario.email", read_only=True)

    class Meta:
        model = Vendedor
        fields = ["id_vendedor", "nombre", "telefono", "email"]


class EtapaSerializer(serializers.ModelSerializer):
    class Meta:
        model = EtapaPipeline
        fields = ["id_etapa", "nombre", "orden"]


class ClienteSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(max_length=120, write_only=True, required=False)
    password = serializers.CharField(write_only=True, required=False, min_length=8, trim_whitespace=False)
    tipo = serializers.SlugRelatedField(slug_field="nombre", queryset=TipoCliente.objects.all())
    id_vendedor = serializers.PrimaryKeyRelatedField(
        source="vendedor", queryset=Vendedor.objects.all(), required=False, allow_null=True
    )
    vendedor_nombre = serializers.CharField(source="vendedor.nombre", read_only=True, default=None)
    rut = serializers.CharField(max_length=12, required=False, allow_null=True, allow_blank=True)
    total_pedidos = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = Cliente
        fields = [
            "id_cliente", "email", "password", "tipo", "id_vendedor", "vendedor_nombre",
            "nombre_razon_social", "rut", "telefono", "direccion_despacho", "total_pedidos",
        ]

    def to_representation(self, instance):
        datos = super().to_representation(instance)
        datos["email"] = instance.usuario.email
        return datos

    def validate_rut(self, rut):
        rut = (rut or "").strip() or None
        if rut:
            repetido = Cliente.objects.filter(rut=rut)
            if self.instance:
                repetido = repetido.exclude(pk=self.instance.pk)
            if repetido.exists():
                raise serializers.ValidationError("Ya existe un cliente con este RUT.")
        return rut

    def validate(self, attrs):
        def valor(campo):
            return attrs[campo] if campo in attrs else getattr(self.instance, campo, None)

        if self.instance is None and not attrs.get("email"):
            raise serializers.ValidationError({"email": "El correo es obligatorio para crear la cuenta del cliente."})

        solicitante = Vendedor.objects.filter(usuario=self.context["request"].user).first()
        if self.instance is None and "vendedor" not in attrs and solicitante:
            attrs["vendedor"] = solicitante  # el vendedor que crea al cliente queda asignado

        if valor("tipo").nombre == TIPO_B2B:
            errores = {}
            if not valor("rut"):
                errores["rut"] = "El RUT es obligatorio para clientes B2B."
            if not valor("vendedor"):
                errores["id_vendedor"] = "Los clientes B2B deben tener un vendedor asignado."
            if errores:
                raise serializers.ValidationError(errores)
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        email = validated_data.pop("email")
        password = validated_data.pop("password", None)
        usuario = crear_usuario_cliente(email, password)
        return Cliente.objects.create(usuario=usuario, **validated_data)

    def update(self, instance, validated_data):
        # El correo (login) y la contraseña no se cambian desde el CRM.
        validated_data.pop("email", None)
        validated_data.pop("password", None)
        return super().update(instance, validated_data)


class OportunidadBreveSerializer(serializers.ModelSerializer):
    etapa = serializers.CharField(source="etapa.nombre")

    class Meta:
        model = Oportunidad
        fields = ["id_oportunidad", "etapa", "monto_estimado", "fecha_creacion", "fecha_cierre"]


class ProspectoSerializer(serializers.ModelSerializer):
    id_vendedor = serializers.PrimaryKeyRelatedField(source="vendedor", queryset=Vendedor.objects.all(), required=False)
    vendedor_nombre = serializers.CharField(source="vendedor.nombre", read_only=True)
    id_cliente = serializers.IntegerField(source="cliente_id", read_only=True)
    oportunidades = OportunidadBreveSerializer(many=True, read_only=True)
    # Opcional al crear: abre de inmediato una oportunidad en la etapa "Prospecto" (aparece en el Kanban).
    monto_estimado = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, write_only=True, required=False
    )

    class Meta:
        model = Prospecto
        fields = [
            "id_prospecto", "id_vendedor", "vendedor_nombre", "id_cliente", "razon_social", "rut",
            "contacto", "email", "telefono", "oportunidades", "monto_estimado",
        ]

    def validate(self, attrs):
        if self.instance is None and "vendedor" not in attrs:
            solicitante = Vendedor.objects.filter(usuario=self.context["request"].user).first()
            if solicitante is None:
                raise serializers.ValidationError({"id_vendedor": "Indica el vendedor responsable del prospecto."})
            attrs["vendedor"] = solicitante
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        monto = validated_data.pop("monto_estimado", None)
        prospecto = super().create(validated_data)
        if monto is not None:
            Oportunidad.objects.create(
                prospecto=prospecto, etapa=EtapaPipeline.objects.get(nombre=ETAPA_PROSPECTO), monto_estimado=monto
            )
        return prospecto

    def update(self, instance, validated_data):
        validated_data.pop("monto_estimado", None)
        return super().update(instance, validated_data)


class ProspectoBreveSerializer(serializers.ModelSerializer):
    id_vendedor = serializers.IntegerField(source="vendedor_id")
    vendedor_nombre = serializers.CharField(source="vendedor.nombre")
    id_cliente = serializers.IntegerField(source="cliente_id")

    class Meta:
        model = Prospecto
        fields = [
            "id_prospecto", "razon_social", "rut", "contacto", "email", "telefono",
            "id_vendedor", "vendedor_nombre", "id_cliente",
        ]


class OportunidadSerializer(serializers.ModelSerializer):
    id_prospecto = serializers.PrimaryKeyRelatedField(source="prospecto", queryset=Prospecto.objects.all())
    prospecto = ProspectoBreveSerializer(read_only=True)
    etapa = serializers.SlugRelatedField(slug_field="nombre", queryset=EtapaPipeline.objects.all(), required=False)
    id_etapa = serializers.IntegerField(source="etapa_id", read_only=True)
    monto_estimado = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    # Solo se usan al pasar a "Ganado", para crear el cliente B2B
    direccion_despacho = serializers.CharField(max_length=200, write_only=True, required=False, allow_blank=True)
    telefono = serializers.CharField(max_length=20, write_only=True, required=False, allow_blank=True)
    rut = serializers.CharField(max_length=12, write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Oportunidad
        fields = [
            "id_oportunidad", "id_prospecto", "prospecto", "etapa", "id_etapa", "monto_estimado",
            "fecha_creacion", "fecha_cierre", "direccion_despacho", "telefono", "rut",
        ]
        read_only_fields = ["fecha_creacion", "fecha_cierre"]

    def validate_id_prospecto(self, prospecto):
        if self.instance is not None and prospecto.pk != self.instance.prospecto_id:
            raise serializers.ValidationError("No se puede cambiar el prospecto de una oportunidad.")
        solicitante = self.context["request"].user
        if solicitante.rol.nombre == "vendedor" and prospecto.vendedor.usuario_id != solicitante.pk:
            raise serializers.ValidationError("Este prospecto pertenece a otro vendedor.")
        return prospecto

    @transaction.atomic
    def create(self, validated_data):
        extras = {c: validated_data.pop(c, None) for c in ("direccion_despacho", "telefono", "rut")}
        etapa = validated_data.pop("etapa", None)
        inicial = EtapaPipeline.objects.get(nombre=ETAPA_PROSPECTO)
        oportunidad = Oportunidad.objects.create(etapa=inicial, **validated_data)
        if etapa is not None and etapa.pk != inicial.pk:
            oportunidad = actualizar_oportunidad(oportunidad, etapa=etapa, **extras)
        return oportunidad

    def update(self, instance, validated_data):
        return actualizar_oportunidad(
            instance,
            etapa=validated_data.get("etapa"),
            monto_estimado=validated_data.get("monto_estimado"),
            direccion_despacho=validated_data.get("direccion_despacho"),
            telefono=validated_data.get("telefono"),
            rut=validated_data.get("rut"),
        )


class InteraccionSerializer(serializers.ModelSerializer):
    id_oportunidad = serializers.PrimaryKeyRelatedField(
        source="oportunidad", queryset=Oportunidad.objects.all(), required=False, allow_null=True
    )
    id_cliente = serializers.PrimaryKeyRelatedField(
        source="cliente", queryset=Cliente.objects.all(), required=False, allow_null=True
    )
    tipo = serializers.ChoiceField(choices=TIPOS_INTERACCION)

    class Meta:
        model = Interaccion
        fields = ["id_interaccion", "id_oportunidad", "id_cliente", "tipo", "detalle", "fecha"]
        read_only_fields = ["fecha"]

    def validate(self, attrs):
        if not attrs.get("oportunidad") and not attrs.get("cliente"):
            raise serializers.ValidationError("La interacción debe ligarse a una oportunidad o a un cliente.")
        return attrs
