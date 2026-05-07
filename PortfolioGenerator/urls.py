# Importamos el admin de Django y las funciones de URL
from django.contrib import admin
from django.urls import path, include

# URLs del PROYECTO (nivel raíz). Delegan a las apps.
urlpatterns = [
    # Panel de administración de Django (accesible en /admin/)
    path('admin/', admin.site.urls),
    # URLs de django-allauth para login social (GitHub, Google)
    # Genera rutas como /accounts/github/login/, /accounts/google/login/, etc.
    path('accounts/', include('allauth.urls')),
    # Incluye TODAS las URLs de nuestra app portfolioCV (definidas en portfolioCV/urls.py)
    # Al usar '' (vacío), las URLs de la app se montan en la raíz del sitio
    path('', include('portfolioCV.urls')),
]
