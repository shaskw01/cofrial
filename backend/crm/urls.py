from rest_framework.routers import SimpleRouter

from .views import (
    ClienteViewSet,
    EtapaViewSet,
    InteraccionViewSet,
    OportunidadViewSet,
    ProspectoViewSet,
    VendedorViewSet,
)

router = SimpleRouter(trailing_slash=False)
router.register("vendedores", VendedorViewSet, basename="vendedores")
router.register("etapas", EtapaViewSet, basename="etapas")
router.register("clientes", ClienteViewSet, basename="clientes")
router.register("prospectos", ProspectoViewSet, basename="prospectos")
router.register("oportunidades", OportunidadViewSet, basename="oportunidades")
router.register("interacciones", InteraccionViewSet, basename="interacciones")

urlpatterns = router.urls
