from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    """Perfil extendido del usuario con tokens de GitHub y GitLab"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    github_token = models.CharField(max_length=255, blank=True, default='')
    gitlab_token = models.CharField(max_length=255, blank=True, default='')
    github_username = models.CharField(max_length=150, blank=True, default='')
    gitlab_username = models.CharField(max_length=150, blank=True, default='')

    def __str__(self):
        return f"Perfil de {self.user.username}"


class ContenidoData(models.Model):
    """Tabla Contenido-Data según la especificación"""
    recurso = models.CharField(max_length=255, unique=True)
    contenido = models.TextField(blank=True, default='')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Contenido'
        verbose_name_plural = 'Contenidos'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return self.recurso
