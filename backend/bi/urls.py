from django.urls import path

from .views import ResumenView

urlpatterns = [
    path("bi/resumen", ResumenView.as_view()),
]
