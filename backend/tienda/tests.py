"""Pruebas de la API (Fase 2): login, precios por perfil, checkout, estados, CRM y permisos."""

import os
from datetime import timedelta

from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APITestCase

from crm.models import Cliente, Oportunidad, Prospecto
from cuentas.models import Usuario
from logistica.models import Despacho
from tienda.models import Pedido, Producto

CLAVE = "clave-de-prueba-123"


class ApiTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        os.environ["DEMO_PASSWORD"] = CLAVE
        call_command("seed_demo", verbosity=0, stdout=open(os.devnull, "w"))

    def login(self, email):
        r = self.client.post("/api/auth/login", {"email": email, "password": CLAVE}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + r.data["access"])
        return r.data["usuario"]

    def logout(self):
        self.client.credentials()

    def checkout(self, producto, cantidad, **extra):
        cuerpo = {
            "items": [{"id_producto": producto.pk, "cantidad": cantidad}],
            "fecha_entrega_solicitada": str(timezone.localdate() + timedelta(days=2)),
            **extra,
        }
        return self.client.post("/api/pedidos", cuerpo, format="json")


class AuthTests(ApiTestCase):
    def test_login_y_me(self):
        usuario = self.login("compras@hospitalregional.cl")
        self.assertEqual(usuario["rol"], "cliente")
        self.assertEqual(usuario["tipo_cliente"], "B2B")
        self.assertEqual(self.client.get("/api/auth/me").data["email"], "compras@hospitalregional.cl")

    def test_login_incorrecto(self):
        r = self.client.post("/api/auth/login", {"email": "admin@cofrial.cl", "password": "mala"}, format="json")
        self.assertEqual(r.status_code, 401)

    def test_me_sin_sesion(self):
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)


class TiendaTests(ApiTestCase):
    def _precio(self, sku):
        return next(p for p in self.client.get("/api/productos").data if p["sku"] == sku)["precio"]

    def test_precios_por_perfil(self):
        visitante = self._precio("CAR-001")
        self.login("cliente@gmail.com")
        b2c = self._precio("CAR-001")
        self.logout()
        self.login("compras@hospitalregional.cl")
        b2b = self._precio("CAR-001")
        self.assertEqual(visitante, b2c)
        self.assertLess(b2b, b2c)

    def test_filtro_categoria(self):
        r = self.client.get("/api/productos", {"categoria": "Insumos hospitalarios"})
        self.assertEqual({p["sku"][:3] for p in r.data}, {"HOS"})

    def test_checkout_b2b_descuenta_stock_y_lo_ve_el_vendedor(self):
        producto = Producto.objects.get(sku="HOS-001")
        stock = producto.stock_disponible
        self.login("compras@hospitalregional.cl")

        sin_oc = self.checkout(producto, 5)
        self.assertEqual(sin_oc.status_code, 400)
        self.assertIn("numero_oc", sin_oc.data)

        r = self.checkout(producto, 5, numero_oc="OC-2026-0042")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.data["estado"], "Recibido")
        self.assertEqual(r.data["canal"], "web")
        self.assertEqual(r.data["total"], 5 * r.data["detalles"][0]["precio_unitario"])
        producto.refresh_from_db()
        self.assertEqual(producto.stock_disponible, stock - 5)
        self.assertEqual(self.client.get("/api/mis-pedidos").data[0]["id_pedido"], r.data["id_pedido"])

        self.logout()
        self.login("vendedor@cofrial.cl")
        ids = [p["id_pedido"] for p in self.client.get("/api/pedidos", {"estado": "Recibido"}).data]
        self.assertIn(r.data["id_pedido"], ids)

    def test_checkout_b2c_ignora_oc(self):
        self.login("cliente@gmail.com")
        r = self.checkout(Producto.objects.get(sku="FRU-001"), 2, numero_oc="NO-APLICA")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertIsNone(r.data["numero_oc"])

    def test_stock_insuficiente_409_y_no_cambia_nada(self):
        producto = Producto.objects.get(sku="HOS-002")
        pedidos = Pedido.objects.count()
        self.login("cliente@gmail.com")
        r = self.checkout(producto, producto.stock_disponible + 1)
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.data["faltantes"][0]["disponible"], producto.stock_disponible)
        self.assertEqual(Pedido.objects.count(), pedidos)
        self.assertEqual(Producto.objects.get(pk=producto.pk).stock_disponible, producto.stock_disponible)

    def test_checkout_sin_sesion(self):
        self.assertEqual(self.checkout(Producto.objects.get(sku="FRU-001"), 1).status_code, 401)

    def test_fecha_pasada(self):
        self.login("cliente@gmail.com")
        r = self.client.post(
            "/api/pedidos",
            {"items": [{"id_producto": 1, "cantidad": 1}], "fecha_entrega_solicitada": "2020-01-01"},
            format="json",
        )
        self.assertEqual(r.status_code, 400)


class PedidosInternosTests(ApiTestCase):
    def _nuevo_pedido(self):
        self.login("cliente@gmail.com")
        id_pedido = self.checkout(Producto.objects.get(sku="LAC-001"), 1).data["id_pedido"]
        self.logout()
        return id_pedido

    def test_flujo_completo_de_estados(self):
        url = f"/api/pedidos/{self._nuevo_pedido()}"
        self.login("despacho@cofrial.cl")

        salto = self.client.patch(url, {"estado": "Entregado"}, format="json")
        self.assertEqual(salto.status_code, 409)

        self.assertEqual(self.client.patch(url, {"estado": "En preparación"}, format="json").status_code, 200)
        sin_camion = self.client.patch(url, {"estado": "Despachado"}, format="json")
        self.assertEqual(sin_camion.status_code, 400)

        r = self.client.patch(url, {"estado": "Despachado", "camion_id": "CAM-007"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.data["despacho"]["camion_id"], "CAM-007")
        self.assertIsNone(r.data["despacho"]["fecha_entrega"])
        flota = {c["camion_id"]: c for c in self.client.get("/api/flota").data}
        self.assertEqual(len(flota), 50)
        self.assertIn(r.data["id_pedido"], [d["id_pedido"] for d in flota["CAM-007"]["despachos"]])

        r = self.client.patch(url, {"estado": "Entregado"}, format="json")
        self.assertEqual(r.data["estado"], "Entregado")
        self.assertIsNotNone(Despacho.objects.get(pedido_id=r.data["id_pedido"]).fecha_entrega)

    def test_permisos_por_rol(self):
        url = f"/api/pedidos/{self._nuevo_pedido()}"
        self.login("vendedor@cofrial.cl")
        self.assertEqual(self.client.patch(url, {"estado": "En preparación"}, format="json").status_code, 403)
        self.assertEqual(self.client.get("/api/flota").status_code, 403)
        self.logout()

        self.login("despacho@cofrial.cl")
        self.assertEqual(self.client.get("/api/prospectos").status_code, 403)
        self.logout()

        self.login("cliente@gmail.com")
        for ruta in ("/api/pedidos", "/api/clientes", "/api/oportunidades", "/api/camiones"):
            self.assertEqual(self.client.get(ruta).status_code, 403, ruta)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.logout()

        self.login("compras@hospitalregional.cl")
        self.assertEqual(self.client.get(url).status_code, 403)  # pedido de otro cliente
        self.logout()

        self.login("admin@cofrial.cl")
        for ruta in ("/api/pedidos", "/api/clientes", "/api/oportunidades", "/api/camiones", "/api/despachos"):
            self.assertEqual(self.client.get(ruta).status_code, 200, ruta)

    def test_pedido_ingresado_por_vendedor(self):
        self.login("vendedor@cofrial.cl")
        hospital = Cliente.objects.get(usuario__email="compras@hospitalregional.cl")
        r = self.checkout(Producto.objects.get(sku="HOS-003"), 3, id_cliente=hospital.pk, numero_oc="OC-77")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.data["canal"], "vendedor")


class CrmTests(ApiTestCase):
    def test_ganado_crea_cliente_b2b_y_usuario(self):
        self.login("vendedor@cofrial.cl")
        oportunidad = Oportunidad.objects.get(prospecto__razon_social="Supermercado Angol Express")
        url = f"/api/oportunidades/{oportunidad.pk}"

        falta = self.client.patch(url, {"etapa": "Ganado"}, format="json")
        self.assertEqual(falta.status_code, 400)
        self.assertIn("direccion_despacho", falta.data)

        r = self.client.patch(
            url, {"etapa": "Ganado", "direccion_despacho": "Av. O'Higgins 100, Angol"}, format="json"
        )
        self.assertEqual(r.status_code, 200, r.content)
        self.assertIsNotNone(r.data["fecha_cierre"])
        prospecto = Prospecto.objects.get(pk=oportunidad.prospecto_id)
        self.assertEqual(r.data["prospecto"]["id_cliente"], prospecto.cliente_id)
        self.assertEqual(prospecto.cliente.tipo.nombre, "B2B")
        self.assertEqual(prospecto.cliente.vendedor_id, prospecto.vendedor_id)
        self.assertEqual(Usuario.objects.get(email=prospecto.email).rol.nombre, "cliente")

        # El nuevo cliente puede entrar y ve precios institucionales
        self.logout()
        self.assertEqual(self.login(prospecto.email)["tipo_cliente"], "B2B")

    def test_cambio_de_etapa_simple(self):
        self.login("vendedor@cofrial.cl")
        oportunidad = Oportunidad.objects.get(prospecto__razon_social="Hotel Lago Villarrica")
        r = self.client.patch(f"/api/oportunidades/{oportunidad.pk}", {"etapa": "Contactado"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.data["etapa"], "Contactado")
        self.assertIsNone(r.data["fecha_cierre"])
        self.assertEqual(len(self.client.get("/api/etapas").data), 6)

    def test_crud_prospecto_e_interaccion(self):
        self.login("vendedor@cofrial.cl")
        r = self.client.post(
            "/api/prospectos",
            {"razon_social": "Colegio Pucón", "contacto": "Ana Soto", "email": "ana@colegiopucon.cl",
             "monto_estimado": 1500000},
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        id_oportunidad = self.client.get(f"/api/prospectos/{r.data['id_prospecto']}").data["oportunidades"][0][
            "id_oportunidad"
        ]
        i = self.client.post(
            "/api/interacciones",
            {"id_oportunidad": id_oportunidad, "tipo": "llamada", "detalle": "Primer contacto."},
            format="json",
        )
        self.assertEqual(i.status_code, 201, i.content)
        lista = self.client.get("/api/interacciones", {"oportunidad": id_oportunidad}).data
        self.assertEqual(len(lista), 1)
        sin_destino = self.client.post("/api/interacciones", {"tipo": "correo", "detalle": "x"}, format="json")
        self.assertEqual(sin_destino.status_code, 400)
        self.assertEqual(self.client.delete(f"/api/prospectos/{r.data['id_prospecto']}").status_code, 204)

    def test_crud_cliente(self):
        self.login("vendedor@cofrial.cl")
        sin_rut = self.client.post(
            "/api/clientes",
            {"email": "compras@clinicasur.cl", "tipo": "B2B", "nombre_razon_social": "Clínica Sur",
             "telefono": "+56452000000", "direccion_despacho": "Prat 100, Temuco"},
            format="json",
        )
        self.assertEqual(sin_rut.status_code, 400)
        r = self.client.post(
            "/api/clientes",
            {"email": "compras@clinicasur.cl", "tipo": "B2B", "nombre_razon_social": "Clínica Sur",
             "rut": "76.111.222-3", "telefono": "+56452000000", "direccion_despacho": "Prat 100, Temuco"},
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.data["email"], "compras@clinicasur.cl")
        self.assertIsNotNone(r.data["id_vendedor"])
        url = f"/api/clientes/{r.data['id_cliente']}"
        self.assertEqual(self.client.patch(url, {"telefono": "+56999999999"}, format="json").data["telefono"],
                         "+56999999999")
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertFalse(Usuario.objects.filter(email="compras@clinicasur.cl").exists())

        hospital = Cliente.objects.get(usuario__email="compras@hospitalregional.cl")
        self.assertEqual(self.client.delete(f"/api/clientes/{hospital.pk}").status_code, 409)


class BiTests(ApiTestCase):
    def test_resumen_solo_administrador(self):
        self.login("vendedor@cofrial.cl")
        self.assertEqual(self.client.get("/api/bi/resumen").status_code, 403)

    def test_resumen_cruza_ventas_con_alertas(self):
        from logistica.models import TelemetriaRuta

        # Pedido nuevo, despachado en un camion que reporta ruptura de frio
        self.login("cliente@gmail.com")
        pedido = self.checkout(Producto.objects.get(sku="CAR-001"), 10).data
        self.logout()
        self.login("admin@cofrial.cl")
        url = f"/api/pedidos/{pedido['id_pedido']}"
        self.client.patch(url, {"estado": "En preparación"}, format="json")
        self.client.patch(url, {"estado": "Despachado", "camion_id": "CAM-050"}, format="json")

        antes = self.client.get("/api/bi/resumen").data
        self.assertEqual(antes["operativo"]["camiones_en_alerta"], 0)
        self.assertNotIn(pedido["id_pedido"], [p["id_pedido"] for p in antes["cruce"]["pedidos_en_riesgo"]])

        TelemetriaRuta.objects.create(
            camion_id="CAM-050", temp_camara=-9.5, lat=-38.74, long=-72.6, combustible_pct=60, alerta_ruptura_frio=True
        )
        r = self.client.get("/api/bi/resumen")
        self.assertEqual(r.status_code, 200, r.content)
        d = r.data
        self.assertEqual(d["operativo"]["camiones_en_alerta_ids"], ["CAM-050"])
        self.assertEqual(d["operativo"]["alertas_ultima_hora"], 1)
        self.assertEqual(sum(m["camiones_en_alerta"] for m in d["operativo"]["alertas_por_minuto"]), 1)
        en_riesgo = {p["id_pedido"]: p for p in d["cruce"]["pedidos_en_riesgo"]}
        self.assertEqual(float(en_riesgo[pedido["id_pedido"]]["monto"]), float(pedido["total"]))
        self.assertGreaterEqual(float(d["cruce"]["monto_en_riesgo"]), float(pedido["total"]))
        self.assertGreater(d["cruce"]["pct_despachos_con_alerta"], antes["cruce"]["pct_despachos_con_alerta"])
        self.assertEqual(len(d["comercial"]["ventas_por_dia"]), 7)
        self.assertGreaterEqual(float(d["comercial"]["ventas_hoy"]), float(pedido["total"]))
        self.assertEqual({c["nombre"] for c in d["comercial"]["por_canal"]}, {"web", "vendedor"})
        self.assertEqual(len(d["comercial"]["pipeline"]["etapas"]), 6)


class IaTests(ApiTestCase):
    def _contacto(self, texto):
        return self.client.post("/api/contacto", {"texto": texto}, format="json")

    def test_sin_clave_queda_sin_clasificar_y_no_se_cae(self):
        from django.test import override_settings

        self.login("cliente@gmail.com")
        with override_settings(GROQ_API_KEY=""):
            r = self._contacto("Hola, quiero saber cuándo llega mi pedido.")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertFalse(r.data["clasificado"])
        self.assertEqual(r.data["categoria"], "sin_clasificar")

    def test_groq_caido_queda_sin_clasificar(self):
        from unittest import mock

        from django.test import override_settings

        self.login("cliente@gmail.com")
        with override_settings(GROQ_API_KEY="clave-falsa"), mock.patch(
            "ia.cliente._llamar_groq", side_effect=TimeoutError("sin red")
        ):
            r = self._contacto("Llegó la carne descongelada.")
        self.assertEqual(r.status_code, 201)
        self.assertFalse(r.data["clasificado"])

    def test_clasifica_y_aparece_en_el_crm_con_prioridad(self):
        import json
        from unittest import mock

        from django.test import override_settings

        respuesta = json.dumps(
            {"categoria": "reclamo_temperatura", "prioridad": "media", "resumen": "Carne llegó descongelada.",
             "respuesta_sugerida": "Lamentamos lo ocurrido. Revisaremos el despacho de inmediato."}
        )
        self.login("cliente@gmail.com")
        with override_settings(GROQ_API_KEY="clave-falsa"), mock.patch("ia.cliente._llamar_groq", return_value=respuesta):
            r = self._contacto("Llegó la carne descongelada.")
            solo = self.client.post("/api/ia/clasificar", {"texto": "Llegó la carne descongelada."}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.data["categoria"], "reclamo_temperatura")
        self.assertEqual(r.data["prioridad"], "alta")  # la regla de negocio sube la prioridad
        self.assertEqual(solo.data["categoria"], "reclamo_temperatura")
        self.logout()

        self.login("vendedor@cofrial.cl")
        lista = self.client.get("/api/interacciones", {"web": 1}).data
        self.assertEqual(lista[0]["id_interaccion"], r.data["id_interaccion"])
        self.assertEqual(lista[0]["tipo"], "reclamo")
        self.assertEqual(lista[0]["clasificacion"], {"categoria": "reclamo_temperatura", "prioridad": "alta"})
        self.assertEqual(lista[0]["cliente_nombre"], "María José González")

    def test_contacto_exige_cliente(self):
        self.assertEqual(self._contacto("Hola, una consulta.").status_code, 401)
        self.login("vendedor@cofrial.cl")
        self.assertEqual(self._contacto("Hola, una consulta.").status_code, 403)
