from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("cuentas.urls")),
    path("api/", include("tienda.urls")),
    path("api/", include("crm.urls")),
    path("api/", include("logistica.urls")),
    path("api/", include("bi.urls")),
    path("api/", include("ia.urls")),
]
