# Trabajo Final LTAW

## Requisitos funcionales / Descripción

* Aplicación web en Django que yo le doy mi perfil de GitHub y GitLab y me genere un CV para el proyecto bases de datos de bibliografias de articulos publicados, trabajar en el tema de la autenticacion con la de GitHub con Auth, que me cree el repositorio con el CV subido en GitHub Pages y que la base de datos este con sqlite3.
* La página principal me enseñará dos apartados entre Gitlab y Github y al entrar en cada uno me enseñará los repositorios que tengo en cada uno.
* Al acceder a un repositorio, me creará un CV del portfolio en PDF, y me lo descargará.
* finalmente implementamos la API de Gemini, para que haga un resumen de cada markdown del proyecto. de cada CV y que te deje elegi entre CV extenso, CV de una pagina , CV de tecnologia, CV del TFG del proyecto que estoy realizando.
* la clave se gestiona manualmente en la interaz web como se está haciendo
* NUEVA FUNCIONALIDAD:
  * vamos a añadir que puedas elegir el LLM entre Gemini 2.5 pro, Gemini 2.5 flash y Gemini 3 flash preview y entre una local que tengo con LM Studio con llama-3.2-3b-instruct voy a lanzar un servidor y la ip es http://[IP_ADDRESS], como no será siempre la misma ip que se guarde en la lista de tokens de la web como los otros tokens. 
  * mini funcionalidad: que cuando llames a la IA cualquiera gemini o local, que cuando empieze a generar texto lo envíe y haga la animacion de escribiendo en tiempo real como cuando hablo con Gemini me va escribiendo el texto poco a poco.
* Nueva Funcionalidad 1/05/2026: añade el logo.svg en el index justo encima de Portofolio creator en el medio y centrado, y que sea el favicon de la web.
* Nueva Funcionalidad 1/05/2026: que cada vez que una IA haga cualquier tipo de interaccion te permita extraerlo en pdf o añadirlo al cv profesional que se está creando en la misma pagina con el boton de agregar que está en la lista de repositorios.
* nueva funcionalidad: que cuando de a descargar el CV me deje tambien la opcion de que se descargue en plantilla HTML o en pdf
  * para el CV al subir la foto que me deje acceder al buscador de archivos y se guarde en la base de datos de sqlite y con los otros campos de datos (telefono y linkedin), que la plantilla HTML que generes sea prácticamente completa para subir a una web con tan solo editar algun dato en los campos de la web. que tenga estilo minimalista y moderno. De un igeniero y desarrollador que sirva como portfolio.
* Funcionalidad FINAL, exterior:
  * quiero eliminar la IA de Google Gemini, y poner google/gemma-2-2b-it, desde nvidia: https://build.nvidia.com/
  * que vaya con una API al solicitar, las IAS disponibles será Gemma a traves de nvidia o la local como ya está hecho, para nvidia este es el mecanismo del código:
```
from openai import OpenAI

client = OpenAI(
  base_url = "https://integrate.api.nvidia.com/v1",
  api_key = "$NVIDIA_API_KEY"
)

completion = client.chat.completions.create(
  model="google/gemma-2-2b-it",
  messages=[{"role":"user","content":""}],
  temperature=0.2,
  top_p=0.7,
  max_tokens=1024,
  stream=True
)

for chunk in completion:
  if chunk.choices and chunk.choices[0].delta.content is not None:
    print(chunk.choices[0].delta.content, end="")

```
* guarda en SQLite la base de datos como NVIDIA KEY

## Requisitos NO funcionales
* Usa los templates de DJANGO los comandos de creacion web con DJANGO que DJANGO haga el trabajo sucio de HTML
* Usa Django como framework web
* Usa el entorno virtual venv-django, en el directorio padre, para ejecutar Python (y los comandos de Django)
* Nombre del proyecto Django: `PortfolioGenerator`.
* Crea el proyecto en este mismo directorio, usando `django-admin startproject PortfolioGenerator .`
* Nombre de la app Django: `portfolioCV`
* Usa modelos (models.py) para acceder a la base de datos
* No uses JavaScript.
* Usa el conversor `<str:recurso>` en las URLs de Django para capturar el nombre del recurso.
* Añade CSS para que se vea profesional y elegante.
* USA la api de Gitlab código:
```
# portfolioCV/views.py
import requests

GITLAB_URL = "https://gitlab.eif.urjc.es/api/v4"

def gitlab_repos(request):
    token = request.user.profile.gitlab_token  # o como lo guardes
    headers = {"PRIVATE-TOKEN": token}
    
    # Listar repos del usuario
    response = requests.get(
        f"{GITLAB_URL}/projects",
        headers=headers,
        params={"owned": True, "per_page": 50}
    )
    repos = response.json()
    
    return render(request, "portfolioCV/gitlab_repos.html", {"repos": repos})
```
* la api de Github normal:
```
# portfolioCV/views.py
import requests

GITHUB_API_URL = "https://api.github.com"

def github_repos(request):
    token = request.user.profile.github_token  # o como lo guardes
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Listar repos del usuario
    response = requests.get(
        f"{GITHUB_API_URL}/user/repos",
        headers=headers,
        params={"per_page": 50, "sort": "updated"}
    )
    repos = response.json()
    
    return render(request, "portfolioCV/github_repos.html", {"repos": repos})
```
* usuario y contraseñas serán dadas por GitHub con Auth 
* cuando le des a descargar CV que no solo descargue lo mismo que aparece sino que entre en el proyecto te ponga bien el README.md dentro del pdf y que tambien ponga el nombre de los archivos que hay en el proyecto ordenados por carpetas todo esto dentro del pdf
* PDF: que el pdf sea bonito y facil de leer usa algo parecido al css para el pdf qque el README.md se vea bien como si lo estuviera viedno en gitlab o github. la ordenacion de archivos tambien debe verse bien
* Sigue la misma funcionalidad para OpenAlex, que te pida el token de acceso y que te muestre los repositorios que tienes en OpenAlex o los que quieras buscar en su base de datos para descargar los trabajos, continúa con la misma funcionalidad que en GitHub y GitLab y estética
* NUEVA FUNCIONALIDAD CV:
  * Vamos a añadir un botón con un + que sea agregar
  * lo que hará ese botón de agregar es agregar los repos que quieras de gitlab o github o openalex a un cv que se irá creando en la misma página, para tener un CV profesional
  * este cv se irá guardando en la tabla Contenido-Data en el campo "contenido" y se podrá descargar en cualquier momento con un botón de descargar
  * el cv se irá actualizando cada vez que le des a agregar, se borrará el anterior y se creará uno nuevo con los repositorios que hayas agregado
  * será un CV profesional que cuando tengas en la lista todos los portfolios o documentos o github o gitlab o openalex que quieras agregar le des a un botón de generar cv y te descargue el cv con todo lo que has agregado
  * el cv debe estar bien ordenado y ser bonito y facil de leer
  * puedes añadir foto linkedin y numero de telefono tambien un about me
  * funcionalidad, usa y crea los test.py de Django para probar todo el código generado. Buscando Fallos y bugs y corrigiendolos. Y volviendolo a probar hasta que no haya ningun bug. Y ejecuta siempre python manage.py test.
  * Auth, funcionalidad, voy a usar https://docs.allauth.org/en/dev/index.html para crear inicios de sesión rápido con Github, Google y Apple, para la autentificación. Y que se puedan usar con el servidor local. y con el servidor de producción (creator.danimh.dev).


## Integración con OpenAlex API (Bibliografías)

Para obtener información detallada sobre las publicaciones científicas asociadas a los proyectos, la aplicación deberá integrarse con la API REST de OpenAlex:
* **Endpoint Principal**: `https://api.openalex.org`
* **Autenticación**: Mediante el parámetro `?api_key=TU_CLAVE` en la URL (su uso es gratuito).
* **Entidades principales a consultar**: Se van a mapear las siguientes entidades extraídas de la API:
  * `/works` (obras, artículos, datasets)
  * `/authors` (autores y perfiles identificativos)
  * `/sources` (revistas y repositorios de las publicaciones)
  * `/institutions` (universidades o centros adscritos)
  * `/topics` y `/keywords` (temáticas y palabras clave)
* **Operaciones de filtrado**: Se utilizará el método `GET` realizando llamadas dinámicas implementando los parámetros `?filter=` (para fechas concretas), `?search=` (para buscar textos exactos) o `?per_page=` (para paginación).
* **Gestión de la Respuesta**: Todo el sistema deberá procesar las respuestas que siempre vendrán como formato JSON, mapeando el bloque de datos que proviene dentro de la clave `"results"`.
* **Identificadores Normalizados**: Se puede (y recomienda) habilitar la búsqueda rápida mediante sistemas de identificación universales usando las rutas de la API, tales como un DOI (`/works/doi:...`) o un ORCID para investigadores (`/authors/https://orcid.org/...`).

## API DE GEMINI
integración en el venv 
intalar: pip install -q -U google-genai

from google import genai

# The client gets the API key from the environment variable `GEMINI_API_KEY`.
client = genai.Client()

response = client.models.generate_content(
    model="gemini-3-flash-preview", contents="input_text"
)
print(response.text)



## Estado

* Tabla `Contenido-Data`:
  * `id` (int, primary key, auto increment)
  * `recurso` (str, unique)
  * `contenido` (str)
  * `usuario` (str)
  * `contraseña` (str)
  * `token_GitLab` (str)
  * `token_GitHub` (str)
  * `plataforma` (str)
  * `nombre_repo` (str)
  * `url_repo` (str)
  * `Obras` (str)
  * `Autor` (str)
  * `Fuentes` (str)
  * `instituciones` (str)
  * `topics` (str)
  * `keywords` (str)
  
 



## Inicialización 
* Migra para ver nueva informacion 
* carga datos iniciales si los hubiera
* y haz comprovaciones 

## Recursos

* `/` : Página principal
  * GET: Devuelve una página HTML con:
    * Título `<h1>`: "Portfolio Creator"
    * Párrafo `<p>`: "Elige entre GitLab o Github:"
    * Lista `<ul>` con todos los recursos de la base de datos, donde cada elemento es un enlace `<a>` a `/<nombre_recurso>/`
    * Formulario para crear un nuevo recurso con su contenido. El formulario debe tener un campo para el nombre del recurso y otro para el contenido.
  * POST: Crea un nuevo recurso con el nombre y el contenido proporcionados en el formulario. Para ello, lo almacenará en la tabla Contenido de la base de datos.
* `/<str:recurso>/` : Página de un recurso
  * GET: 
    * Si el recurso existe en la tabla `Contenido`, devuelve una página HTML con:
      * Título `<h1>`: el nombre del recurso (capitalizado)
      * Párrafo `<p>`: el contenido asociado en la base de datos, extraido de la tabla `Contenido`
      * Enlace para volver a `/`
    * Si el recurso no existe en la tabla `Contenido`, devuelve un error HTTP 404 con:
      * Título `<h1>`: "Error 404"
      * Párrafo `<p>`: "El recurso '`<nombre_recurso>`' no fue encontrado"
      * Enlace para volver a `/`
  * GET; Eliminar:
    * Añade un botón para eliminar dicho recurso cuando estés dentro de él

## Entrega
* Crea tambiénn un fichero entrega.md para indicar, brevemente:
  * Hasta qué fase has realizado.
  * Qué parte de lo especificado has realizado en cada fase.