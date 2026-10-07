# Importamos el módulo de modelos de Django para definir las tablas de la BD
from django.db import models
# Importamos el modelo User que Django trae integrado (tiene username, password, email)
from django.contrib.auth.models import User
# Importamos las signals para ejecutar código automáticamente cuando se crea un usuario
from django.db.models.signals import post_save
# Importamos el decorador receiver para conectar la signal con nuestra función
from django.dispatch import receiver
# Campo que cifra su valor en la BD
from .fields import EncryptedCharField


# ─── Tabla UserProfile ─────────────────────────────────────
# Extiende el modelo User de Django con campos adicionales (tokens de API)
class UserProfile(models.Model):
    """Perfil extendido del usuario con tokens de GitHub y GitLab"""
    # Relación 1-a-1 con User: cada usuario tiene exactamente 1 perfil
    # on_delete=CASCADE: si se borra el User, se borra este perfil también
    # related_name='profile': permite acceder desde user.profile
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    # Token de acceso personal de GitHub (para autenticarse en la API)
    github_token = EncryptedCharField(blank=True, default='')
    # Token de acceso personal de GitLab
    gitlab_token = EncryptedCharField(blank=True, default='')
    # Nombre de usuario en GitHub (para construir URLs de repos)
    github_username = models.CharField(max_length=150, blank=True, default='')
    # URL de la instancia GitLab (gitlab.com, GitLab autoalojado, etc.)
    gitlab_url = models.CharField(max_length=255, blank=True, default='')
    # Nombre de usuario en GitLab
    gitlab_username = models.CharField(max_length=150, blank=True, default='')
    # API Key de OpenAlex (opcional, para evitar límites de peticiones)
    openalex_token = EncryptedCharField(blank=True, default='')
    # API Key del proveedor de IA en la nube (se llama nvidia_* por historia: NVIDIA es el
    # proveedor por defecto, pero vale la de cualquier API compatible con OpenAI)
    nvidia_api_key = EncryptedCharField(blank=True, default='')
    # URL base del proveedor de IA (vacío = NVIDIA) y modelo (vacío = settings.NVIDIA_MODEL)
    ia_base_url = models.CharField(max_length=255, blank=True, default='')
    ia_model = models.CharField(max_length=150, blank=True, default='')
    # URL del servidor LM Studio local (para IA en local, ej: http://127.0.0.1:1234)
    lm_studio_url = models.CharField(max_length=255, blank=True, default='')

    # Representación en texto del modelo (se muestra en el panel admin)
    def __str__(self):
        return f"Perfil de {self.user.username}"

    @property
    def ia(self):
        """Proveedor y modelo de IA que se usarán (para mostrarlos en las plantillas)"""
        from .ia import configuracion_ia
        return configuracion_ia(self)


# ─── Tabla ContenidoData ───────────────────────────────────
# Tabla principal de recursos/contenidos según la especificación del spec.md
class ContenidoData(models.Model):
    """Tabla Contenido-Data según la especificación"""
    # Nombre del recurso. Es único POR USUARIO (ver Meta.constraints): Paco y Dani pueden
    # tener cada uno su "notas". Se usa como identificador en la URL: /<recurso>/, que
    # muestra el del usuario que ha iniciado sesión
    recurso = models.CharField(max_length=255)
    # Contenido del recurso (texto libre o JSON serializado para el CV profesional)
    contenido = models.TextField(blank=True, default='')
    # Nombre del usuario que creó este recurso
    usuario = models.CharField(max_length=255, blank=True, default='')
    # Campo de contraseña (especificado en spec.md para la tabla Contenido-Data)
    contraseña = models.CharField(max_length=255, blank=True, default='')
    # Tokens almacenados por recurso (campos del spec.md)
    token_GitLab = models.CharField(max_length=255, blank=True, default='')
    token_GitHub = models.CharField(max_length=255, blank=True, default='')
    # Plataforma de origen (GitHub, GitLab, OpenAlex)
    plataforma = models.CharField(max_length=100, blank=True, default='')
    # Nombre y URL del repositorio asociado
    nombre_repo = models.CharField(max_length=255, blank=True, default='')
    url_repo = models.URLField(max_length=500, blank=True, default='')
    # Campos de OpenAlex: obras, autores, fuentes, instituciones, temas, palabras clave
    Obras = models.TextField(blank=True, default='')
    Autor = models.TextField(blank=True, default='')
    Fuentes = models.TextField(blank=True, default='')
    instituciones = models.TextField(blank=True, default='')
    topics = models.TextField(blank=True, default='')
    keywords = models.TextField(blank=True, default='')
    # Fecha de creación: se pone AUTOMÁTICAMENTE al crear el registro (auto_now_add)
    # No se puede modificar después. Django la guarda en UTC y la convierte a Europe/Madrid
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    # Metadatos del modelo: nombre en español y orden por defecto
    class Meta:
        verbose_name = 'Contenido'           # Nombre singular en el admin
        verbose_name_plural = 'Contenidos'   # Nombre plural en el admin
        ordering = ['-fecha_creacion']       # Ordenar por fecha descendente (más reciente primero)
        constraints = [
            models.UniqueConstraint(fields=['recurso', 'usuario'], name='recurso_unico_por_usuario'),
        ]

    # Representación en texto (lo que se ve en el admin de Django)
    def __str__(self):
        return self.recurso


# ─── Signal: Crear UserProfile automáticamente ────────────
# Esta función se ejecuta AUTOMÁTICAMENTE cada vez que se crea un nuevo User
# (incluido cuando se registra con login social como GitHub/Google)
@receiver(post_save, sender=User)  # Se activa después de guardar un User
def crear_perfil_usuario(sender, instance, created, **kwargs):
    """Crea un UserProfile automáticamente al crear un usuario (incluido social login)"""
    if created:  # Solo cuando el User es NUEVO (no cuando se actualiza)
        UserProfile.objects.get_or_create(user=instance)  # Crea el perfil si no existe
