# Guía de Entrevista — Trabajo Final LTAW

Documento preparatorio para la defensa oral. Preguntas típicas del profesor con respuestas claras sobre la **lógica**, no sobre el código en sí.

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
# POST → los datos viajan en el body
platform = request.POST.get('platform')  # body del HTTP
item_id = request.POST.get('id')         # body del HTTP
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
path('<str:recurso>/', views.detalle_recurso)
# Si la URL es /mi-proyecto/ → recurso = "mi-proyecto"
# Si la URL es /notas-clase/ → recurso = "notas-clase"
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
headers = {
    "Authorization": f"Bearer {profile.github_token}",  # Token personal del usuario
    "Accept": "application/vnd.github.v3+json"           # Formato de respuesta deseado
}

response = requests.get(
    f"https://api.github.com/user/repos",   # Endpoint de la API REST de GitHub
    headers=headers,                         # Cabeceras de autenticación
    params={"per_page": 50, "sort": "updated"},  # Query string: ?per_page=50&sort=updated
    timeout=10                               # Máximo 10 segundos esperando respuesta
)

repos = response.json()  # Parsear la respuesta JSON a un diccionario Python
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
@login_required
def gitlab_repos(request):
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
Si te preguntan: *¿Cómo funciona el login con GitHub?*
1. El usuario hace clic en "Entrar con GitHub".
2. Nuestra app lo **redirige** a github.com pidiendo permiso.
3. El usuario acepta en la web de GitHub.
4. GitHub redirige de vuelta a nuestra app (a una URL de **callback**) con un código temporal.
5. Nuestra app (`django-allauth`) intercambia ese código por los datos del usuario.
6. Si el usuario no existía en nuestra BD, lo crea automáticamente. Luego inicia sesión normal (con la cookie `sessionid`).

### B. Streaming y la IA (StreamingHttpResponse)
Si te preguntan: *¿Por qué usas StreamingHttpResponse en vez de un HttpResponse normal para la IA?*
- Si la IA (Gemini/Llama) tarda 40 segundos en generar el resumen, un `HttpResponse` normal se quedaría "cargando" y servicios como PythonAnywhere cortan la conexión por **Timeout** a los 30 segundos dando error.
- Usando `StreamingHttpResponse` con un `yield` en Python, enviamos el texto **palabra por palabra** en tiempo real. 
- La conexión se mantiene viva y el usuario ve un efecto de "máquina de escribir" usando JavaScript (`fetch` y `ReadableStream`).

### C. Persistencia del "Carrito" (JSON Serialization)
Si te preguntan: *¿Cómo guardas en la base de datos que un usuario ha añadido 3 repos y 2 obras al CV?*
- No he creado una tabla por cada ítem. He usado el campo `contenido` (que es de tipo `TextField` / texto largo) de la tabla `ContenidoData`.
- Transformo un **diccionario de Python** con toda la estructura (info personal + array de ítems) a un string de texto usando `json.dumps(data)`. 
- Cuando el usuario entra al creador de CV, leo ese string de la BD y lo vuelvo a convertir a diccionario con `json.loads(texto)`. Es un modelo de datos flexible tipo "NoSQL" dentro de SQLite.

### D. Generación de PDFs (Playwright)
Si te preguntan: *¿Cómo generas el PDF final?*
1. Recopilo los datos de las APIs (descripciones, autores, READMEs).
2. Convierto los READMEs de Markdown a código HTML usando la librería `markdown`.
3. Inyecto todo ese HTML, junto con el CSS, en un template (`cv_template.html`).
4. Utilizo **Playwright** (un navegador web oculto/headless basado en Chromium).
5. Playwright abre ese HTML como si fuera un usuario real, aplica los estilos de GitHub, e imprime la página a PDF devolviendo los **bytes en memoria** (usando `io.BytesIO`), sin necesidad de guardar archivos temporales en el disco del servidor.
