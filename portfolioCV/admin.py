# Importamos el módulo admin de Django para registrar modelos en el panel de administración
from django.contrib import admin
# Importamos nuestros modelos para registrarlos
from .models import UserProfile, ContenidoData


# ─── Panel Admin para UserProfile ──────────────────────────
# @admin.register: decorador que registra el modelo en /admin/
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    # Columnas que se muestran en la lista de perfiles en el admin
    list_display = ('user', 'github_username', 'gitlab_username')
    # Campos por los que se puede buscar en el buscador del admin
    search_fields = ('user__username',)  # user__username = buscar en el campo username del modelo User relacionado


# ─── Panel Admin para ContenidoData ────────────────────────
@admin.register(ContenidoData)
class ContenidoDataAdmin(admin.ModelAdmin):
    # Columnas visibles en la lista
    list_display = ('recurso', 'usuario', 'fecha_creacion')
    # Buscador: permite buscar por nombre de recurso
    search_fields = ('recurso',)
    # Filtro lateral: permite filtrar por fecha de creación
    list_filter = ('fecha_creacion',)
