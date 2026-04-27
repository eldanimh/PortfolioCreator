from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    """Perfil extendido del usuario con tokens de GitHub y GitLab"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    github_token = models.CharField(max_length=255, blank=True, default='')
    gitlab_token = models.CharField(max_length=255, blank=True, default='')
    github_username = models.CharField(max_length=150, blank=True, default='')
    gitlab_username = models.CharField(max_length=150, blank=True, default='')
    openalex_token = models.CharField(max_length=255, blank=True, default='')
    gemini_api_key = models.CharField(max_length=255, blank=True, default='')


    def __str__(self):
        return f"Perfil de {self.user.username}"


class ContenidoData(models.Model):
    """Tabla Contenido-Data según la especificación"""
    recurso = models.CharField(max_length=255, unique=True)
    contenido = models.TextField(blank=True, default='')
    usuario = models.CharField(max_length=255, blank=True, default='')
    contraseña = models.CharField(max_length=255, blank=True, default='')
    token_GitLab = models.CharField(max_length=255, blank=True, default='')
    token_GitHub = models.CharField(max_length=255, blank=True, default='')
    plataforma = models.CharField(max_length=100, blank=True, default='')
    nombre_repo = models.CharField(max_length=255, blank=True, default='')
    url_repo = models.URLField(max_length=500, blank=True, default='')
    Obras = models.TextField(blank=True, default='')
    Autor = models.TextField(blank=True, default='')
    Fuentes = models.TextField(blank=True, default='')
    instituciones = models.TextField(blank=True, default='')
    topics = models.TextField(blank=True, default='')
    keywords = models.TextField(blank=True, default='')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Contenido'
        verbose_name_plural = 'Contenidos'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return self.recurso
