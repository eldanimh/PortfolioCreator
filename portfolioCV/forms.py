# Importamos los formularios de Django
from django import forms
# Importamos el modelo User de Django (para el formulario de registro)
from django.contrib.auth.models import User
# Importamos UserCreationForm: formulario base que Django trae para crear usuarios
from django.contrib.auth.forms import UserCreationForm
# Importamos nuestros modelos propios
from .models import UserProfile, ContenidoData


# ─── Formulario de Registro ────────────────────────────────
# Hereda de UserCreationForm que ya trae campos de username, password1, password2
class RegistroForm(UserCreationForm):
    """Formulario de registro de usuario"""
    # Añadimos un campo extra de email (obligatorio)
    email = forms.EmailField(required=True)

    class Meta:
        model = User  # Este formulario crea/modifica objetos de tipo User
        fields = ['username', 'email', 'password1', 'password2']  # Campos visibles en el HTML


# ─── Formulario de Tokens/API Keys ─────────────────────────
# ModelForm: genera automáticamente campos HTML a partir de los campos del modelo
class TokensForm(forms.ModelForm):
    """Formulario para configurar los tokens de GitHub y GitLab"""
    class Meta:
        model = UserProfile  # Este formulario edita objetos de tipo UserProfile
        # Campos que se muestran en el formulario (orden en que aparecen)
        fields = ['github_token', 'gitlab_url', 'gitlab_token', 'openalex_token', 'nvidia_api_key', 'github_username', 'gitlab_username', 'lm_studio_url']
        # Widgets: controlan CÓMO se renderiza cada campo en el HTML
        widgets = {
            # PasswordInput: muestra el campo como tipo password (****) para ocultar el token
            'github_token': forms.PasswordInput(attrs={'placeholder': 'Token de GitHub'}),
            'gitlab_url': forms.URLInput(attrs={'placeholder': 'https://gitlab.com'}),
            'gitlab_token': forms.PasswordInput(attrs={'placeholder': 'Token de GitLab'}),
            'openalex_token': forms.PasswordInput(attrs={'placeholder': 'API Key de OpenAlex (Opcional)'}),
            'nvidia_api_key': forms.PasswordInput(attrs={'placeholder': 'API Key de NVIDIA'}),
            # TextInput: campo de texto normal (el username no es secreto)
            'github_username': forms.TextInput(attrs={'placeholder': 'Usuario de GitHub'}),
            'gitlab_username': forms.TextInput(attrs={'placeholder': 'Usuario de GitLab'}),
            # URLInput: campo de tipo URL (valida que sea una URL válida)
            'lm_studio_url': forms.URLInput(attrs={'placeholder': 'http://127.0.0.1:1234'}),
        }
        # Labels: texto que aparece encima de cada campo en el formulario HTML
        labels = {
            'github_token': 'GitHub Personal Access Token',
            'gitlab_url': 'URL de tu GitLab (vacío = gitlab.com)',
            'gitlab_token': 'GitLab Personal Access Token',
            'openalex_token': 'OpenAlex API Key',
            'nvidia_api_key': 'NVIDIA API Key',
            'github_username': 'Nombre de usuario en GitHub',
            'gitlab_username': 'Nombre de usuario en GitLab',
            'lm_studio_url': 'URL de servidor LM Studio Local',
        }


# ─── Formulario de Contenido/Recurso ──────────────────────
# Formulario para crear un recurso nuevo en la tabla ContenidoData
class ContenidoForm(forms.ModelForm):
    """Formulario para crear un nuevo recurso"""
    class Meta:
        model = ContenidoData  # Este formulario crea objetos de tipo ContenidoData
        fields = ['recurso', 'contenido']  # Solo mostramos nombre y contenido
        widgets = {
            # TextInput: campo de una línea para el nombre del recurso
            'recurso': forms.TextInput(attrs={'placeholder': 'Nombre del recurso'}),
            # Textarea: campo multilínea para el contenido (4 filas de alto)
            'contenido': forms.Textarea(attrs={'placeholder': 'Contenido del recurso', 'rows': 4}),
        }
