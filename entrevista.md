# Guía de Entrevista — Trabajo Final LTAW

Documento preparatorio para la defensa oral. Preguntas típicas del profesor con respuestas claras sobre la **lógica**, no sobre el código en sí.

---

## 0. Resumen Global: ¿Cómo funciona la aplicación? (El "Elevator Pitch")

Si el profesor te pide: *"Explícame en un minuto qué hace tu aplicación y cómo funciona por debajo"*.

**"Mi aplicación es un Generador de Portafolios Profesionales basado en Django."**
1. **El Usuario:** Se autentica en la plataforma (puede ser mediante usuario/contraseña o OAuth con GitHub). Las claves y tokens de sus APIs (GitHub, GitLab, OpenAlex) se guardan de forma persistente en una tabla de SQLite llamada `UserProfile`.
2. **Extracción de Datos:** Cuando el usuario navega por la app, el backend (Django) hace peticiones HTTP a las APIs REST externas usando esos tokens para extraer en tiempo real sus repositorios y publicaciones.
3. **El Carrito (CV Unificado):** El usuario puede ir añadiendo repositorios a una "cesta" o "carrito". El estado de este carrito se serializa a JSON y se guarda en la base de datos, actuando como un almacén persistente.
4. **Inteligencia Artificial:** He integrado un LLM (Gemini/Local) que lee el README y los lenguajes del repositorio, y genera un resumen automático. Esto se envía al navegador usando *StreamingHTTPResponse* para evitar cuelgues por *timeout*.
5. **Generación de PDF:** Finalmente, con todos los datos recogidos de las APIs y la IA, Django renderiza una plantilla HTML. Luego, usando **Playwright** (un navegador *headless*), "imprimimos" virtualmente ese HTML a PDF en la memoria RAM y se lo enviamos al usuario para descargar. Todo en un flujo continuo sin dejar archivos temporales en el servidor.

---

## 1. HTTP: GET, POST y Query Strings

### ¿Cuándo haces un GET y cuándo un POST?

| Acción | Método | ¿Por qué? |
|--------|--------|-----------|
| Abrir la página principal `/` | **GET** | Solo estoy pidiendo ver la página, no modifico nada |
| Enviar el formulario de login | **POST** | Estoy enviando datos sensibles (usuario y contraseña) al servidor |
| Buscar en OpenAlex `/openalex/?search=BabiaXR` | **GET** | Es una consulta de lectura, los parámetros van en la URL |
| Crear un recurso nuevo | **POST** | Estoy modificando la base de datos (creando un registro) |
| Añadir un repo al CV (`/mi-cv/add/`) | **POST** | Estoy modificando el estado del servidor |
| Descargar un PDF | **GET** | Solo pido que el servidor me devuelva un fichero |

### ¿Dónde está la query string?

La **query string** son los parámetros que van **después del `?`** en la URL.

**Ejemplo real en la app — búsqueda en OpenAlex:**
```
GET /openalex/?search=BabiaXR
                ↑
                Esto es la query string: search=BabiaXR
```

En el código (`views.py`), se recoge así:
```python
query = request.GET.get('search', '').strip()
#       ↑               ↑            ↑
#       |               |            Quitar espacios en blanco
#       |               Nombre del parámetro en la URL
#       Diccionario con todos los parámetros GET de la URL
```

Otro ejemplo — cuando GitHub API envía parámetros:
```python
params = {"per_page": 50, "sort": "updated"}
# Esto se convierte en: ?per_page=50&sort=updated
```

### ¿Y en un POST dónde van los datos?

En el **cuerpo (body)** de la petición HTTP, NO en la URL. Por eso no se ven en la barra del navegador.

```python
# 📌 Archivo: portfolioCV/views.py (Vista agregar_al_cv)
@login_required
def agregar_al_cv(request):
    if request.method == 'POST':
        # Los datos viajan en el cuerpo de la petición HTTP, NO en la URL
        platform = request.POST.get('platform')  
        item_id = request.POST.get('id')         
```

---

## 2. Cookies y Sesiones

### ¿Dónde están las cookies?

Django usa cookies para **mantener la sesión del usuario**. La cookie principal se llama `sessionid`.

**Flujo completo:**

```
1. Usuario hace login (POST /login/)
2. Django verifica usuario/contraseña en la BD
3. Si es correcto:
   a) Crea una entrada en la tabla django_session (en SQLite)
   b) Devuelve una respuesta HTTP con la cabecera:
      Set-Cookie: sessionid=abc123xyz; HttpOnly; Path=/
4. El navegador guarda esa cookie
5. En CADA petición siguiente, el navegador envía:
      Cookie: sessionid=abc123xyz
6. Django lee esa cookie → busca en django_session → sabe quién eres
```

### ¿Por qué se envía la cookie `sessionid` en particular?

- Django la configura en `settings.py` a través del middleware `SessionMiddleware`
- Es la forma de mantener el **estado** entre peticiones HTTP (que son stateless por naturaleza)
- Sin esta cookie, el servidor NO sabría que ya hiciste login → te pediría autenticarte en cada página
- Es `HttpOnly` → JavaScript NO puede leerla (seguridad contra ataques XSS)

**📌 ¿Cómo leo el usuario en mi código?**
Gracias al Middleware de Django que procesa esta cookie `sessionid`, yo no tengo que buscar manualmente en la base de datos. Django me lo da "masticado" en `request.user`:

```python
# 📌 Archivo: portfolioCV/views.py
@login_required
def cv_builder(request):
    # Ya sé quién es el usuario directamente de la petición:
    usuario_actual = request.user 
    contenido_obj, data = _get_cv_data(usuario_actual)
```

### ¿Qué hay dentro de la cookie `sessionid`?

La cookie solo contiene un **ID aleatorio** (ej: `abc123xyz`). Los datos reales de la sesión (quién eres, cuándo se creó, etc.) están en la **tabla `django_session`** de la base de datos SQLite, no en la cookie.

### ¿Qué es la cookie `csrftoken`?

- Es un token de protección contra ataques CSRF (Cross-Site Request Forgery)
- Se envía en cada formulario como un campo oculto: `{% csrf_token %}`
- Django verifica que el token del formulario coincide con el de la cookie
- Sin esto, un sitio malicioso podría enviar formularios en tu nombre

```html
<form method="post">
    {% csrf_token %}    ← Genera: <input type="hidden" name="csrfmiddlewaretoken" value="...">
    ...
</form>
```

### ¿Por qué es importante borrar cookies?

- Si compartes ordenador o usas el del profe, puede haber cookies de otro usuario
- La cookie `sessionid` de otro usuario haría que te logues como él sin querer
- Antes de la demo: **Ctrl+Shift+Supr → borrar cookies del sitio**

---

## 3. Las Plantillas (Templates)

### ¿Dónde están las plantillas?

```
portfolioCV/
  templates/
    portfolioCV/           ← Doble carpeta: convención Django para evitar conflictos
      base.html            ← Plantilla BASE (navbar, footer, CSS)
      index.html           ← Página principal
      login.html           ← Formulario de login
      registro.html        ← Formulario de registro
      tokens.html          ← Configurar API keys
      gitlab_repos.html    ← Lista repos GitLab
      github_repos.html    ← Lista repos GitHub
      openalex_repos.html  ← Búsqueda OpenAlex
      repo_detalle.html    ← Detalle de un repo
      cv_builder.html      ← Constructor de CV (cesta)
      gemini_resumen.html  ← Resumen generado por IA
      detalle.html         ← Detalle de un recurso genérico
      404.html             ← Página de error 404
      cv_template.html     ← Template HTML para generar el PDF individual
      cv_profesional_template.html  ← Template HTML para el PDF unificado
```

### ¿Por qué doble carpeta `templates/portfolioCV/`?

Es la convención de Django. Si tuvieras 2 apps con un `index.html` cada una, Django no sabría cuál usar. Con `portfolioCV/index.html` se evita el conflicto.

### ¿Cómo funciona la herencia de templates?

```
base.html (PADRE)
  ├── define: navbar, footer, CSS, bloque {% block content %}
  │
  ├── index.html (HIJO)
  │     └── {% extends "portfolioCV/base.html" %}
  │     └── {% block content %} ... contenido propio ... {% endblock %}
  │
  ├── login.html (HIJO)
  │     └── {% extends "portfolioCV/base.html" %}
  │     └── {% block content %} ... formulario login ... {% endblock %}
  │
  └── (todos los demás templates HEREDAN de base.html)
```

Esto evita repetir el HTML del navbar/footer en cada página.

### ¿Qué hacen las etiquetas `{% %}` y `{{ }}`?

```html
{% ... %}  →  LÓGICA (bucles, condiciones, herencia)
{{ ... }}  →  MOSTRAR UN VALOR (variable)

Ejemplos:
{% for repo in repos %}          ← Bucle: recorre la lista de repos
    <h3>{{ repo.name }}</h3>     ← Muestra el nombre del repo
{% endfor %}

{% if user.is_authenticated %}   ← Condición: ¿está logueado?
    <p>Hola {{ user.username }}</p>
{% else %}
    <a href="/login/">Entra</a>
{% endif %}

{% csrf_token %}                 ← Genera token anti-CSRF
{% url 'github_repos' %}         ← Genera la URL /github/ automáticamente
{% static 'portfolioCV/css/style.css' %}  ← Ruta al archivo CSS estático
```

---

## 4. Modelo de Datos (Base de Datos)

### ¿Qué tablas tiene la app?

```
┌───────────────────────────────────────┐
│             UserProfile               │
├───────────────────────────────────────┤
│ user (FK → auth_user)  ← El usuario  │
│ github_token           ← Token GitHub │
│ gitlab_token           ← Token GitLab │
│ github_username        ← Username GH  │
│ gitlab_username        ← Username GL  │
│ openalex_token         ← Key OpenAlex │
│ nvidia_api_key         ← Key NVIDIA   │
│ lm_studio_url          ← URL local IA │
└───────────────────────────────────────┘

┌───────────────────────────────────────┐
│            ContenidoData              │
├───────────────────────────────────────┤
│ id (PK, auto)                         │
│ recurso (unique)  ← Nombre del recurso│
│ contenido (text)  ← Texto/JSON        │
│ usuario           ← Quién lo creó     │
│ contraseña                            │
│ token_GitLab / token_GitHub           │
│ plataforma                            │
│ nombre_repo / url_repo                │
│ Obras / Autor / Fuentes              │
│ instituciones / topics / keywords     │
│ fecha_creacion (auto_now_add)         │
└───────────────────────────────────────┘
```

### ¿Por qué `UserProfile` y no usar directamente `User`?

- Django ya trae un modelo `User` integrado con username, password, email
- Pero nosotros necesitamos campos EXTRA (tokens, API keys)
- Solución: crear `UserProfile` con una relación **OneToOneField** → cada User tiene exactamente 1 Profile

```python
user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
#                                   ↑                        ↑
#                                   |                        Acceso inverso: user.profile
#                                   Si borras el User, se borra su Profile
```

### ¿Dónde se guardan las fechas?

```python
fecha_creacion = models.DateTimeField(auto_now_add=True)
#                                     ↑
#                                     Se pone AUTOMÁTICAMENTE la fecha/hora
#                                     del momento en que se CREA el registro.
#                                     NO se puede modificar después.
```

- Se guarda en la tabla `ContenidoData` de SQLite (`db.sqlite3`)
- Django convierte automáticamente al timezone configurado (`Europe/Madrid`)
- Se muestra en los templates con: `{{ c.fecha_creacion|date:"d/m/Y H:i" }}`

### ¿Por qué `recurso` es `unique=True`?

- Cada recurso debe tener un nombre único en la BD
- Si intentas crear otro con el mismo nombre, Django da error
- Así usamos el nombre del recurso como "identificador" en la URL: `/<str:recurso>/`

### ¿Dónde se guarda el CV profesional?

El CV unificado se guarda en la tabla `ContenidoData` como JSON:
```
recurso = "cv_profesional_eldanimh"
contenido = '{"personal_info": {"photo": "...", "name": "...", "linkedin": "..."}, "items": [...]}'
```

Es decir, se reutiliza la misma tabla pero el campo `contenido` almacena un JSON serializado con toda la estructura del CV.

---

## 5. URLs y Routing

### ¿Cómo Django sabe qué vista ejecutar?

```
1. Navegador pide: GET /github/eldanimh/TeoriaLTAW/
2. Django mira PortfolioGenerator/urls.py:
     path('', include('portfolioCV.urls'))  → delega a la app
3. Django mira portfolioCV/urls.py:
     path('github/<str:owner>/<str:repo_name>/', views.github_repo_detalle)
4. Coincide → extrae owner="eldanimh", repo_name="TeoriaLTAW"
5. Llama a: github_repo_detalle(request, owner="eldanimh", repo_name="TeoriaLTAW")
```

### ¿Qué es `<str:recurso>` en las URLs?

Es un **conversor** de Django. Captura una parte de la URL y la pasa como argumento a la vista:

```python
# 📌 Archivo: portfolioCV/urls.py
urlpatterns = [
    # Si la URL es /openalex/123xyz/ -> work_id="123xyz"
    path('openalex/<str:work_id>/', views.openalex_repo_detalle, name='openalex_repo_detalle'),
    
    # Si la URL es /gitlab/456/ -> repo_id=456 (y Django asegura que sea un entero)
    path('gitlab/<int:repo_id>/', views.gitlab_repo_detalle, name='gitlab_repo_detalle'),
]

# 📌 Archivo: portfolioCV/views.py
def openalex_repo_detalle(request, work_id):
    # La variable work_id me llega mágicamente como argumento a la función
    url = f"https://api.openalex.org/works/{work_id}"
```

Tipos de conversores:
- `<str:nombre>` → texto (por defecto)
- `<int:id>` → número entero (ej: `<int:repo_id>` para GitLab)

### ¿Por qué los recursos genéricos van AL FINAL?

```python
urlpatterns = [
    path('gitlab/', ...),           # Rutas específicas primero
    path('github/', ...),
    path('mi-cv/', ...),
    path('<str:recurso>/', ...),    # ← AL FINAL: captura TODO lo que no coincida antes
]
```

Si `<str:recurso>/` fuera primero, `/gitlab/` se interpretaría como `recurso="gitlab"` en vez de ir a la vista de GitLab.

---

## 6. Flujo HTTP Completo (Ejemplo: Login)

```
┌──────────┐                          ┌──────────┐                    ┌─────────┐
│ Navegador│                          │  Django   │                    │ SQLite  │
└────┬─────┘                          └────┬──────┘                    └────┬────┘
     │                                      │                               │
     │  1. GET /login/                      │                               │
     │ ──────────────────────────────────→  │                               │
     │                                      │                               │
     │  2. Devuelve HTML con formulario     │                               │
     │  ←────────────────────────────────── │                               │
     │    + Set-Cookie: csrftoken=xyz       │                               │
     │                                      │                               │
     │  3. POST /login/                     │                               │
     │     Body: username=dani&password=123 │                               │
     │     Cookie: csrftoken=xyz            │                               │
     │ ──────────────────────────────────→  │                               │
     │                                      │  4. SELECT * FROM auth_user   │
     │                                      │     WHERE username='dani'     │
     │                                      │ ─────────────────────────────→│
     │                                      │                               │
     │                                      │  5. Devuelve el usuario       │
     │                                      │ ←─────────────────────────────│
     │                                      │                               │
     │                                      │  6. Verifica contraseña (hash)│
     │                                      │  7. Crea sesión en django_session
     │                                      │ ─────────────────────────────→│
     │                                      │                               │
     │  8. 302 Redirect → /                 │                               │
     │     Set-Cookie: sessionid=abc123     │                               │
     │ ←────────────────────────────────── │                               │
     │                                      │                               │
     │  9. GET / (con Cookie: sessionid)    │                               │
     │ ──────────────────────────────────→  │                               │
     │                                      │                               │
     │  10. HTML de la página principal     │                               │
     │      (usuario autenticado)           │                               │
     │ ←────────────────────────────────── │                               │
```

---

## 7. APIs Externas

### ¿Cómo se conecta con GitHub?

```python
# 📌 Archivo: portfolioCV/views.py (Vista github_repo_detalle)
def github_repo_detalle(request, owner, repo_name):
    profile = get_object_or_404(UserProfile, user=request.user)
    
    # 1. Preparamos las cabeceras con el Token de la base de datos
    headers = {
        "Authorization": f"Bearer {profile.github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # 2. Hacemos la petición HTTP GET a la API externa
    response = requests.get(
        f"https://api.github.com/repos/{owner}/{repo_name}",
        headers=headers,
        timeout=10,
        proxies=PA_PROXIES # Vital: Proxy para salir a Internet en PythonAnywhere
    )

    # 3. Parseamos la respuesta de texto plano a un diccionario Python
    repo_data = response.json() 
```

### ¿Y GitLab URJC?

Misma idea, distinta autenticación:
```python
headers = {"PRIVATE-TOKEN": profile.gitlab_token}  # GitLab usa PRIVATE-TOKEN en vez de Bearer
```

### ¿Y OpenAlex?

No requiere autenticación estricta, pero la API key evita límites:
```python
params = {"search": query, "per_page": 30}
if profile.openalex_token:
    params["api_key"] = profile.openalex_token  # Opcional, va como query string
```

---

## 8. Middleware de Django

### ¿Qué es el middleware?

Son **capas** que procesan cada petición/respuesta ANTES y DESPUÉS de la vista:

```
Petición HTTP →  SecurityMiddleware
              →  SessionMiddleware      ← Lee la cookie sessionid
              →  CommonMiddleware
              →  CsrfViewMiddleware     ← Verifica el token CSRF en POST
              →  AuthenticationMiddleware ← Pone request.user con el usuario
              →  MessageMiddleware      ← Sistema de mensajes flash
              →  XFrameOptionsMiddleware
              →  AccountMiddleware      ← Middleware de allauth (social login)
              →  TU VISTA (views.py)
              ←  (misma cadena en orden inverso para la respuesta)
```

### ¿Qué hace `@login_required`?

Es un **decorador** que se pone encima de la vista:
```python
# 📌 Archivo: portfolioCV/views.py
from django.contrib.auth.decorators import login_required

# Al poner @login_required, el Middleware de Django se activa ANTES
# de ejecutar la función. Si la cookie sessionid no existe o es inválida, 
# la función no se ejecuta y Django devuelve un redirect (302) al /login/
@login_required
def gitlab_repos(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    ...
```

Antes de ejecutar la vista, Django verifica:
1. ¿Tiene cookie `sessionid`? → Si no → redirect a `/login/`
2. ¿La sesión es válida en la BD? → Si no → redirect a `/login/`
3. ¿El usuario está activo? → Si no → redirect a `/login/`
4. Todo OK → ejecuta la vista normalmente

---

## 9. Archivos Estáticos (CSS)

### ¿Dónde está el CSS?

```
portfolioCV/static/portfolioCV/css/style.css
```

### ¿Por qué esa ruta tan larga?

Misma razón que los templates: evitar conflictos si hay más apps con archivos estáticos.

### ¿Cómo se carga en el HTML?

```html
{% load static %}    ← Carga el sistema de archivos estáticos
<link rel="stylesheet" href="{% static 'portfolioCV/css/style.css' %}">
```

Django traduce `{% static '...' %}` a la URL real del archivo (ej: `/static/portfolioCV/css/style.css`).

---

## 10. Preguntas Rápidas Frecuentes

| Pregunta | Respuesta |
|----------|-----------|
| ¿Dónde se guarda la BD? | En `db.sqlite3` (fichero en el directorio raíz) |
| ¿Qué motor de BD usas? | SQLite3 (configurado en `settings.py`) |
| ¿Qué es `manage.py`? | Script de gestión de Django: migraciones, servidor, etc. |
| ¿Qué son las migraciones? | Scripts que modifican la estructura de la BD (crear/alterar tablas) |
| ¿Se usa JavaScript? | Sí, solo para el streaming de la IA (fetch + escritura progresiva) |
| ¿Qué es `{% csrf_token %}`? | Token anti-falsificación en formularios POST |
| ¿Qué es `allauth`? | Librería para login social (GitHub, Google) |
| ¿Por qué `ALLOWED_HOSTS = ['*']`? | Para aceptar peticiones de cualquier dominio (desarrollo/PythonAnywhere) |
| ¿Qué es `SITE_ID = 1`? | Requerido por allauth para identificar el sitio |
| ¿Qué es el `SECRET_KEY`? | Clave criptográfica de Django para firmar cookies y tokens |
| ¿Qué hace `auto_now_add=True`? | Pone la fecha automáticamente al CREAR el registro |
| ¿Qué hace `on_delete=CASCADE`? | Si borras el User → se borra su Profile automáticamente |
| ¿Qué es `StreamingHttpResponse`? | Respuesta que envía datos poco a poco (para streaming IA) |
| ¿Qué es un proxy? | Intermediario de red (necesario en PythonAnywhere free) |

---

## 11. Conceptos Arquitectónicos Avanzados (Para subir nota)

### A. Login Social (OAuth con GitHub/Google)
Si te preguntan: *¿Cómo funciona exactamente el login con GitHub?*

El protocolo OAuth2 es un "baile" a 3 bandas entre el Navegador, nuestro Servidor (Django) y el Servidor de GitHub. Su objetivo principal es que el usuario se autentique **sin tener que darnos su contraseña**.

```
┌──────────┐                          ┌──────────┐                    ┌─────────┐
│ Navegador│                          │  Django  │                    │ GitHub  │
└────┬─────┘                          └────┬─────┘                    └────┬────┘
     │                                     │                               │
     │ 1. Clic en "Entrar con GitHub"      │                               │
     │ ──────────────────────────────────→ │                               │
     │                                     │                               │
     │ 2. 302 Redirect a github.com/login  │                               │
     │    (Incluye nuestro CLIENT_ID)      │                               │
     │ ←─────────────────────────────────  │                               │
     │                                     │                               │
     │ 3. GET github.com/login             │                               │
     │ ──────────────────────────────────────────────────────────────────→ │
     │                                     │                               │
     │ 4. GitHub muestra: "¿Das permiso a  │                               │
     │    PortfolioGen para leer tus datos?"                               │
     │ ←────────────────────────────────────────────────────────────────── │
     │                                     │                               │
     │ 5. Usuario pulsa "Autorizar"        │                               │
     │ ──────────────────────────────────────────────────────────────────→ │
     │                                     │                               │
     │ 6. 302 Redirect de vuelta a Django  │                               │
     │    URL: /callback/?code=XYZ123      │                               │
     │ ←────────────────────────────────────────────────────────────────── │
     │                                     │                               │
     │ 7. GET /callback/?code=XYZ123       │                               │
     │ ──────────────────────────────────→ │                               │
     │                                     │ 8. POST a GitHub con:         │
     │                                     │    - code=XYZ123              │
     │                                     │    - CLIENT_SECRET            │
     │                                     │ ────────────────────────────→ │
     │                                     │                               │
     │                                     │ 9. Devuelve Access Token      │
     │                                     │ ←──────────────────────────── │
     │                                     │                               │
     │                                     │ 10. Django usa el Token para  │
     │                                     │     pedir email y nombre      │
     │                                     │ ────────────────────────────→ │
     │                                     │                               │
     │                                     │ 11. Devuelve {"email": "..."} │
     │                                     │ ←──────────────────────────── │
     │                                     │                               │
     │                                     │ 12. Django crea/busca al User │
     │                                     │ 13. Crea cookie sessionid     │
     │                                     │                               │
     │ 14. 302 Redirect a página principal │                               │
     │     Set-Cookie: sessionid=abc123    │                               │
     │ ←─────────────────────────────────  │                               │
```

**Resumen clave para el profe:**
1. Nosotros nunca vemos la contraseña del usuario.
2. Todo se basa en intercambiar un **código temporal** (paso 6) por un **Token de Acceso** (paso 9).
3. El intercambio se hace **de servidor a servidor** usando un "Client Secret" que nadie más conoce.
4. `django-allauth` abstrae todo este "baile".

**📌 ¿Dónde está esto en el código?**
Todo este motor no está en `views.py` porque lo gestiona la librería `allauth`. Se configura en dos sitios clave:

- **Archivo `PortfolioGenerator/settings.py`**:
  ```python
  INSTALLED_APPS = [
      ...
      'allauth',
      'allauth.account',
      'allauth.socialaccount',
      'allauth.socialaccount.providers.github',
  ]
  ```
- **Archivo `PortfolioGenerator/urls.py`** (Línea 14):
  ```python
  urlpatterns = [
      ...
      path('accounts/', include('allauth.urls')), # Delega el OAuth a allauth
  ]
  ```
### B. Streaming y la IA (StreamingHttpResponse)
Si te preguntan: *¿Por qué usas StreamingHttpResponse en vez de un HttpResponse normal para la IA?*
- Si la IA (Gemini/Llama) tarda 40 segundos en generar el resumen, un `HttpResponse` normal se quedaría "cargando" y servicios como PythonAnywhere cortan la conexión por **Timeout** a los 30 segundos dando error.
- Usando `StreamingHttpResponse` con un `yield` en Python, enviamos el texto **palabra por palabra** en tiempo real. 

**📌 ¿Dónde está esto en el código?**
- **Archivo `portfolioCV/views.py`** (a partir de la línea 906):
  ```python
  from django.http import StreamingHttpResponse

  def stream_resumen_gemini(request):
      def event_stream():
          ...
          # Petición a la API de la IA con stream=True
          response = client.chat.completions.create(..., stream=True)
          
          # Bucle que "escupe" trocitos de texto al navegador
          for chunk in response:
              yield chunk.choices[0].delta.content 
              
      # Devuelve la respuesta manteniendo la conexión abierta
      return StreamingHttpResponse(event_stream(), content_type='text/plain')
  ```
### C. Persistencia del "Carrito" (JSON Serialization)
Si te preguntan: *¿Cómo guardas en la base de datos que un usuario ha añadido 3 repos y 2 obras al CV?*
- No he creado una tabla por cada ítem. He usado el campo `contenido` (que es un `TextField`) de la tabla `ContenidoData`.
- Transformo un **diccionario de Python** a un string usando `json.dumps(data)`. Y para leer, `json.loads(texto)`.

**📌 ¿Dónde está esto en el código?**
- **Archivo `portfolioCV/models.py`** (Línea 30):
  ```python
  class ContenidoData(models.Model):
      ...
      contenido = models.TextField() # Aquí guardamos todo el JSON gigante
  ```
- **Archivo `portfolioCV/views.py`** (Línea 679 - `_get_cv_data` y 714 - `cv_builder`):
  ```python
  # LEER de la BD: de String a Diccionario Python
  data = json.loads(contenido_obj.contenido) 

  # ESCRIBIR a la BD: de Diccionario Python a String
  contenido_obj.contenido = json.dumps(data)
  contenido_obj.save()
  ```
### D. Generación de PDFs (Playwright)
Si te preguntan: *¿Cómo generas el PDF final?*
1. Recopilo los datos de las APIs y convierto los Markdown a HTML.
2. Inyecto todo ese HTML en un template (`cv_template.html`).
3. Playwright abre ese HTML como si fuera un usuario, aplica los estilos, e imprime a PDF devolviendo los **bytes en memoria** (`io.BytesIO`), sin guardar basura en el disco duro.

**📌 ¿Dónde está esto en el código?**
- **Archivo `portfolioCV/views.py`** (a partir de la línea 597 - `_generar_pdf`):
  ```python
  import io
  from playwright.sync_api import sync_playwright

  buffer = io.BytesIO() # RAM virtual, no es disco duro
  
  with sync_playwright() as p:
      browser = p.chromium.launch(headless=True) # Navegador invisible
      page = browser.new_page()
      page.set_content(html_string, wait_until='networkidle')
      
      # Imprime a PDF
      pdf_bytes = page.pdf(format="A4", print_background=True)
      browser.close()

  buffer.write(pdf_bytes) # Guardamos en memoria
  response = HttpResponse(buffer, content_type='application/pdf')
  ```
