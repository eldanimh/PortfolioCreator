from django.contrib import admin
from .models import UserProfile, ContenidoData


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'github_username', 'gitlab_username')
    search_fields = ('user__username',)


@admin.register(ContenidoData)
class ContenidoDataAdmin(admin.ModelAdmin):
    list_display = ('recurso', 'usuario', 'fecha_creacion')
    search_fields = ('recurso',)
    list_filter = ('fecha_creacion',)
