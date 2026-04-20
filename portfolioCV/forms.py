from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile, ContenidoData


class RegistroForm(UserCreationForm):
    """Formulario de registro de usuario"""
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


class TokensForm(forms.ModelForm):
    """Formulario para configurar los tokens de GitHub y GitLab"""
    class Meta:
        model = UserProfile
        fields = ['github_token', 'gitlab_token', 'github_username', 'gitlab_username']
        widgets = {
            'github_token': forms.PasswordInput(attrs={'placeholder': 'Token de GitHub'}),
            'gitlab_token': forms.PasswordInput(attrs={'placeholder': 'Token de GitLab URJC'}),
            'github_username': forms.TextInput(attrs={'placeholder': 'Usuario de GitHub'}),
            'gitlab_username': forms.TextInput(attrs={'placeholder': 'Usuario de GitLab URJC'}),
        }
        labels = {
            'github_token': 'GitHub Personal Access Token',
            'gitlab_token': 'GitLab URJC Personal Access Token',
            'github_username': 'Nombre de usuario en GitHub',
            'gitlab_username': 'Nombre de usuario en GitLab URJC',
        }


class ContenidoForm(forms.ModelForm):
    """Formulario para crear un nuevo recurso"""
    class Meta:
        model = ContenidoData
        fields = ['recurso', 'contenido']
        widgets = {
            'recurso': forms.TextInput(attrs={'placeholder': 'Nombre del recurso'}),
            'contenido': forms.Textarea(attrs={'placeholder': 'Contenido del recurso', 'rows': 4}),
        }
