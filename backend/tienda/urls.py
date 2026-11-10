from django.urls import path

from .views import CategoriasView, MisPedidosView, PedidoDetalleView, PedidosView, ProductosView

urlpatterns = [
    path("categorias", CategoriasView.as_view()),
    path("productos", ProductosView.as_view()),
    path("pedidos", PedidosView.as_view()),
    path("pedidos/<int:id_pedido>", PedidoDetalleView.as_view()),
    path("mis-pedidos", MisPedidosView.as_view()),
]
