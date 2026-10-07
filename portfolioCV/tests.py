from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import UserProfile, ContenidoData
from .forms import RegistroForm, TokensForm, ContenidoForm

class ModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword123')
    
    def test_user_profile_creation(self):
        """Test that UserProfile is created automatically or can be created and __str__ works"""
        # Our app might rely on a signal, or we create it manually
        if not hasattr(self.user, 'profile'):
            UserProfile.objects.create(user=self.user, nvidia_api_key='test-key')
        
        self.assertEqual(str(self.user.profile), "Perfil de testuser")
        self.assertTrue(isinstance(self.user.profile, UserProfile))

    def test_contenido_data_creation(self):
        """Test ContenidoData creation and __str__"""
        contenido = ContenidoData.objects.create(
            recurso="Repo de Prueba",
            contenido="Este es el contenido del repo"
        )
        self.assertEqual(str(contenido), "Repo de Prueba")
        self.assertEqual(contenido.contenido, "Este es el contenido del repo")

class FormTests(TestCase):
    def test_registro_form_valid(self):
        data = {
            'username': 'newuser',
            'email': 'test@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!'
        }
        form = RegistroForm(data=data)
        self.assertTrue(form.is_valid())

    def test_tokens_form_valid(self):
        data = {
            'github_token': 'ghp_abc123',
            'nvidia_api_key': 'nv_123'
        }
        form = TokensForm(data=data)
        # All fields are blank=True, so it should be valid even if empty or partial
        self.assertTrue(form.is_valid())

    def test_tokens_form_conserva_tokens_vacios(self):
        """Guardar solo un token no debe borrar los que ya estaban guardados"""
        user = User.objects.create_user(username='tokenuser', password='testpassword123')
        profile = user.profile
        profile.github_token = 'ghp_guardado'
        profile.save()

        form = TokensForm(data={'gitlab_token': 'glpat_nuevo'}, instance=profile)
        self.assertTrue(form.is_valid())
        form.save()

        profile.refresh_from_db()
        self.assertEqual(profile.github_token, 'ghp_guardado')
        self.assertEqual(profile.gitlab_token, 'glpat_nuevo')

    def test_tokens_form_eliminar_token(self):
        """La casilla "Eliminar" borra el token guardado"""
        user = User.objects.create_user(username='tokenuser2', password='testpassword123')
        profile = user.profile
        profile.github_token = 'ghp_guardado'
        profile.save()

        form = TokensForm(data={'borrar_github_token': 'on'}, instance=profile)
        self.assertTrue(form.is_valid())
        form.save()

        profile.refresh_from_db()
        self.assertEqual(profile.github_token, '')

    def test_contenido_form_valid(self):
        data = {
            'recurso': 'Mi Recurso Único',
            'contenido': 'Info importante'
        }
        form = ContenidoForm(data=data)
        self.assertTrue(form.is_valid())
        
    def test_contenido_form_invalid(self):
        # Missing recurso which is required
        data = {
            'contenido': 'Info importante'
        }
        form = ContenidoForm(data=data)
        self.assertFalse(form.is_valid())

class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Creamos un usuario de prueba (la señal post_save creará automáticamente su UserProfile)
        self.user = User.objects.create_user(username='testuser', password='testpassword123')
        
    def test_login_required(self):
        """Test that protected views require login"""
        response = self.client.get(reverse('configurar_tokens'))
        self.assertNotEqual(response.status_code, 200)
        self.assertTrue(response.url.startswith(reverse('login')))
        
    def test_registro_view_success(self):
        """Prueba que el registro funciona correctamente y NO lanza IntegrityError por la señal post_save"""
        data = {
            'username': 'nuevousuario1',
            'email': 'nuevo@example.com',
            'password1': 'PasswordFuerte123!',
            'password2': 'PasswordFuerte123!'
        }
        response = self.client.post(reverse('registro'), data)
        
        # Debe redirigir a configurar_tokens (HTTP 302)
        self.assertRedirects(response, reverse('configurar_tokens'))
        
        # Verificamos que se ha creado el usuario
        self.assertTrue(User.objects.filter(username='nuevousuario1').exists())
        
        # Verificamos que se ha creado su UserProfile (y no ha fallado por duplicado)
        self.assertTrue(UserProfile.objects.filter(user__username='nuevousuario1').exists())
        
        # Verificamos que ha iniciado sesión correctamente (evitando el error del backend múltiple)
        self.assertTrue('_auth_user_id' in self.client.session)

    def test_login_view_success(self):
        """Prueba que el login manual funciona y NO lanza ValueError por múltiples backends"""
        data = {
            'username': 'testuser',
            'password': 'testpassword123'
        }
        response = self.client.post(reverse('login'), data)
        
        # Debe redirigir al index (HTTP 302)
        self.assertRedirects(response, reverse('index'))
        
        # Verificamos que la sesión está activa
        self.assertTrue('_auth_user_id' in self.client.session)
        
    def test_login_view_invalid(self):
        """Prueba que un login incorrecto recarga la página con error"""
        data = {
            'username': 'testuser',
            'password': 'contraseñamala'
        }
        response = self.client.post(reverse('login'), data)
        
        # No debe redirigir, debe volver a cargar la plantilla de login con status 200
        self.assertEqual(response.status_code, 200)
        self.assertFalse('_auth_user_id' in self.client.session)

from unittest.mock import patch

class ExternalAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='apiuser', password='password123')
        self.profile = UserProfile.objects.get(user=self.user)
        self.profile.github_token = 'gh_fake'
        self.profile.gitlab_token = 'gl_fake'
        self.profile.openalex_token = 'oa_fake'
        self.profile.save()
        self.client.login(username='apiuser', password='password123')

    @patch('portfolioCV.views.requests.get')
    def test_github_repos_success(self, mock_get):
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {'name': 'test-repo', 'owner': {'login': 'testuser'}, 'html_url': 'http://github.com/test', 'description': 'desc', 'language': 'Python', 'updated_at': '2026-05-01T00:00:00Z'}
        ]
        
        response = self.client.get(reverse('github_repos'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'test-repo')
        mock_get.assert_called_once()

    @patch('portfolioCV.views.requests.get')
    def test_gitlab_repos_success(self, mock_get):
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {'id': 12345, 'name': 'gitlab-repo', 'web_url': 'http://gitlab.com/test', 'description': 'desc', 'created_at': '2026-05-01T00:00:00Z'}
        ]
        
        response = self.client.get(reverse('gitlab_repos'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'gitlab-repo')
        mock_get.assert_called_once()

    @patch('portfolioCV.views.requests.get')
    def test_openalex_repos_success(self, mock_get):
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': [
                {'id': 'https://openalex.org/W12345', 'title': 'Scientific Paper', 'publication_year': 2026}
            ]
        }
        
        # Searching triggers the API
        response = self.client.get(reverse('openalex_repos') + '?search=science')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Scientific Paper')
        mock_get.assert_called_once()

class TestCVBuilder(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='cvuser', password='password123')
        self.profile = UserProfile.objects.get(user=self.user)
        self.profile.nvidia_api_key = 'nv_fake'
        self.profile.save()
        self.client.login(username='cvuser', password='password123')

    def test_cv_builder_view(self):
        response = self.client.get(reverse('cv_builder'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Constructor de CV')

    def test_cv_builder_post(self):
        data = {
            'action': 'save_personal_info',
            'name': 'Daniel',
            'email': 'd@example.com'
        }
        response = self.client.post(reverse('cv_builder'), data)
        self.assertEqual(response.status_code, 302) # Redirects back to cv_builder

    def test_descargar_cv_html(self):
        import json
        # Add some fake data via ContenidoData
        recurso_name = f"cv_profesional_{self.user.username}"
        data = {
            'personal_info': {'name': 'Daniel'},
            'items': [{'id': '123', 'name': 'Repo 1', 'platform': 'IA Summary', 'content': 'Test Content'}]
        }
        ContenidoData.objects.create(
            recurso=recurso_name,
            usuario=self.user.username,
            contenido=json.dumps(data)
        )
        
        response = self.client.get(reverse('descargar_cv_completo') + '?format=html')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/html; charset=utf-8')
        self.assertContains(response, 'Repo 1')

    @patch('openai.OpenAI')
    def test_stream_resumen_gemini(self, mock_openai):
        # Mocking the streaming response of NVIDIA Gemma via OpenAI client
        mock_client = mock_openai.return_value
        mock_chunk = type('obj', (object,), {
            'choices': [type('choice', (object,), {'delta': type('delta', (object,), {'content': 'Hello from AI'})()})]
        })
        mock_client.chat.completions.create.return_value = [mock_chunk]

        data = {
            'id': '123',
            'cv_type': 'extenso',
            'name': 'Project',
            'llm_model': 'nvidia-gemma'
        }
        response = self.client.post(reverse('stream_resumen_gemini'), data)
        self.assertEqual(response.status_code, 200)
        # Content is a StreamingHttpResponse
        content = b''.join(response.streaming_content).decode('utf-8')
        self.assertIn('Hello from AI', content)

