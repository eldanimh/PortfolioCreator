import json
from django.core.cache import cache
from django.test import TestCase as DjangoTestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import UserProfile, ContenidoData
from .forms import RegistroForm, TokensForm, ContenidoForm


class TestCase(DjangoTestCase):
    """Cada test empieza con la caché vacía: los límites de descargas y los PDF guardados
    van por id de usuario, y los ids se repiten entre tests."""
    def _pre_setup(self):
        super()._pre_setup()
        cache.clear()


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
        self.profile.nvidia_api_key = 'nvapi-fake'
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

    @patch('openai.OpenAI')
    def test_stream_resumen_usa_proveedor_del_usuario(self, mock_openai):
        """Si el usuario configura URL y modelo propios, se usan en lugar de los de NVIDIA"""
        self.profile.ia_base_url = 'https://api.openai.com/v1'
        self.profile.ia_model = 'gpt-test'
        self.profile.save()
        mock_openai.return_value.chat.completions.create.return_value = []

        response = self.client.post(reverse('stream_resumen_gemini'), {
            'id': '123', 'cv_type': 'extenso', 'name': 'Project', 'llm_model': 'nvidia-gemma',
        })
        b''.join(response.streaming_content)

        self.assertEqual(mock_openai.call_args.kwargs['base_url'], 'https://api.openai.com/v1')
        create_kwargs = mock_openai.return_value.chat.completions.create.call_args.kwargs
        self.assertEqual(create_kwargs['model'], 'gpt-test')
        # El parámetro para desactivar el razonamiento solo se manda a NVIDIA
        self.assertNotIn('extra_body', create_kwargs)

    @patch('openai.OpenAI')
    def test_stream_resumen_nvidia_desactiva_razonamiento(self, mock_openai):
        mock_openai.return_value.chat.completions.create.return_value = []
        response = self.client.post(reverse('stream_resumen_gemini'), {
            'id': '123', 'cv_type': 'extenso', 'name': 'Project', 'llm_model': 'nvidia-gemma',
        })
        b''.join(response.streaming_content)
        create_kwargs = mock_openai.return_value.chat.completions.create.call_args.kwargs
        self.assertEqual(create_kwargs['extra_body'],
                         {'chat_template_kwargs': {'enable_thinking': False}})



class ProveedorIATests(TestCase):
    """El proveedor y el modelo de IA se deducen del prefijo de la API Key"""

    def setUp(self):
        self.profile = User.objects.create_user(username='iauser', password='x').profile

    def _config(self, key, base_url='', model=''):
        from .ia import configuracion_ia
        self.profile.nvidia_api_key = key
        self.profile.ia_base_url = base_url
        self.profile.ia_model = model
        return configuracion_ia(self.profile)

    def test_detecta_proveedor_por_prefijo(self):
        casos = {
            'nvapi-x': 'nvidia', 'sk-or-v1-x': 'openrouter', 'gsk_x': 'groq',
            'sk-ant-api03-x': 'anthropic', 'AIzaSyX': 'google', 'xai-x': 'xai',
            'sk-proj-x': 'openai', 'sk-x': 'openai',
        }
        for key, proveedor in casos.items():
            with self.subTest(key=key):
                config = self._config(key)
                self.assertEqual(config['proveedor'], proveedor)
                self.assertTrue(config['base_url'].startswith('https://'))
                self.assertTrue(config['modelo'])

    def test_clave_desconocida_sin_url(self):
        config = self._config('clave-sin-prefijo')
        self.assertIsNone(config['base_url'])

    def test_url_y_modelo_del_usuario_tienen_prioridad(self):
        config = self._config('sk-x', base_url='https://api.deepseek.com/v1', model='deepseek-chat')
        self.assertEqual(config['base_url'], 'https://api.deepseek.com/v1')
        self.assertEqual(config['modelo'], 'deepseek-chat')
        self.assertIsNone(config['proveedor'])

    def test_url_conocida_usa_su_modelo_por_defecto(self):
        from .ia import PROVEEDORES
        groq = next(p for p in PROVEEDORES if p['id'] == 'groq')
        config = self._config('clave-cualquiera', base_url=groq['base_url'])
        self.assertEqual(config['modelo'], groq['modelo'])

    @patch('portfolioCV.ia.requests.get')
    def test_aviso_si_el_modelo_no_existe(self, mock_get):
        from .ia import comprobar_configuracion
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {'data': [{'id': 'otro-modelo'}]}
        self.profile.nvidia_api_key = 'gsk_x'
        self.assertIn('no aparece', comprobar_configuracion(self.profile))

        mock_get.return_value.json.return_value = {'data': [{'id': 'openai/gpt-oss-20b'}]}
        self.assertIsNone(comprobar_configuracion(self.profile))


class DetalleRecursoTests(TestCase):
    """La página de un recurso se adapta a su contenido y solo la ve su dueño"""

    def setUp(self):
        User.objects.create_user(username='ana', password='pw')
        User.objects.create_user(username='otro', password='pw')
        self.client.login(username='ana', password='pw')

    def test_cv_profesional_se_muestra_como_ficha(self):
        data = {'personal_info': {'name': 'Ana Pérez', 'email': 'ana@example.com', 'linkedin': 'linkedin.com/in/ana',
                                  'photo': 'data:image/png;base64,AAAA', 'about': 'Hola\r\nAdiós'},
                'items': [{'platform': 'GitHub', 'id': '1', 'name': 'MiRepo'}]}
        ContenidoData.objects.create(recurso='cv_profesional_ana', usuario='ana', contenido=json.dumps(data))
        response = self.client.get(reverse('detalle_recurso', args=['cv_profesional_ana']))
        self.assertContains(response, 'class="cv-ficha"')
        self.assertContains(response, 'Ana Pérez')
        self.assertContains(response, 'href="https://linkedin.com/in/ana"')
        self.assertContains(response, 'MiRepo')
        self.assertNotContains(response, '"personal_info"')  # no se vuelca el JSON crudo

    def test_json_generico_formateado_y_sin_base64(self):
        ContenidoData.objects.create(recurso='datos', usuario='ana', contenido=json.dumps({'img': 'data:image/png;base64,' + 'A' * 500}))
        response = self.client.get(reverse('detalle_recurso', args=['datos']))
        self.assertContains(response, 'class="contenido-json"')
        self.assertContains(response, '[imagen]')
        self.assertNotContains(response, 'A' * 500)

    def test_texto_respeta_saltos_de_linea(self):
        ContenidoData.objects.create(recurso='nota', usuario='ana', contenido='uno\ndos')
        response = self.client.get(reverse('detalle_recurso', args=['nota']))
        self.assertContains(response, 'uno<br>dos')

    def test_sin_sesion_no_se_ve(self):
        ContenidoData.objects.create(recurso='nota', usuario='ana', contenido='privado')
        self.client.logout()
        response = self.client.get(reverse('detalle_recurso', args=['nota']))
        self.assertEqual(response.status_code, 302)  # redirige al login

    def test_recurso_ajeno_da_404(self):
        ContenidoData.objects.create(recurso='nota', usuario='ana', contenido='privado')
        self.client.login(username='otro', password='pw')
        response = self.client.get(reverse('detalle_recurso', args=['nota']))
        self.assertEqual(response.status_code, 404)
        self.assertNotContains(response, 'privado', status_code=404)

    def test_eliminar_solo_por_post_y_solo_el_dueno(self):
        ContenidoData.objects.create(recurso='nota', usuario='ana', contenido='x')
        url = reverse('eliminar_recurso', args=['nota'])
        # GET ya no borra
        self.assertEqual(self.client.get(url).status_code, 405)
        # Otro usuario no puede borrarlo
        self.client.login(username='otro', password='pw')
        self.assertEqual(self.client.post(url).status_code, 404)
        self.assertTrue(ContenidoData.objects.filter(recurso='nota').exists())
        # El dueño sí
        self.client.login(username='ana', password='pw')
        self.assertRedirects(self.client.post(url), reverse('index'))
        self.assertFalse(ContenidoData.objects.filter(recurso='nota').exists())


def _texto_pdf(contenido):
    """Texto de todas las páginas de un PDF (para comprobar qué se ha pintado)."""
    import io
    from pypdf import PdfReader
    return '\n'.join(pagina.extract_text() for pagina in PdfReader(io.BytesIO(contenido)).pages)


class PDFTypstTests(TestCase):
    """Los PDF se generan con Typst sin que los datos del usuario puedan inyectar código"""

    def setUp(self):
        self.user = User(username='ana')

    def test_markdown_dentro_de_div_y_rutas_relativas(self):
        from . import pdf
        readme = '<div align="center">\n\n# Título\n\n**negrita** ![logo](img/logo.png)\n\n</div>\n\nTexto [enlace](https://example.com)'
        repo = {'name': 'proyecto', 'full_name': 'ana/proyecto', 'default_branch': 'main'}
        with patch('portfolioCV.pdf._descargar_imagen', return_value=None) as mock_descarga:
            texto = _texto_pdf(pdf.cv_repo(self.user, repo, [{'name': 'Python', 'pct': 80}], ['README.md'], readme, 'GitHub'))
        self.assertEqual(mock_descarga.call_args.args[0], 'https://raw.githubusercontent.com/ana/proyecto/main/img/logo.png')
        self.assertIn('Título', texto)
        self.assertIn('negrita', texto)
        self.assertIn('Python: 80', texto)
        self.assertNotIn('**', texto)

    def test_datos_del_usuario_no_se_ejecutan_como_typst(self):
        from . import pdf
        cv = {'personal_info': {'name': '#panic("nombre") $x$', 'about': '<!--raw-typst #panic("about") -->Hola'},
              'items': [{'id': 1, 'name': '#panic("item")', 'platform': 'IA Summary',
                         'content': '<!--raw-typst #panic("ia") -->\n#read("main.typ")'}]}
        texto = _texto_pdf(pdf.cv_profesional(self.user, cv))  # con raw-typst activo, panic() rompería el PDF
        self.assertIn('#panic("nombre") $x$', texto)
        self.assertIn('#panic("item")', texto)
        self.assertIn('#read(', texto)  # el Markdown pone comillas tipográficas: #read(“main.typ”)

    def test_cv_profesional_muestra_titular_y_oculta_ids(self):
        from . import pdf
        cv = {'personal_info': {'name': 'Ana Pérez', 'headline': 'Arquitecta · Diseño sostenible'},
              'items': [{'id': '785ae689-d03e-40d7', 'name': 'Resumen IA - Casa', 'platform': 'IA Summary', 'content': '# Título enorme\nTexto'},
                        {'id': 'ana/casa', 'name': 'casa', 'platform': 'GitHub'}]}
        texto = _texto_pdf(pdf.cv_profesional(self.user, cv))
        self.assertIn('Arquitecta · Diseño sostenible', texto)
        self.assertIn('CV Profesional — Ana Pérez', texto)  # cabecera con el nombre, no el usuario
        self.assertNotIn('785ae689', texto)
        self.assertNotIn('ID:', texto)
        self.assertNotIn('Plataforma Portfolio Creator', texto)

    def test_cv_profesional_con_foto(self):
        import base64
        from . import pdf
        png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGD4DwABBAEAwS2OUAAAAABJRU5ErkJggg==')
        cv = {'personal_info': {'name': 'Ana', 'photo': 'data:image/png;base64,' + base64.b64encode(png).decode()}, 'items': []}
        self.assertTrue(pdf.cv_profesional(self.user, cv).startswith(b'%PDF'))

    def test_imagenes_internas_no_se_descargan(self):
        from . import pdf
        import time
        with patch('portfolioCV.pdf.requests.get') as mock_get:
            self.assertIsNone(pdf._descargar_imagen('http://169.254.169.254/latest/meta-data/', time.monotonic() + 5))
        mock_get.assert_not_called()

    def test_redireccion_a_direccion_interna_bloqueada(self):
        from . import pdf
        import time
        from unittest.mock import MagicMock
        redireccion = MagicMock(is_redirect=True, headers={'location': 'http://127.0.0.1/secreto.png'})
        redireccion.__enter__.return_value = redireccion
        with patch('portfolioCV.pdf.requests.get', return_value=redireccion) as mock_get:
            self.assertIsNone(pdf._descargar_imagen('https://8.8.8.8/logo.png', time.monotonic() + 5))
        self.assertEqual(mock_get.call_count, 1)  # no llega a pedir la dirección interna


class RecursoPublicoTests(TestCase):
    """Lo que puede cargar el PDF: solo http/https hacia hosts públicos"""

    def test_bloquea_direcciones_internas_y_esquemas_raros(self):
        from .seguridad import recurso_publico
        for url in ['http://127.0.0.1:8000/', 'http://169.254.169.254/latest/meta-data/',
                    'http://10.0.0.5/', 'http://[::1]/', 'file:///etc/passwd',
                    'http://user:pass@8.8.8.8/', 'ftp://8.8.8.8/']:
            with self.subTest(url=url):
                self.assertFalse(recurso_publico(url))

    def test_permite_hosts_publicos_con_parametros(self):
        from .seguridad import recurso_publico
        self.assertTrue(recurso_publico('https://8.8.8.8/badge?logo=django&color=white'))


class AislamientoRecursosTests(TestCase):
    """Paco y Dani solo ven, abren y borran sus propios recursos"""

    def setUp(self):
        User.objects.create_user(username='paco', password='pw')
        User.objects.create_user(username='dani', password='pw')

    def _crear(self, usuario, nombre, contenido):
        self.client.login(username=usuario, password='pw')
        # follow=True: como un navegador, carga la página siguiente y consume el mensaje flash
        return self.client.post(reverse('index'), {'recurso': nombre, 'contenido': contenido}, follow=True)

    def test_cada_uno_ve_solo_lo_suyo(self):
        self._crear('paco', 'notas-paco', 'secreto de Paco')
        self._crear('dani', 'notas-dani', 'secreto de Dani')

        self.client.login(username='dani', password='pw')
        portada = self.client.get(reverse('index'))
        self.assertContains(portada, 'notas-dani')
        self.assertNotContains(portada, 'notas-paco')
        self.assertEqual(self.client.get(reverse('detalle_recurso', args=['notas-paco'])).status_code, 404)

        self.client.login(username='paco', password='pw')
        portada = self.client.get(reverse('index'))
        self.assertContains(portada, 'notas-paco')
        self.assertNotContains(portada, 'notas-dani')
        self.assertEqual(self.client.get(reverse('detalle_recurso', args=['notas-dani'])).status_code, 404)

    def test_mismo_nombre_para_dos_usuarios(self):
        """Si Paco tiene "notas", Dani puede crear su propio "notas" y cada uno ve el suyo"""
        self._crear('paco', 'notas', 'de Paco')
        respuesta = self._crear('dani', 'notas', 'de Dani')
        self.assertNotContains(respuesta, 'Ya tienes un recurso con ese nombre.')
        self.assertTrue(ContenidoData.objects.filter(recurso='notas', usuario='dani').exists())

        self.client.login(username='dani', password='pw')
        detalle = self.client.get(reverse('detalle_recurso', args=['notas']))
        self.assertContains(detalle, 'de Dani')
        self.assertNotContains(detalle, 'de Paco')

        # Dani borra su "notas"; el de Paco sigue ahí
        self.client.post(reverse('eliminar_recurso', args=['notas']))
        self.assertFalse(ContenidoData.objects.filter(recurso='notas', usuario='dani').exists())
        self.assertTrue(ContenidoData.objects.filter(recurso='notas', usuario='paco').exists())

    def test_nombre_repetido_del_mismo_usuario_da_error(self):
        self._crear('dani', 'notas', 'uno')
        respuesta = self._crear('dani', 'notas', 'dos')
        self.assertContains(respuesta, 'Ya tienes un recurso con ese nombre.')


class HuggingFaceTests(TestCase):
    """Integración con Hugging Face (API simulada con mocks)"""

    def setUp(self):
        self.user = User.objects.create_user(username='hfuser', password='pw')
        self.profile = self.user.profile
        self.profile.huggingface_username = 'ana'
        self.profile.save()
        self.client.login(username='hfuser', password='pw')

    @staticmethod
    def _respuesta(datos, status=200, texto=''):
        from unittest.mock import MagicMock
        r = MagicMock(status_code=status, text=texto)
        r.json.return_value = datos
        return r

    @patch('portfolioCV.huggingface.requests.get')
    def test_lista_modelos_datasets_y_spaces(self, mock_get):
        def fake_get(url, **kwargs):
            if url.endswith('/api/models'):
                return self._respuesta([{'id': 'ana/modelo', 'lastModified': '2026-01-02', 'pipeline_tag': 'text-generation', 'likes': 3}])
            if url.endswith('/api/datasets'):
                return self._respuesta([{'id': 'ana/datos', 'lastModified': '2026-03-01'}])
            return self._respuesta([{'id': 'ana/demo', 'lastModified': '2026-02-01', 'sdk': 'gradio'}])
        mock_get.side_effect = fake_get

        response = self.client.get(reverse('huggingface_repos'))
        self.assertEqual(response.status_code, 200)
        nombres = [r['name'] for r in response.context['repos']]
        self.assertEqual(nombres, ['datos', 'demo', 'modelo'])  # del más reciente al más antiguo
        self.assertContains(response, 'text-generation')
        self.assertContains(response, reverse('huggingface_repo_detalle', args=['space', 'ana', 'demo']))

    def test_sin_usuario_muestra_el_buscador(self):
        self.profile.huggingface_username = ''
        self.profile.save()
        response = self.client.get(reverse('huggingface_repos'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="q"')
        self.assertContains(response, reverse('configurar_tokens'))

    @patch('portfolioCV.huggingface.requests.get')
    def test_buscar_repos_de_otro_usuario(self, mock_get):
        mock_get.return_value = self._respuesta([])
        self.client.get(reverse('huggingface_repos'), {'q': 'openai', 'modo': 'autor'})
        params = [c.kwargs['params'] for c in mock_get.call_args_list]
        self.assertEqual(len(params), 3)  # modelos, datasets y Spaces
        self.assertTrue(all(p['author'] == 'openai' and 'search' not in p for p in params))

    @patch('portfolioCV.huggingface.requests.get')
    def test_buscar_por_nombre(self, mock_get):
        mock_get.return_value = self._respuesta([{'id': 'otra/gpt-mini', 'lastModified': '2026-01-01'}])
        response = self.client.get(reverse('huggingface_repos'), {'q': 'gpt', 'modo': 'nombre'})
        params = [c.kwargs['params'] for c in mock_get.call_args_list]
        self.assertTrue(all(p['search'] == 'gpt' and 'author' not in p for p in params))
        self.assertContains(response, 'gpt-mini')
        self.assertContains(response, 'Ver mis repositorios')

    def test_tipo_desconocido_da_404(self):
        response = self.client.get(reverse('huggingface_repo_detalle', args=['otro', 'ana', 'x']))
        self.assertEqual(response.status_code, 404)

    @patch('portfolioCV.huggingface.requests.get')
    def test_detalle_de_un_modelo(self, mock_get):
        mock_get.return_value = self._respuesta({
            'id': 'ana/modelo', 'pipeline_tag': 'text-generation', 'library_name': 'transformers',
            'cardData': {'license': 'apache-2.0'}, 'tags': ['pytorch', 'license:apache-2.0'],
            'siblings': [{'rfilename': 'config.json'}], 'likes': 7, 'downloads': 42,
        })
        response = self.client.get(reverse('huggingface_repo_detalle', args=['model', 'ana', 'modelo']))
        self.assertContains(response, 'https://huggingface.co/ana/modelo')
        self.assertContains(response, 'apache-2.0')
        self.assertContains(response, 'transformers')
        self.assertContains(response, 'pytorch')
        self.assertNotContains(response, 'license:apache-2.0')  # etiquetas técnicas fuera

    @patch('portfolioCV.huggingface.requests.get')
    def test_readme_sin_cabecera_yaml(self, mock_get):
        from . import huggingface as hf
        mock_get.return_value = self._respuesta(None, texto='---\nlicense: mit\ntags: [a]\n---\n\n# Mi modelo\nTexto')
        self.assertEqual(hf.readme_repo(self.profile, 'model', 'ana/modelo'), '# Mi modelo\nTexto')
        url = mock_get.call_args.args[0]
        self.assertEqual(url, 'https://huggingface.co/ana/modelo/raw/main/README.md')

    @patch('portfolioCV.huggingface.requests.get')
    def test_usuario_deducido_del_token(self, mock_get):
        from . import huggingface as hf
        self.profile.huggingface_username = ''
        self.profile.huggingface_token = 'hf_x'
        mock_get.return_value = self._respuesta({'name': 'ana'})
        self.assertEqual(hf.usuario_hf(self.profile), 'ana')
        self.assertEqual(mock_get.call_args.kwargs['headers'], {'Authorization': 'Bearer hf_x'})

    @patch('portfolioCV.pdf._descargar_imagen', return_value=b'\x89PNG\r\n\x1a\n...')
    def test_imagenes_del_readme_en_el_pdf(self, mock_descarga):
        from . import pdf
        repo = {'html_url': 'https://huggingface.co/datasets/ana/datos', 'default_branch': 'main'}
        mapa, ficheros = pdf._imagenes_readme('![grafica](img/g.png)', pdf._base_raw(repo, 'Hugging Face'))
        self.assertEqual(mock_descarga.call_args.args[0], 'https://huggingface.co/datasets/ana/datos/resolve/main/img/g.png')
        self.assertEqual(mapa, {'img/g.png': 'img0.png'})


def _png(ancho=1200, alto=900, modo='RGB'):
    import io
    from PIL import Image
    salida = io.BytesIO()
    Image.new(modo, (ancho, alto), (30, 120, 200)).save(salida, 'PNG')
    return salida.getvalue()


class FotoWebPTests(TestCase):
    """La foto de perfil, sea del formato que sea, se guarda como WebP pequeño"""

    def setUp(self):
        self.user = User.objects.create_user(username='foto', password='password123')
        self.client.login(username='foto', password='password123')

    def _cv(self):
        from .views import _get_cv_data
        return _get_cv_data(self.user)[1]

    def test_png_grande_se_guarda_como_webp_reducido(self):
        import base64, io
        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image
        foto = SimpleUploadedFile('foto.png', _png(), content_type='image/png')
        self.client.post(reverse('cv_builder'), {'name': 'Ana', 'photo': foto})
        guardada = self._cv()['personal_info']['photo']
        self.assertTrue(guardada.startswith('data:image/webp;base64,'))
        imagen = Image.open(io.BytesIO(base64.b64decode(guardada.split(',', 1)[1])))
        self.assertEqual(imagen.format, 'WEBP')
        self.assertLessEqual(max(imagen.size), 512)
        self.assertEqual(imagen.size, (512, 384))  # mantiene la proporción

    def test_fichero_que_no_es_imagen_no_cambia_la_foto(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        falso = SimpleUploadedFile('foto.png', b'<script>alert(1)</script>', content_type='image/png')
        response = self.client.post(reverse('cv_builder'), {'name': 'Ana', 'photo': falso}, follow=True)
        self.assertContains(response, 'No se ha podido leer la foto')
        self.assertEqual(self._cv()['personal_info']['photo'], '')
        self.assertEqual(self._cv()['personal_info']['name'], 'Ana')  # el resto sí se guarda

    def test_foto_antigua_se_convierte_al_leer_el_cv(self):
        import base64
        ContenidoData.objects.create(recurso='cv_profesional_foto', usuario='foto', contenido=json.dumps({
            'personal_info': {'photo': 'data:image/png;base64,' + base64.b64encode(_png()).decode()}, 'items': []}))
        self.assertTrue(self._cv()['personal_info']['photo'].startswith('data:image/webp;base64,'))
        guardado = json.loads(ContenidoData.objects.get(recurso='cv_profesional_foto').contenido)
        self.assertTrue(guardado['personal_info']['photo'].startswith('data:image/webp;base64,'))  # convertida una sola vez


class DescargasMasivasTests(TestCase):
    """Límites por usuario, caché de descargas y llamadas a las APIs en paralelo"""

    def setUp(self):
        self.user = User.objects.create_user(username='masivo', password='password123')
        self.client.login(username='masivo', password='password123')
        items = [{'platform': 'GitHub', 'id': f'ana/repo{i}', 'name': f'Repo {i}'} for i in range(6)]
        ContenidoData.objects.create(recurso='cv_profesional_masivo', usuario='masivo',
                                     contenido=json.dumps({'personal_info': {'name': 'Ana'}, 'items': items}))
        self.url = reverse('descargar_cv_completo') + '?format=html'

    @staticmethod
    def _api_lenta(profile, item):
        import time
        time.sleep(0.3)
        return {'description': f"Descripción de {item['id']}"}

    def test_apis_en_paralelo_en_orden_y_cacheadas(self):
        import time
        with patch('portfolioCV.views._datos_actualizados', side_effect=self._api_lenta) as mock_api:
            inicio = time.monotonic()
            response = self.client.get(self.url)
            duracion = time.monotonic() - inicio
            self.assertEqual(mock_api.call_count, 6)
            self.assertLess(duracion, 1.2)  # en serie serían 6 × 0,3 = 1,8 s
            html = response.content.decode()
            posiciones = [html.index(f'Descripción de ana/repo{i}') for i in range(6)]
            self.assertEqual(posiciones, sorted(posiciones))  # mismo orden que en el CV

            self.client.get(self.url)  # segunda descarga: datos y HTML desde la caché
            self.assertEqual(mock_api.call_count, 6)

    def test_maximo_de_descargas_por_minuto(self):
        from .descargas import MAX_POR_MINUTO
        with patch('portfolioCV.views._datos_actualizados', return_value={}):
            for _ in range(MAX_POR_MINUTO):
                self.assertEqual(self.client.get(self.url).status_code, 200)
            response = self.client.get(self.url, follow=True)
        self.assertContains(response, 'Has hecho muchas descargas seguidas')

    def test_una_descarga_a_la_vez_por_usuario(self):
        cache.add(f'descargando:{self.user.pk}', 1, 60)  # otra descarga del mismo usuario en marcha
        response = self.client.get(self.url, follow=True)
        self.assertContains(response, 'Ya tienes una descarga en marcha')

    def test_pdf_de_repo_cacheado_sin_volver_a_llamar_a_github(self):
        from unittest.mock import MagicMock
        def respuesta(url, **kwargs):
            r = MagicMock(status_code=200)
            r.json.return_value = {'name': 'repo', 'full_name': 'ana/repo', 'default_branch': 'main'} if url.endswith('/repos/ana/repo') else {}
            r.text = '# Repo'
            return r
        url = reverse('generar_cv_github', args=['ana', 'repo'])
        with patch('portfolioCV.views.requests.get', side_effect=respuesta) as mock_get:
            primera = self.client.get(url)
            llamadas = mock_get.call_count
            segunda = self.client.get(url)
        self.assertEqual(primera.status_code, 200)
        self.assertEqual(primera.content, segunda.content)
        self.assertEqual(mock_get.call_count, llamadas)  # la segunda no llama a GitHub

    def test_pdf_de_repo_vacio_no_se_cachea(self):
        from unittest.mock import MagicMock
        url = reverse('generar_cv_github', args=['ana', 'caido'])
        with patch('portfolioCV.views.requests.get', return_value=MagicMock(status_code=503)) as mock_get:
            self.client.get(url)
            llamadas = mock_get.call_count
            self.client.get(url)
        self.assertEqual(mock_get.call_count, llamadas * 2)  # GitHub caído: se reintenta la próxima vez


class ImagenesReadmeParaleloTests(TestCase):
    def test_orden_del_readme_aunque_lleguen_desordenadas(self):
        import time
        from . import pdf
        def descarga(url, limite):
            time.sleep(0.2 if url.endswith('a.png') else 0)  # la primera tarda más
            return _png(10, 10)
        with patch('portfolioCV.pdf._descargar_imagen', side_effect=descarga):
            mapa, ficheros = pdf._imagenes_readme('![](https://8.8.8.8/a.png) ![](https://8.8.8.8/b.png)', None)
        self.assertEqual(mapa, {'https://8.8.8.8/a.png': 'img0.png', 'https://8.8.8.8/b.png': 'img1.png'})
        with patch('portfolioCV.pdf._descargar_imagen') as mock_descarga:  # ya en caché
            pdf._imagenes_readme('![](https://8.8.8.8/a.png)', None)
        mock_descarga.assert_not_called()
