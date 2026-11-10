from django.urls import path

from .views import ClasificarView, ContactoView

urlpatterns = [
    path("ia/clasificar", ClasificarView.as_view()),
    path("contacto", ContactoView.as_view()),
]
