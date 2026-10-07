# Importamos los formularios de Django
from django import forms
# Importamos el modelo User de Django (para el formulario de registro)
from django.contrib.auth.models import User
# Importamos UserCreationForm: formulario base que Django trae para crear usuarios
from django.contrib.auth.forms import UserCreationForm
# Importamos nuestros modelos propios
from .models import UserProfile, ContenidoData
from .seguridad import url_externa_segura
from django.conf import settings


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
        fields = ['github_token', 'gitlab_url', 'gitlab_token', 'openalex_token', 'ia_base_url', 'nvidia_api_key', 'ia_model', 'github_username', 'gitlab_username', 'lm_studio_url']
        # Widgets: controlan CÓMO se renderiza cada campo en el HTML
        widgets = {
            # PasswordInput: muestra el campo como tipo password (****) para ocultar el token
            'github_token': forms.PasswordInput(attrs={'placeholder': 'Token de GitHub'}),
            'gitlab_url': forms.URLInput(attrs={'placeholder': 'https://gitlab.com'}),
            'gitlab_token': forms.PasswordInput(attrs={'placeholder': 'Token de GitLab'}),
            'openalex_token': forms.PasswordInput(attrs={'placeholder': 'API Key de OpenAlex (Opcional)'}),
            'ia_base_url': forms.URLInput(attrs={'placeholder': 'Se detecta por la API Key'}),
            'nvidia_api_key': forms.PasswordInput(attrs={'placeholder': 'nvapi-…, sk-…, gsk_…, AIza…'}),
            'ia_model': forms.TextInput(attrs={'placeholder': 'El recomendado para tu proveedor'}),
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
            'ia_base_url': 'URL del proveedor de IA (opcional)',
            'nvidia_api_key': 'API Key de IA',
            'ia_model': 'Modelo de IA (opcional)',
            'github_username': 'Nombre de usuario en GitHub',
            'gitlab_username': 'Nombre de usuario en GitLab',
            'lm_studio_url': 'URL de servidor LM Studio Local',
        }

    # Campos secretos: PasswordInput no reenvía su valor al navegador, así que
    # si llegan vacíos se conserva lo guardado (salvo que se marque "Eliminar")
    SECRET_FIELDS = ['github_token', 'gitlab_token', 'openalex_token', 'nvidia_api_key']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # LM Studio solo funciona en local: fuera de ahí ni se muestra el campo
        if not settings.ALLOW_LOCAL_LLM:
            self.fields.pop('lm_studio_url', None)

        orden = []
        for name in list(self.fields):
            orden.append(name)
            if name in self.SECRET_FIELDS and getattr(self.instance, name, ''):
                self.fields[name].widget.attrs['placeholder'] = 'Guardado ••••••  (déjalo vacío para mantenerlo)'
                self.fields['borrar_' + name] = forms.BooleanField(
                    required=False, label='Eliminar el valor guardado'
                )
                orden.append('borrar_' + name)
        self.order_fields(orden)

    def clean(self):
        cleaned = super().clean()
        for name in self.SECRET_FIELDS:
            if name not in self.fields:
                continue
            if cleaned.get('borrar_' + name):
                cleaned[name] = ''
            elif not cleaned.get(name):
                cleaned[name] = getattr(self.instance, name, '')
        return cleaned

    def _post_clean(self):
        super()._post_clean()
        # construct_instance ignora los campos que no vienen en el POST;
        # se asignan a mano para que "Eliminar" funcione siempre
        for name in self.SECRET_FIELDS:
            if name in self.cleaned_data:
                setattr(self.instance, name, self.cleaned_data[name])

    def clean_ia_base_url(self):
        """Solo URLs https públicas para el proveedor de IA (anti-SSRF)"""
        url = (self.cleaned_data.get('ia_base_url') or '').strip().rstrip('/')
        if url and not url_externa_segura(url):
            raise forms.ValidationError(
                "Usa la URL https pública de una API compatible con OpenAI (sin puerto ni parámetros)."
            )
        return url

    def clean_gitlab_url(self):
        """Rechaza URLs de GitLab que no sean https públicas (anti-SSRF)"""
        url = (self.cleaned_data.get('gitlab_url') or '').strip()
        if url and not url_externa_segura(url):
            raise forms.ValidationError(
                "Usa una URL https pública de tu GitLab (sin puerto ni parámetros)."
            )
        return url


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
