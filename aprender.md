# Aprender: Portfolio Creator — Guía Técnica Completa

Guía paso a paso de cómo se construyó **Portfolio Creator**, una aplicación Django que integra APIs externas (GitHub, GitLab, OpenAlex) e Inteligencia Artificial (NVIDIA Gemma-2) para generar portfolios y CVs profesionales.

---

## 1. Arquitectura del Proyecto

```
final/
├── manage.py                  ← Punto de entrada de Django
├── requirements.txt           ← Dependencias del proyecto
├── db.sqlite3                 ← Base de datos SQLite
├── PortfolioGenerator/        ← Configuración del proyecto Django
│   ├── settings.py            ← Configuración global
│   ├── urls.py                ← Rutas raíz
│   └── wsgi.py                ← Servidor WSGI (producción)
└── portfolioCV/               ← App principal
    ├── models.py              ← Modelos de datos (tablas)
    ├── views.py               ← Lógica de negocio (vistas)
    ├── urls.py                ← Rutas de la app
    ├── forms.py               ← Formularios Django
    ├── admin.py               ← Registro en Admin Site
    ├── tests.py               ← Tests unitarios
    ├── templates/portfolioCV/ ← Plantillas HTML (16 archivos)
    │   ├── base.html          ← Plantilla padre (herencia)
    │   ├── index.html         ← Página principal
    │   ├── login.html         ← Inicio de sesión
    │   ├── registro.html      ← Registro de usuario
    │   ├── tokens.html        ← Configuración de tokens
    │   ├── gitlab_repos.html  ← Lista repos GitLab
    │   ├── github_repos.html  ← Lista repos GitHub
    │   ├── openalex_repos.html← Lista publicaciones
    │   ├── repo_detalle.html  ← Detalle de un repo
    │   ├── gemini_resumen.html← Streaming IA en vivo
    │   ├── cv_builder.html    ← Constructor de CV
    │   └── cv_profesional_template.html ← Plantilla PDF
    └── static/portfolioCV/
        ├── css/style.css      ← Estilos CSS (responsive)
        └── img/logo.svg       ← Favicon
```

---

## 2. Modelos de Datos — `models.py`

### Tabla 1: `UserProfile`
Extiende el modelo `User` nativo de Django con una relación One-to-One:

```python
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    github_token = models.CharField(max_length=255, blank=True, default='')
    gitlab_token = models.CharField(max_length=255, blank=True, default='')
    github_username = models.CharField(max_length=150, blank=True, default='')
    gitlab_username = models.CharField(max_length=150, blank=True, default='')
    openalex_token = models.CharField(max_length=255, blank=True, default='')
    nvidia_api_key = models.CharField(max_length=255, blank=True, default='')
    lm_studio_url = models.CharField(max_length=255, blank=True, default='')
```

- `OneToOneField` → cada usuario tiene exactamente un perfil
- `on_delete=CASCADE` → si se borra el usuario, se borra su perfil
- Todos los campos son opcionales (`blank=True, default=''`)

### Tabla 2: `ContenidoData`
Almacena los recursos y CVs generados en formato JSON:

```python
class ContenidoData(models.Model):
    recurso = models.CharField(max_length=255, unique=True)
    contenido = models.TextField(blank=True, default='')   # JSON del CV
    usuario = models.CharField(max_length=255, blank=True, default='')
    plataforma = models.CharField(max_length=100, blank=True, default='')
    url_repo = models.URLField(max_length=500, blank=True, default='')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
```

- `unique=True` en recurso → no se pueden crear dos con el mismo nombre
- `auto_now_add=True` → fecha automática al crear el registro

### Migraciones
Cada vez que se modifica un modelo:
```bash
python3 manage.py makemigrations portfolioCV
python3 manage.py migrate
```

---

## 3. Autenticación — Login, Registro y Sesiones

### Registro (`registro_view`)
Usa `UserCreationForm` de Django con email obligatorio:

```python
def registro_view(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user)
            login(request, user)
            return redirect('configurar_tokens')
        else:
            # Errores específicos en español
            for field, errors in form.errors.items():
                for error in errors:
                    if 'already exists' in error:
                        messages.error(request, 'Ese usuario ya existe.')
                    elif 'too short' in error:
                        messages.error(request, 'Contraseña muy corta (mín. 8 caracteres).')
```

### Login (`login_view`)
Autenticación manual con mensajes de error diferenciados:

```python
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')

        user_exists = User.objects.filter(username=username).exists()

        if not user_exists:
            messages.error(request, 'No existe ese usuario. ¿Quieres registrarte?')
        else:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('index')
            else:
                messages.error(request, 'Contraseña incorrecta.')
```

### Protección de rutas
Se usa el decorador `@login_required` en todas las vistas que requieren autenticación:
```python
@login_required
def github_repos(request):
    ...
```

### Social Login — django-allauth (GitHub + Google)

Además del login manual, se integró `django-allauth` para permitir inicio de sesión con un clic usando cuentas de GitHub o Google.

#### Configuración en `settings.py`:
```python
INSTALLED_APPS = [
    ...
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.github',
    'allauth.socialaccount.providers.google',
]

SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Middleware adicional
MIDDLEWARE = [
    ...
    'allauth.account.middleware.AccountMiddleware',
]

# Configuración de allauth
ACCOUNT_EMAIL_VERIFICATION = 'none'
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_AUTO_SIGNUP = True
```

#### URLs en `PortfolioGenerator/urls.py`:
```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),  # ← Callbacks OAuth
    path('', include('portfolioCV.urls')),
]
```

#### Botones en los templates (`login.html`):
```html
{% load socialaccount %}

<a href="{% provider_login_url 'github' %}" class="btn-social btn-github">
    Continuar con GitHub
</a>
<a href="{% provider_login_url 'google' %}" class="btn-social btn-google">
    Continuar con Google
</a>
```

#### Signal para crear UserProfile automáticamente:
Cuando un usuario entra por social login, no pasa por `registro_view`, así que se usa un signal en `models.py`:
```python
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)
```

#### Configuración de credenciales OAuth:
Las credenciales (Client ID + Secret) se configuran desde el **Admin Site** → **Social Applications**:
1. Crear OAuth App en GitHub (Settings → Developer Settings → OAuth Apps)
2. Crear OAuth Client en Google Cloud Console (APIs → Credentials)
3. Registrar ambos en `/admin/` → Social Applications con el sitio correcto

> **Nota:** Las callback URLs deben coincidir:
> - GitHub: `https://eldanimh.pythonanywhere.com/accounts/github/login/callback/`
> - Google: `https://eldanimh.pythonanywhere.com/accounts/google/login/callback/`

---

## 4. APIs Externas — GitHub, GitLab y OpenAlex

### 4.1 GitHub API
```python
GITHUB_API_URL = "https://api.github.com"

headers = {
    "Authorization": f"Bearer {profile.github_token}",
    "Accept": "application/vnd.github.v3+json"
}
response = requests.get(f"{GITHUB_API_URL}/user/repos", headers=headers,
                        params={"per_page": 50}, timeout=10, proxies=PA_PROXIES)
repos = response.json()
```

- Autenticación: `Bearer Token` en cabecera `Authorization`
- Endpoints usados: `/user/repos`, `/repos/{owner}/{name}`, `/repos/.../readme`, `/repos/.../languages`, `/repos/.../git/trees/`

### 4.2 GitLab URJC API
```python
GITLAB_URJC_URL = "https://gitlab.eif.urjc.es/api/v4"

headers = {"PRIVATE-TOKEN": profile.gitlab_token}
response = requests.get(f"{GITLAB_URJC_URL}/projects", headers=headers,
                        params={"owned": True, "per_page": 50}, timeout=10)
```

- Autenticación: `PRIVATE-TOKEN` en cabecera (formato GitLab)
- Endpoints: `/projects`, `/projects/{id}`, `/projects/{id}/languages`, `/projects/{id}/repository/tree`, `/projects/{id}/repository/files/README.md/raw`

### 4.3 OpenAlex API
```python
url = "https://api.openalex.org/works"
params = {"search": query, "per_page": 15}
response = requests.get(url, params=params, timeout=10)
```

- Sin autenticación obligatoria (API abierta)
- Particularidad: el abstract viene como "inverted index":

```python
# Reconstruir abstract desde inverted index
abs_idx = wdata.get('abstract_inverted_index')
if abs_idx:
    words = {}
    for word, pos_list in abs_idx.items():
        for pos in pos_list:
            words[pos] = word
    abstract = " ".join([words[p] for p in sorted(words.keys())])
```

### 4.4 Proxy para PythonAnywhere
Las cuentas gratuitas requieren proxy para acceso a internet:
```python
import os
PA_PROXIES = {
    "http": "http://proxy.server:3128",
    "https": "http://proxy.server:3128"
} if "PYTHONANYWHERE_DOMAIN" in os.environ else None
```
Se pasa como `proxies=PA_PROXIES` a todas las llamadas `requests.get/post`.

---

## 5. Inteligencia Artificial — NVIDIA Gemma-2 en Streaming

### 5.1 Arquitectura del streaming

```
┌──────────┐    POST     ┌──────────────┐   render   ┌──────────────────┐
│ Detalle  │ ──────────→ │ generar_     │ ────────→  │ gemini_          │
│ del repo │  (platform, │ resumen_     │            │ resumen.html     │
│          │   id, type)  │ gemini()     │            │ (página vacía)   │
└──────────┘              └──────────────┘            └───────┬──────────┘
                                                              │ fetch()
                                                              ▼
                                                     ┌──────────────────┐
                                                     │ stream_resumen_  │
                                                     │ gemini()         │
                                                     │                  │
                                                     │ yield chunk      │
                                                     │ yield chunk      │
                                                     │ yield chunk...   │
                                                     └──────────────────┘
```

1. El usuario pulsa "Generar" → POST a `generar_resumen_gemini`
2. La vista renderiza `gemini_resumen.html` (página con un `<div>` vacío)
3. JavaScript hace un `fetch()` a `stream_resumen_gemini`
4. El servidor responde con `StreamingHttpResponse` (texto en chunks)
5. El frontend va pintando cada chunk con `marked.js` (Markdown → HTML)

### 5.2 Vista de streaming (`stream_resumen_gemini`)

```python
from django.http import StreamingHttpResponse

@login_required
def stream_resumen_gemini(request):
    def event_stream():
        # 1. Recopilar contenido del repo vía API
        contenido_texto = f"Proyecto: {item_name}\nPlataforma: {platform}\n"
        # ... llamadas a GitHub/GitLab/OpenAlex ...

        # 2. Construir prompt
        prompt = "RESPONDE SIEMPRE EN ESPAÑOL. Genera un CV extenso..."
        prompt += f"\n\nContenido:\n{contenido_texto}"

        # 3. Llamar a NVIDIA con streaming
        from openai import OpenAI
        import httpx

        if PA_PROXIES:
            http_client = httpx.Client(proxy=PA_PROXIES["http"])
        else:
            http_client = httpx.Client()

        client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=profile.nvidia_api_key,
            http_client=http_client
        )

        response = client.chat.completions.create(
            model="google/gemma-2-2b-it",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2, top_p=0.7, max_tokens=2048,
            stream=True   # ← Clave: activar streaming
        )

        # 4. Yield cada chunk de texto
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    return StreamingHttpResponse(event_stream(), content_type='text/plain; charset=utf-8')
```

### 5.3 Frontend: recibir streaming con JavaScript

```javascript
// gemini_resumen.html
fetch("/gemini/stream/", { method: 'POST', body: formData })
.then(async response => {
    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let fullText = "";

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, {stream: true});
        fullText += chunk;

        // Convertir Markdown acumulado a HTML en tiempo real
        contentDiv.innerHTML = marked.parse(fullText);
    }
});
```

### 5.4 Soporte para LM Studio (modelo local)
Alternativa para usar modelos en tu propio PC:

```python
if llm_model == 'local':
    url = f"{profile.lm_studio_url}/v1/chat/completions"
    payload = {
        "model": "qwen2.5-7b-instruct",
        "messages": [{"role": "user", "content": prompt}],
        "stream": True
    }
    resp = requests.post(url, json=payload, stream=True, timeout=180)
    for line in resp.iter_lines():
        if line.startswith(b'data: '):
            data_json = json.loads(line[6:])
            chunk = data_json['choices'][0]['delta'].get('content', '')
            if chunk:
                yield chunk
```

---

## 6. Constructor de CV — Sistema de "Cesta"

### 6.1 Almacenamiento en JSON
El CV se guarda como un JSON dentro de `ContenidoData.contenido`:

```python
# Estructura del JSON
{
    "personal_info": {
        "name": "Daniel Martín",
        "email": "d.martin@...",
        "phone": "+34 600...",
        "linkedin": "linkedin.com/in/...",
        "about": "Ingeniero de software...",
        "photo": "data:image/jpeg;base64,..."  # foto en Base64
    },
    "items": [
        {"name": "Repo1", "platform": "GitHub", "id": "user/repo"},
        {"name": "Paper1", "platform": "OpenAlex", "id": "W12345"},
        {"name": "Resumen IA", "platform": "IA Summary", "content": "..."}
    ]
}
```

### 6.2 Añadir al CV (`agregar_al_cv`)
```python
@login_required
def agregar_al_cv(request):
    contenido, _ = ContenidoData.objects.get_or_create(
        recurso=f"cv_profesional_{request.user.username}",
        defaults={'usuario': request.user.username}
    )
    data = json.loads(contenido.contenido) if contenido.contenido else {...}
    data['items'].append({
        'name': request.POST.get('name'),
        'platform': request.POST.get('platform'),
        'id': request.POST.get('id')
    })
    contenido.contenido = json.dumps(data)
    contenido.save()
```

### 6.3 Exportación PDF (Playwright)
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.set_content(html_string, wait_until='networkidle')
    pdf_bytes = page.pdf(format="A4", print_background=True,
                         margin={'top': '25mm', 'bottom': '25mm'})
    browser.close()
```

> **Nota:** Playwright no funciona en PythonAnywhere (Free Tier) por falta de espacio. Se usa un `try/except ImportError` para mostrar un mensaje amigable.

### 6.4 Exportación HTML
```python
if request.GET.get('format') == 'html':
    html_string = render_to_string('portfolioCV/cv_web_portfolio_template.html', context)
    response = HttpResponse(html_string, content_type='text/html')
    response['Content-Disposition'] = 'attachment; filename="cv_profesional.html"'
    return response
```

---

## 7. Plantillas Django — Herencia

```
base.html (padre)
├── index.html
├── login.html
├── registro.html
├── tokens.html
├── gitlab_repos.html
├── github_repos.html
├── openalex_repos.html
├── repo_detalle.html
├── gemini_resumen.html
├── cv_builder.html
└── detalle.html
```

### base.html (plantilla padre)
```html
{% load static %}
<html lang="es">
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Portfolio Creator{% endblock %}</title>
    <link rel="stylesheet" href="{% static 'portfolioCV/css/style.css' %}">
</head>
<body>
    <nav class="navbar">
        <div class="nav-container">
            <a href="/" class="nav-brand">◆ Portfolio Creator</a>
            <div class="nav-links">
                {% if user.is_authenticated %}
                <a href="/mi-cv/" class="nav-link">📄 Mi CV</a>
                <a href="/tokens/" class="nav-link">⚙ Tokens</a>
                <a href="/logout/" class="nav-link">Cerrar sesión</a>
                <span class="nav-user-badge">¡Hola, {{ user.username }}!</span>
                {% else %}
                <a href="/login/" class="nav-link">Iniciar sesión</a>
                <a href="/registro/" class="nav-link nav-link-accent">Registrarse</a>
                {% endif %}
            </div>
        </div>
    </nav>
    <main>{% block content %}{% endblock %}</main>
    <footer class="footer">...</footer>
</body>
</html>
```

La variable `{{ user.username }}` está disponible automáticamente en todas las plantillas gracias al context processor `django.contrib.auth.context_processors.auth` configurado en `settings.py`. El badge `nav-user-badge` se muestra como una pastilla roja con el nombre del usuario logueado.


### Plantilla hija (ejemplo: login.html)
```html
{% extends "portfolioCV/base.html" %}

{% block title %}Iniciar sesión{% endblock %}

{% block content %}
<div class="auth-container">
    <form method="post">
        {% csrf_token %}
        {% for field in form %}
            <div class="form-group">
                <label>{{ field.label }}</label>
                {{ field }}
                {% if field.errors %}<div class="form-error">{{ field.errors }}</div>{% endif %}
            </div>
        {% endfor %}
        <button type="submit">Entrar</button>
    </form>
</div>
{% endblock %}
```

---

## 8. Admin Site — `admin.py`

```python
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
```

Accesible en `/admin/` con el superusuario creado con:
```bash
python manage.py createsuperuser
```

---

## 9. Tests Unitarios — `tests.py`

Suite de 15 tests usando `unittest.mock` para simular APIs externas:

```python
from unittest.mock import patch, MagicMock

class APITests(TestCase):
    @patch('portfolioCV.views.requests.get')
    def test_github_repos(self, mock_get):
        """Simula la respuesta de la API de GitHub"""
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: [{"name": "test-repo", "description": "Test"}]
        )
        response = self.client.get(reverse('github_repos'))
        self.assertEqual(response.status_code, 200)
```

Ejecutar los tests:
```bash
python manage.py test portfolioCV
```

---

## 10. Diseño Responsive — CSS

### Media queries para móvil
```css
@media (max-width: 768px) {
    .nav-container { flex-wrap: wrap; height: auto; }
    .nav-link { font-size: 0.78rem; padding: 0.35rem 0.5rem; }
    .cv-grid { grid-template-columns: 1fr; }  /* 1 columna en móvil */
    .platforms-grid { grid-template-columns: 1fr; }
    .detail-actions { flex-direction: column; }
}
```

### Selector de tipo de CV (radio buttons estilizados)
```css
.cv-type-option input[type="radio"] { display: none; }

.cv-type-option input[type="radio"]:checked + .cv-type-card {
    border-color: #7c3aed;
    background: #ede9fe;
    box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.15);
}
```

---

## 11. Despliegue en PythonAnywhere

### Pasos de configuración:
1. Crear cuenta en pythonanywhere.com
2. Clonar repositorio: `git clone <url>`
3. Instalar dependencias: `pip3.12 install --user django requests ...`
4. Configurar WSGI apuntando a `PortfolioGenerator.wsgi`
5. Configurar ficheros estáticos: `python manage.py collectstatic`
6. Crear superusuario: `python manage.py createsuperuser`

### Limitaciones del plan gratuito:
- **Proxy obligatorio** → Todas las llamadas HTTP necesitan `proxies=PA_PROXIES`
- **Sin Playwright** → El PDF no se puede generar (falta espacio para Chromium)
- **512 MB de disco** → No instalar dependencias innecesarias

---

## 12. URLs y Recursos (19 endpoints)

| URL | Método | Descripción |
|-----|--------|-------------|
| `/` | GET, POST | Página principal + crear recursos |
| `/registro/` | GET, POST | Registro de usuario |
| `/login/` | GET, POST | Inicio de sesión |
| `/logout/` | GET | Cerrar sesión |
| `/tokens/` | GET, POST | Configurar API keys |
| `/gitlab/` | GET | Listar repos GitLab |
| `/gitlab/<id>/` | GET | Detalle repo GitLab |
| `/github/` | GET | Listar repos GitHub |
| `/github/<owner>/<name>/` | GET | Detalle repo GitHub |
| `/openalex/` | GET | Buscar publicaciones |
| `/openalex/<id>/` | GET | Detalle publicación |
| `/mi-cv/` | GET, POST | Constructor de CV |
| `/mi-cv/add/` | POST | Añadir proyecto al CV |
| `/mi-cv/add-ia/` | POST | Añadir resumen IA al CV |
| `/mi-cv/remove/` | POST | Eliminar del CV |
| `/mi-cv/descargar/` | GET | Descargar PDF o HTML |
| `/gemini/resumen/` | POST | Página de resumen IA |
| `/gemini/stream/` | POST | Streaming texto IA |
| `/<recurso>/eliminar/` | POST | Eliminar recurso |

---

## 13. Dependencias — `requirements.txt`

```
Django
requests
social-auth-app-django
markdown
openai          ← Cliente para NVIDIA Gemma-2 (protocolo OpenAI)
playwright      ← Generación de PDF (solo local)
httpx           ← Cliente HTTP para proxy de PythonAnywhere
django-allauth  ← Login social con GitHub y Google
```

---

## 14. Seguridad

- **CSRF Token**: Todos los formularios POST llevan `{% csrf_token %}`
- **Filtrado por usuario**: Los recursos solo son visibles para su propietario:
  ```python
  ContenidoData.objects.filter(usuario=request.user.username)
  ```
- **Contraseñas**: Django las hashea automáticamente con PBKDF2
- **Tokens ocultos**: Se muestran como `PasswordInput` (tipo `****`)
- **`@login_required`**: Protege todas las rutas sensibles
- **OAuth Social Login**: Las credenciales OAuth (Client ID/Secret) se almacenan en la base de datos a través del Admin Site, nunca en el código fuente
- **Login con validación**: Mensajes de error diferenciados en español (usuario no existe, contraseña incorrecta, contraseña débil)
