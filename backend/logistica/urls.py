from django.urls import path

from .views import CamionesView, DespachosView, FlotaView

urlpatterns = [
    path("camiones", CamionesView.as_view()),
    path("despachos", DespachosView.as_view()),
    path("flota", FlotaView.as_view()),
]
