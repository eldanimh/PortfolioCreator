# ─── IMPORTACIONES ─────────────────────────────────────────
import io        # Módulo para manejar buffers de bytes en memoria (para generar PDFs)
import json      # Módulo para serializar/deserializar JSON (para el CV profesional)
import requests  # Librería HTTP para hacer peticiones GET/POST a APIs externas (GitHub, GitLab, OpenAlex)
from django.shortcuts import render, redirect, get_object_or_404  # Funciones de atajo de Django
# render: renderiza un template HTML con un contexto (diccionario de variables)
# redirect: redirige al navegador a otra URL (genera respuesta HTTP 302)
# get_object_or_404: busca un objeto en la BD o devuelve error 404 si no existe
from django.http import HttpResponse, Http404  # Clases de respuesta HTTP
from django.contrib.auth import login, logout, authenticate  # Funciones de autenticación de Django
# login: crea la sesión del usuario (guarda en django_session y envía cookie sessionid)
# logout: destruye la sesión (borra de django_session y elimina la cookie)
# authenticate: verifica usuario+contraseña contra la BD (devuelve User o None)
from django.contrib.auth.decorators import login_required  # Decorador que protege vistas
# @login_required: si no hay cookie sessionid válida → redirige a /login/
from django.contrib.auth.forms import AuthenticationForm  # Formulario de login de Django
from django.contrib import messages  # Sistema de mensajes flash (se muestran una vez al usuario)
from .models import UserProfile, ContenidoData  # Nuestros modelos de BD
from .forms import RegistroForm, TokensForm, ContenidoForm  # Nuestros formularios
from .seguridad import url_externa_segura  # Valida URLs que introduce el usuario (anti-SSRF)
from django.conf import settings

# ─── URLs base de las APIs externas ────────────────────────
GITLAB_DEFAULT_URL = "https://gitlab.com"  # Instancia por defecto si el usuario no indica otra
GITHUB_API_URL = "https://api.github.com"                # API REST v3 de GitHub


def gitlab_api_url(profile):
    """Devuelve la URL base de la API v4 de la instancia GitLab del usuario (cualquier GitLab)"""
    base = (profile.gitlab_url or GITLAB_DEFAULT_URL).strip().rstrip('/')
    if not url_externa_segura(base):
        base = GITLAB_DEFAULT_URL  # nunca llamamos a una dirección interna
    if base.endswith('/api/v4'):
        base = base[:-len('/api/v4')]
    return f"{base}/api/v4"


def modelo_permitido(request):
    """Lee el modelo elegido y descarta 'local' (LM Studio) si no está permitido en este entorno"""
    modelo = request.POST.get('llm_model', 'nvidia-gemma')
    if modelo == 'local' and not settings.ALLOW_LOCAL_LLM:
        return 'nvidia-gemma'
    return modelo


# ─── Página principal ──────────────────────────────────────
def index(request):
    """Página principal con dos apartados: GitLab y GitHub"""
    # Si el usuario está autenticado (tiene cookie sessionid válida),
    # recuperamos sus recursos de la BD ordenados por fecha (más reciente primero)
    if request.user.is_authenticated:
        contenidos = ContenidoData.objects.filter(usuario=request.user.username).order_by('-fecha_creacion')
    else:
        contenidos = []  # Usuario anónimo: no ve recursos

    # Si el método HTTP es POST → el usuario está enviando el formulario para crear un recurso
    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, 'Debes iniciar sesión para crear recursos.')
            return redirect('login')  # Redirige a /login/ (HTTP 302)
        form = ContenidoForm(request.POST)  # request.POST es un diccionario con los datos del body
        if form.is_valid():  # Valida que los campos cumplan las restricciones del modelo
            contenido = form.save(commit=False)  # Crea el objeto PERO no lo guarda aún en la BD
            contenido.usuario = request.user      # Asignamos el usuario actual antes de guardar
            contenido.save()                      # AHORA sí se guarda en SQLite (INSERT INTO...)
            messages.success(request, f'Recurso "{contenido.recurso}" creado correctamente.')
            return redirect('index')  # Redirige a la misma página (patrón POST-Redirect-GET)
    else:
        form = ContenidoForm()  # GET → formulario vacío para mostrar

    # render() combina el template HTML con las variables del contexto y devuelve HTTP 200
    return render(request, 'portfolioCV/index.html', {
        'contenidos': contenidos,  # Lista de recursos para el template
        'form': form,              # Formulario (vacío o con errores)
    })


# ─── Política de privacidad ────────────────────────────────
def privacidad(request):
    """Política de privacidad (página estática)."""
    return render(request, 'portfolioCV/privacidad.html')


# ─── Condiciones del servicio ──────────────────────────────
def condiciones(request):
    """Condiciones del Servicio (página estática)."""
    return render(request, 'portfolioCV/condiciones.html')


# ─── Detalle de recurso ────────────────────────────────────
def detalle_recurso(request, recurso):
    """Muestra el contenido de un recurso específico"""
    # 'recurso' viene de la URL: /<str:recurso>/ (capturado por el conversor de Django)
    try:
        # Busca en la BD un ContenidoData con ese nombre de recurso
        contenido = ContenidoData.objects.get(recurso=recurso)
    except ContenidoData.DoesNotExist:
        # Si no existe → devuelve página 404 con código de estado HTTP 404
        return render(request, 'portfolioCV/404.html', {
            'recurso': recurso,
        }, status=404)

    return render(request, 'portfolioCV/detalle.html', {
        'contenido': contenido,
    })


# ─── Eliminar recurso ──────────────────────────────────────
@login_required  # Solo usuarios autenticados pueden borrar (si no → redirige a /login/)
def eliminar_recurso(request, recurso):
    """Elimina un recurso de la base de datos"""
    # get_object_or_404: busca el recurso, si no existe devuelve HTTP 404 automáticamente
    contenido = get_object_or_404(ContenidoData, recurso=recurso)
    contenido.delete()  # DELETE FROM contenidodata WHERE recurso='...'
    messages.success(request, f'Recurso "{recurso}" eliminado correctamente.')
    return redirect('index')  # Vuelve a la página principal


# ─── Autenticación ─────────────────────────────────────────
def registro_view(request):
    """Registro de nuevo usuario — POST crea la cuenta, GET muestra el formulario"""
    if request.method == 'POST':  # El usuario ha enviado el formulario (datos en el body HTTP)
        form = RegistroForm(request.POST)  # Rellenamos el formulario con los datos del POST
        if form.is_valid():  # Valida: username único, contraseña segura, contraseñas coinciden
            user = form.save()  # Crea el User en la BD (INSERT INTO auth_user...)
            UserProfile.objects.get_or_create(user=user)  # Obtiene el perfil (creado por la signal) o lo crea si no existe
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')  # Especificamos el backend porque tenemos 2 (normal + allauth)
            messages.success(request, '¡Cuenta creada correctamente! Configura tus tokens.')
            return redirect('configurar_tokens')  # Redirige a /tokens/ (HTTP 302)
        else:
            # Si la validación falla, traducimos los errores de Django al español
            for field, errors in form.errors.items():
                for error in errors:
                    if 'already exists' in error or 'ya existe' in error:
                        messages.error(request, f'El nombre de usuario "{form.data.get("username", "")}" ya está registrado. Elige otro.')
                    elif 'too short' in error or 'muy corta' in error or 'at least' in error:
                        messages.error(request, 'La contraseña debe tener al menos 8 caracteres.')
                    elif 'too common' in error or 'muy común' in error:
                        messages.error(request, 'Esa contraseña es demasiado común. Usa una más segura.')
                    elif 'entirely numeric' in error or 'numérica' in error:
                        messages.error(request, 'La contraseña no puede ser completamente numérica.')
                    elif 'too similar' in error or 'similar' in error:
                        messages.error(request, 'La contraseña es demasiado parecida a tu nombre de usuario.')
                    elif 'didn' in error or 'no coinciden' in error or 'match' in error:
                        messages.error(request, 'Las dos contraseñas no coinciden.')
    else:
        form = RegistroForm()  # GET → formulario vacío
    return render(request, 'portfolioCV/registro.html', {'form': form})


def login_view(request):
    """Inicio de sesión — verifica credenciales y crea la cookie de sesión"""
    if request.method == 'POST':  # El usuario envió usuario+contraseña
        # request.POST.get() lee los datos del BODY de la petición HTTP (no de la URL)
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        
        # Primero comprobamos si el usuario existe en la BD
        from django.contrib.auth.models import User
        user_exists = User.objects.filter(username=username).exists()  # SELECT COUNT(*) WHERE...
        
        if not username or not password:
            messages.error(request, 'Por favor, rellena todos los campos.')
        elif not user_exists:
            messages.error(request, f'No existe ninguna cuenta con el usuario "{username}". ¿Quieres registrarte?')
        else:
            # authenticate() verifica el hash de la contraseña contra la BD
            # Django NUNCA guarda contraseñas en texto plano, usa hashing (pbkdf2_sha256)
            user = authenticate(request, username=username, password=password)
            if user is not None:  # Contraseña correcta
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')  # Especificamos el backend
                UserProfile.objects.get_or_create(user=user)  # Asegura que tiene perfil
                messages.success(request, f'¡Bienvenido, {user.username}!')
                return redirect('index')  # HTTP 302 → /
            else:
                messages.error(request, 'Contraseña incorrecta. Inténtalo de nuevo.')
        
        form = AuthenticationForm()
    else:
        form = AuthenticationForm()  # GET → formulario vacío
    return render(request, 'portfolioCV/login.html', {'form': form})


def logout_view(request):
    """Cerrar sesión — destruye la cookie sessionid y la entrada en django_session"""
    logout(request)  # Borra la sesión de la BD y la cookie del navegador
    messages.info(request, 'Has cerrado sesión correctamente.')
    return redirect('index')


# ─── Configurar tokens ─────────────────────────────────────
@login_required  # Requiere cookie sessionid válida → si no, redirige a LOGIN_URL (/login/)
def configurar_tokens(request):
    """Página para configurar los tokens de GitHub y GitLab"""
    # get_or_create: busca el perfil del usuario, si no existe lo crea (para usuarios de social login)
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':  # El usuario envió el formulario con tokens
        # instance=profile: indica que estamos EDITANDO un perfil existente (UPDATE), no creando uno nuevo
        form = TokensForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()  # UPDATE userprofile SET github_token='...', gitlab_token='...' WHERE user_id=...
            messages.success(request, '¡Tokens actualizados correctamente!')
            return redirect('index')
    else:
        form = TokensForm(instance=profile)
    return render(request, 'portfolioCV/tokens.html', {'form': form})


# ─── GitLab - Repositorios ────────────────────────────
@login_required
def gitlab_repos(request):
    """Lista los repositorios del usuario en GitLab — petición GET a la API de GitLab"""
    profile = get_object_or_404(UserProfile, user=request.user)  # Busca el perfil del usuario

    # Verificar que el usuario tiene un token configurado
    if not profile.gitlab_token:
        messages.warning(request, 'Configura tu token de GitLab primero.')
        return redirect('configurar_tokens')

    # Cabecera HTTP de autenticación: GitLab usa PRIVATE-TOKEN (diferente a GitHub que usa Bearer)
    headers = {"PRIVATE-TOKEN": profile.gitlab_token}
    repos = []
    error_msg = None

    try:
        # Petición GET a la API REST de GitLab: GET /api/v4/projects?owned=True&per_page=50
        # params se convierten en query string: ?owned=True&per_page=50
        response = requests.get(
            f"{gitlab_api_url(profile)}/projects",       # URL del endpoint
            headers=headers,                      # Cabeceras HTTP (con el token)
            params={"owned": True, "per_page": 50},  # Query string: solo mis repos, máximo 50
            timeout=10,                           # Máximo 10 segundos esperando respuesta
            allow_redirects=False                 # No seguir redirecciones (podrían ir a una IP interna)
        )
        if response.status_code == 200:   # HTTP 200 OK → éxito
            repos = response.json()       # Parsea el JSON de la respuesta a lista Python
        else:
            error_msg = f"Error al conectar con GitLab (código {response.status_code}). Verifica tu token."
    except requests.exceptions.RequestException as e:  # Error de red (timeout, DNS, etc.)
        error_msg = f"No se pudo conectar con GitLab: {str(e)}"

    # Renderiza el template con la lista de repos (o el mensaje de error)
    return render(request, 'portfolioCV/gitlab_repos.html', {
        'repos': repos,           # Lista de diccionarios con datos de cada repo
        'error_msg': error_msg,   # Mensaje de error (None si todo fue bien)
        'platform': 'GitLab',
    })


# ─── GitHub - Repositorios ─────────────────────────────────
@login_required
def github_repos(request):
    """Lista los repositorios del usuario en GitHub — usa Bearer token (diferente a GitLab)"""
    profile = get_object_or_404(UserProfile, user=request.user)

    if not profile.github_token:
        messages.warning(request, 'Configura tu token de GitHub primero.')
        return redirect('configurar_tokens')

    # Cabeceras HTTP: GitHub usa "Authorization: Bearer <token>" y el header Accept
    # para indicar que queremos respuesta en formato JSON v3
    headers = {
        "Authorization": f"Bearer {profile.github_token}",     # Token en cabecera Authorization
        "Accept": "application/vnd.github.v3+json"              # Formato de respuesta deseado
    }
    repos = []
    error_msg = None

    try:
        # GET /user/repos → devuelve los repos del usuario autenticado
        # Query string: ?per_page=50&sort=updated (los 50 más recientes)
        response = requests.get(
            f"{GITHUB_API_URL}/user/repos",
            headers=headers,
            params={"per_page": 50, "sort": "updated"},  # Se convierte en query string en la URL
            timeout=10,
        )
        if response.status_code == 200:
            repos = response.json()  # Parsea JSON → lista de diccionarios Python
        else:
            error_msg = f"Error al conectar con GitHub (código {response.status_code}). Verifica tu token."
    except requests.exceptions.RequestException as e:
        error_msg = f"No se pudo conectar con GitHub: {str(e)}"

    return render(request, 'portfolioCV/github_repos.html', {
        'repos': repos,
        'error_msg': error_msg,
        'platform': 'GitHub',
    })


# ─── OpenAlex - Bibliografías ──────────────────────────────
@login_required
def openalex_repos(request):
    """Busca obras científicas en OpenAlex — la búsqueda va por QUERY STRING en GET"""
    profile = get_object_or_404(UserProfile, user=request.user)
    # request.GET.get('search') → lee el parámetro 'search' de la URL
    # Ejemplo: /openalex/?search=BabiaXR → query = "BabiaXR"
    # Esto es la QUERY STRING: los datos van en la URL después del ?
    query = request.GET.get('search', '').strip()
    
    repos = []
    error_msg = None

    if query:  # Solo busca si hay algo escrito
        url = "https://api.openalex.org/works"  # Endpoint de la API de OpenAlex
        params = {"search": query, "per_page": 30}  # Query string: ?search=BabiaXR&per_page=30
        if profile.openalex_token:
            params["api_key"] = profile.openalex_token  # API key opcional para evitar rate limits
            
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()  # La respuesta viene como JSON
                results = data.get('results', [])  # Lista de obras científicas
                for work in results:
                    # Extraer nombres de autores de la estructura anidada
                    authors = ", ".join([a.get('author', {}).get('display_name', '') for a in work.get('authorships', [])])
                    # Normalizar la estructura para que sea compatible con el template de repos
                    repos.append({
                        'id': work.get('id', '').split('/')[-1],  # Extraer solo el ID (última parte de la URL)
                        'name': work.get('title', 'Sin título')[:100],  # Título truncado a 100 chars
                        'description': authors,          # Los autores como descripción
                        'language': work.get('language', 'unknown'),
                        'visibility': work.get('type', 'work').capitalize(),
                        'created_at': work.get('publication_year'),
                    })
            else:
                error_msg = f"Error al conectar con OpenAlex (código {response.status_code})."
        except requests.exceptions.RequestException as e:
            error_msg = f"Error al buscar en OpenAlex: {str(e)}"
    
    return render(request, 'portfolioCV/openalex_repos.html', {
        'repos': repos,
        'error_msg': error_msg,
        'platform': 'OpenAlex',
        'query': query  # Devolvemos la búsqueda para mostrarla en el input del template
    })

@login_required
def openalex_repo_detalle(request, work_id):
    """Detalle de una obra científica — work_id viene de la URL: /openalex/<work_id>/"""
    profile = get_object_or_404(UserProfile, user=request.user)
    repo = None
    languages = {}
    error_msg = None
    
    url = f"https://api.openalex.org/works/{work_id}"
    params = {}
    if profile.openalex_token:
        params["api_key"] = profile.openalex_token
        
    try:
        # GET a la API de OpenAlex: obtiene todos los datos de una obra específica
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            work = resp.json()  # Parsea el JSON de la respuesta
            # Normalizamos la estructura para reutilizar el mismo template que GitHub/GitLab
            repo = {
                'name': work.get('title', 'Sin título'),
                'description': f"Publicado en {work.get('publication_year', 'Desconocido')}",
                'web_url': work.get('id'),
                'created_at': work.get('publication_date'),
                'default_branch': work.get('type', 'N/A')
            }
            # Los 'topics' de OpenAlex se usan como si fueran 'lenguajes' de programación
            # para reutilizar el mismo template de porcentajes
            topics = work.get('topics', [])
            total_score = sum([t.get('score', 0) for t in topics])
            if total_score > 0:
                for t in topics:
                    # Calculamos el porcentaje de cada topic sobre el total
                    languages[t.get('display_name')] = int((t.get('score', 0) / total_score) * 100)
            else:
                languages = {work.get('language', 'N/A'): 100}  # Fallback: idioma de la obra
        else:
            error_msg = f"Obra no encontrada (Error {resp.status_code})"
    except requests.exceptions.RequestException as e:
        error_msg = str(e)

    return render(request, 'portfolioCV/repo_detalle.html', {
        'repo': repo,
        'languages': _language_bars(languages),
        'error_msg': error_msg,
        'platform': 'OpenAlex',
        'work_id': work_id,
    })



# ─── Detalle de repo GitLab ────────────────────────────────
@login_required
def gitlab_repo_detalle(request, repo_id):
    """Detalle de un repo GitLab — repo_id (entero) viene de la URL: /gitlab/<int:repo_id>/"""
    profile = get_object_or_404(UserProfile, user=request.user)
    headers = {"PRIVATE-TOKEN": profile.gitlab_token}  # Auth de GitLab
    repo = None
    languages = {}
    error_msg = None

    try:
        # 1ª petición: GET /projects/{id} → info general del repo (nombre, descripción, URL)
        resp = requests.get(f"{gitlab_api_url(profile)}/projects/{repo_id}", headers=headers, timeout=10, allow_redirects=False)
        if resp.status_code == 200:
            repo = resp.json()

        # 2ª petición: GET /projects/{id}/languages → porcentaje de cada lenguaje
        resp_lang = requests.get(f"{gitlab_api_url(profile)}/projects/{repo_id}/languages", headers=headers, timeout=10, allow_redirects=False)
        if resp_lang.status_code == 200:
            languages = resp_lang.json()  # Ej: {"Python": 65.2, "JavaScript": 34.8}
    except requests.exceptions.RequestException as e:
        error_msg = str(e)

    return render(request, 'portfolioCV/repo_detalle.html', {
        'repo': repo,
        'languages': _language_bars(languages),
        'error_msg': error_msg,
        'platform': 'GitLab',
        'repo_id': repo_id,
    })


# ─── Detalle de repo GitHub ────────────────────────────────
@login_required
def github_repo_detalle(request, owner, repo_name):
    """Detalle de un repo GitHub — owner y repo_name vienen de /github/<owner>/<repo_name>/"""
    profile = get_object_or_404(UserProfile, user=request.user)
    headers = {
        "Authorization": f"Bearer {profile.github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    repo = None
    languages = {}
    error_msg = None

    try:
        resp = requests.get(f"{GITHUB_API_URL}/repos/{owner}/{repo_name}", headers=headers, timeout=10)
        if resp.status_code == 200:
            repo = resp.json()

        resp_lang = requests.get(f"{GITHUB_API_URL}/repos/{owner}/{repo_name}/languages", headers=headers, timeout=10)
        if resp_lang.status_code == 200:
            languages = resp_lang.json()
    except requests.exceptions.RequestException as e:
        error_msg = str(e)

    return render(request, 'portfolioCV/repo_detalle.html', {
        'repo': repo,
        'languages': _language_bars(languages),
        'error_msg': error_msg,
        'platform': 'GitHub',
        'owner': owner,
        'repo_name': repo_name,
    })


# ─── Generar CV en PDF ─────────────────────────────────────
@login_required
def generar_cv_gitlab(request, repo_id):
    """Genera un CV en PDF de un repo GitLab. Hace 4 llamadas API para recopilar todos los datos."""
    profile = get_object_or_404(UserProfile, user=request.user)
    headers = {"PRIVATE-TOKEN": profile.gitlab_token}

    repo = {}
    languages = {}
    tree = []
    readme = ""
    try:
        resp = requests.get(f"{gitlab_api_url(profile)}/projects/{repo_id}", headers=headers, timeout=10, allow_redirects=False)
        if resp.status_code == 200:
            repo = resp.json()
        
        default_branch = repo.get('default_branch', 'main')

        # 2ª llamada: obtener lenguajes
        resp_lang = requests.get(f"{gitlab_api_url(profile)}/projects/{repo_id}/languages", headers=headers, timeout=10, allow_redirects=False)
        if resp_lang.status_code == 200:
            languages = resp_lang.json()

        # 3ª llamada: obtener el árbol de archivos (recursive=true para subcarpetas)
        resp_tree = requests.get(f"{gitlab_api_url(profile)}/projects/{repo_id}/repository/tree", headers=headers, params={"recursive": "true", "ref": default_branch}, timeout=10, allow_redirects=False)
        if resp_tree.status_code == 200:
            # Filtramos solo los archivos (tipo 'blob'), ignorando carpetas ('tree')
            tree = [item['path'] for item in resp_tree.json() if item.get('type') == 'blob']
        
        # 4ª llamada: obtener el README
        # Intentamos obtenerlo asumiendo que se llama README.md en la rama principal
        resp_readme = requests.get(f"{gitlab_api_url(profile)}/projects/{repo_id}/repository/files/README.md/raw", headers=headers, params={"ref": default_branch}, timeout=10, allow_redirects=False)
        if resp_readme.status_code == 200:
            readme = resp_readme.text
        else:
            readme = "No se encontró README.md u ocurrió un error."

    except requests.exceptions.RequestException:
        pass  # Si falla algo, pasamos variables vacías a _generar_pdf y allí se gestiona

    # Delega la creación real del PDF a la función común _generar_pdf
    return _generar_pdf(request.user, repo, languages, tree, readme, 'GitLab')


@login_required
def generar_cv_github(request, owner, repo_name):
    """Genera un CV en PDF de un repo GitHub. Hace 4 llamadas API (info, lenguajes, árbol, README)."""
    profile = get_object_or_404(UserProfile, user=request.user)
    headers = {
        "Authorization": f"Bearer {profile.github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    repo = {}
    languages = {}
    tree = []
    readme = ""
    try:
        resp = requests.get(f"{GITHUB_API_URL}/repos/{owner}/{repo_name}", headers=headers, timeout=10)
        if resp.status_code == 200:
            repo = resp.json()

        default_branch = repo.get('default_branch', 'main')

        # 2ª llamada: Lenguajes
        resp_lang = requests.get(f"{GITHUB_API_URL}/repos/{owner}/{repo_name}/languages", headers=headers, timeout=10)
        if resp_lang.status_code == 200:
            languages = resp_lang.json()

        # 3ª llamada: Árbol de archivos (API de Git Data)
        resp_tree = requests.get(f"{GITHUB_API_URL}/repos/{owner}/{repo_name}/git/trees/{default_branch}", headers=headers, params={"recursive": "1"}, timeout=10)
        if resp_tree.status_code == 200:
             # Filtramos para obtener solo paths de archivos que no sean subárboles (blob)
            tree_data = resp_tree.json().get('tree', [])
            tree = [item['path'] for item in tree_data if item.get('type') == 'blob']
            
        # 4ª llamada: README (formato RAW)
        # Cambiamos el header Accept para pedir el README en raw markdown, no en JSON base64
        headers_readme = {
            "Authorization": f"Bearer {profile.github_token}",
            "Accept": "application/vnd.github.v3.raw"
        }
        resp_readme = requests.get(f"{GITHUB_API_URL}/repos/{owner}/{repo_name}/readme", headers=headers_readme, timeout=10)
        if resp_readme.status_code == 200:
            readme = resp_readme.text
        else:
            readme = "No se encontró README u ocurrió un error al extraerlo."

    except requests.exceptions.RequestException:
        pass

    return _generar_pdf(request.user, repo, languages, tree, readme, 'GitHub')



@login_required
def generar_cv_openalex(request, work_id):
    """Genera PDF de una obra de OpenAlex usando la misma plantilla que los repositorios."""
    profile = get_object_or_404(UserProfile, user=request.user)
    
    url = f"https://api.openalex.org/works/{work_id}"
    params = {}
    if profile.openalex_token:
        params["api_key"] = profile.openalex_token
        
    repo = {}
    languages = {}
    tree = []
    readme = ""
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        work = resp.json() if resp.status_code == 200 else {}
        
        if work:
            repo = {
                'name': work.get('title', 'Sin título'),
                'web_url': work.get('id'),
                'last_activity_at': work.get('publication_date', 'N/A')
            }
            
            # OpenAlex devuelve el Abstract (resumen) de forma peculiar (Inverted Index)
            # Viene como un diccionario: {"palabra": [posicion1, posicion2]}
            # Hay que reconstruir el texto ordenando las palabras por su posición
            abs_idx = work.get('abstract_inverted_index')
            if abs_idx:
                words = {}
                for word, pos_list in abs_idx.items():
                    for pos in pos_list:
                        words[pos] = word
                # Une las palabras en el orden de las posiciones (sorted)
                abstract = " ".join([words[p] for p in sorted(words.keys())])
                readme = f"## Resumen (Abstract)\n\n{abstract}\n\n"
            else:
                readme = "## Resumen\n\nNo hay resumen disponible para este artículo.\n\n"
                
            readme += "## Autores e Instituciones\n\n"
            for auth in work.get('authorships', []):
                aname = auth.get('author', {}).get('display_name', 'Unknown')
                inst = [i.get('display_name') for i in auth.get('institutions', [])]
                if inst:
                    readme += f"- **{aname}** ({', '.join(inst)})\n"
                else:
                    readme += f"- **{aname}**\n"
                    
            tree = [a.get('author', {}).get('display_name', 'Unknown') + ".author" for a in work.get('authorships', [])]
            
            topics = work.get('topics', [])
            total_score = sum([t.get('score', 0) for t in topics])
            if total_score > 0:
                for t in topics:
                    languages[t.get('display_name')] = int((t.get('score', 0) / total_score) * 100)
    except requests.exceptions.RequestException:
        pass

    return _generar_pdf(request.user, repo, languages, tree, readme, 'OpenAlex')

def _language_bars(languages):
    """Lista ordenada de lenguajes con el ancho de barra relativo al mayor.

    La API de GitHub devuelve bytes y las de GitLab/OpenAlex porcentajes
    (suman ~100), por eso se distingue por el total.
    """
    if not languages:
        return []
    total = sum(languages.values())
    maximo = max(languages.values())
    en_bytes = total > 101
    bars = []
    for name, value in sorted(languages.items(), key=lambda kv: kv[1], reverse=True):
        bars.append({
            'name': name,
            'label': f"{value} bytes" if en_bytes else f"{round(value, 1):g}%",
            'width': round(value / maximo * 100, 1) if maximo > 0 else 0,
        })
    return bars


def _generar_pdf(user, repo, languages, tree, readme, platform):
    """Genera el PDF del CV/Portfolio usando Playwright para un renderizado HTML/CSS nativo tipo GitHub.
    Recibe los datos unificados (da igual si vienen de GitHub o GitLab) y los renderiza en un PDF."""
    from django.template.loader import render_to_string
    import markdown
    
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        error_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Error PDF</title>
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; background-color: #0d1117; color: #c9d1d9; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
                .container { background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 40px; max-width: 600px; text-align: center; box-shadow: 0 8px 24px rgba(0,0,0,0.5); }
                h1 { color: #ff7b72; margin-top: 0; }
                p { line-height: 1.6; font-size: 16px; margin-bottom: 20px; }
                .btn { display: inline-block; background-color: #238636; color: #ffffff; text-decoration: none; padding: 10px 20px; border-radius: 6px; font-weight: 500; border: 1px solid rgba(240, 246, 252, 0.1); }
                .btn:hover { background-color: #2ea043; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>⚠️ Generación de PDF no disponible</h1>
                <p>No se pudo generar el PDF en este servidor.</p>
                <p>Por favor, usa el creador de <strong>CV Unificado (El Carrito)</strong> y dale a la opción de descargar como <strong>HTML</strong>, o corre la aplicación en tu entorno local (Mac).</p>
                <a href="javascript:history.back()" class="btn">Volver Atrás</a>
            </div>
        </body>
        </html>
        """
        return HttpResponse(error_html, status=501)

    buffer = io.BytesIO()  # Creamos un archivo temporal en la memoria RAM
    
    # 1. Preprocesar Markdown
    # Convertimos el texto del README (Markdown) a código HTML para que el PDF lo entienda
    readme_html = ""
    if readme:
        readme_html = markdown.markdown(
            readme, 
            extensions=['extra', 'codehilite', 'tables', 'fenced_code']  # Soportar tablas, bloques de código, etc.
        )
    
    # 2. Procesar lenguajes (calcular porcentajes)
    processed_languages = []
    if languages:
        total = sum(languages.values())  # Suma total de bytes/líneas de código
        for lang, valor in languages.items():
            if isinstance(valor, (int, float)) and total > 0:
                pct = (valor / total * 100) if total > 100 else valor
            else:
                pct = 0
            processed_languages.append({'name': lang, 'pct': pct})
            
    # 3. Ordenar árbol de ficheros alfabéticamente
    tree_sorted = sorted(tree) if tree else []
            
    # 4. Contexto para el template
    # Preparamos todas las variables que se inyectarán en el HTML
    context = {
        'user': user,
        'proyecto': repo,
        'url': repo.get('web_url', repo.get('html_url', 'N/A')),  # GitLab usa web_url, GitHub usa html_url
        'act_date': repo.get('last_activity_at', repo.get('updated_at', 'N/A')),
        'platform': platform,
        'processed_languages': processed_languages,
        'tree': tree_sorted,
        'readme_html': readme_html,
    }

    # render_to_string() genera el HTML completo en memoria como un string de texto
    html_string = render_to_string('portfolioCV/cv_template.html', context)
    
    # 5. Renderizar el PDF usando Headless Chromium (Playwright)
    # Abre un navegador oculto, carga el HTML y le pide imprimir a PDF
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html_string, wait_until='networkidle')  # Espera a que carguen imágenes/CSS
        
        # Header/Footer content para Playwright (debe ser HTML inyectado en el PDF)
        repo_name = repo.get('name', repo.get('path', 'Repositorio'))
        header_html = f'<div style="font-size:9px; color:#57606a; text-align:right; width:100%; padding-right:15mm;">Portfolio CV — {user.username} — {platform}</div>'
        footer_html = '<div style="font-size:8px; color:#57606a; text-align:center; width:100%; border-top:1px solid #eaecef; padding-top:5px; margin:0 15mm;"><span class="pageNumber"></span> / <span class="totalPages"></span></div>'
        
        pdf_bytes = page.pdf(
            format="A4",
            print_background=True,  # Imprimir colores de fondo y CSS
            margin={'top': '25mm', 'bottom': '25mm', 'left': '15mm', 'right': '15mm'},
            display_header_footer=True,
            header_template=header_html,
            footer_template=footer_html
        )
        browser.close()

    # Escribir los bytes generados por el navegador en nuestro buffer de memoria
    buffer.write(pdf_bytes)
    buffer.seek(0)  # Rebobinar el buffer al principio para leerlo
    
    # 6. Devolver respuesta HTTP con el PDF
    filename = f"CV_{repo_name}_{platform}.pdf".replace(" ", "_")
    response = HttpResponse(buffer, content_type='application/pdf')  # Tipo MIME de PDF
    response['Content-Disposition'] = f'attachment; filename="{filename}"'  # Descargar como fichero adjunto
    return response


# ─── CV Profesional Unificado ──────────────────────────────
def _get_cv_data(user):
    """
    Recupera el estado de la 'cesta' del CV.
    Guarda los datos serializados como texto JSON en la tabla ContenidoData,
    usando un recurso especial con nombre 'cv_profesional_username'.
    """
    recurso_name = f"cv_profesional_{user.username}"
    # Busca el registro o lo crea vacío si no existe
    contenido_obj, created = ContenidoData.objects.get_or_create(
        recurso=recurso_name,
        defaults={'usuario': user.username, 'contenido': '{}'}
    )
    try:
        # Deserializar JSON (texto a diccionario Python)
        data = json.loads(contenido_obj.contenido)
    except json.JSONDecodeError:
        data = {}
        
    if not isinstance(data, dict):
        data = {}
    
    # Estructura inicial obligatoria
    if 'personal_info' not in data:
        data['personal_info'] = {'photo': '', 'name': '', 'linkedin': '', 'phone': '', 'email': '', 'about': ''}
    if 'items' not in data:
        data['items'] = []
        
    return contenido_obj, data

@login_required
def cv_builder(request):
    """Renderiza el panel de control del CV unificado (la vista de la 'cesta')"""
    contenido_obj, data = _get_cv_data(request.user)  # Lee la base de datos
    
    if request.method == 'POST':
        # El usuario ha enviado el formulario de "Información Personal"
        import base64
        if 'photo' in request.FILES:  # Si ha subido una foto
            try:
                photo_file = request.FILES['photo']
                # Convierte la foto a Base64: un string gigante que la incrusta directamente en el HTML
                photo_b64 = base64.b64encode(photo_file.read()).decode('utf-8')
                data['personal_info']['photo'] = f"data:{photo_file.content_type};base64,{photo_b64}"
            except Exception:
                pass
        
        # Guarda los textos
        data['personal_info']['name'] = request.POST.get('name', '').strip()
        data['personal_info']['linkedin'] = request.POST.get('linkedin', '').strip()
        data['personal_info']['phone'] = request.POST.get('phone', '').strip()
        data['personal_info']['email'] = request.POST.get('email', '').strip()
        data['personal_info']['about'] = request.POST.get('about', '').strip()
        
        # Vuelve a convertir el diccionario a texto JSON y lo guarda en la BD
        contenido_obj.contenido = json.dumps(data)
        contenido_obj.save()
        messages.success(request, 'Información del CV guardada correctamente.')
        return redirect('cv_builder')

    return render(request, 'portfolioCV/cv_builder.html', {
        'cv_data': data
    })

@login_required
def agregar_al_cv(request):
    """Agrega un repositorio u obra a la cesta del CV (se llama desde un formulario POST)"""
    if request.method == 'POST':
        # Se reciben los datos básicos del repositorio para añadirlos a la 'cesta'
        platform = request.POST.get('platform')
        item_id = request.POST.get('id')
        name = request.POST.get('name')
        
        if platform and item_id and name:
            contenido_obj, data = _get_cv_data(request.user)
            # Evitar duplicados (no añadir la misma repo dos veces)
            if not any(str(item['id']) == str(item_id) and item['platform'] == platform for item in data['items']):
                data['items'].append({  # Añadir al array de JSON
                    'platform': platform,
                    'id': item_id,
                    'name': name
                })
                contenido_obj.contenido = json.dumps(data)  # Guardar
                contenido_obj.save()
                messages.success(request, f'"{name}" añadido a tu CV Profesional.')
            else:
                messages.info(request, f'"{name}" ya estaba en tu CV Profesional.')
                
        # Vuelve a la página anterior (HTTP Referer) o al CV Builder si no hay
        return redirect(request.META.get('HTTP_REFERER', 'cv_builder'))
    return redirect('index')

@login_required
def agregar_resumen_ia_al_cv(request):
    """Agrega un texto generado por IA a la cesta del CV como un nuevo bloque"""
    import uuid
    if request.method == 'POST':
        content = request.POST.get('content')
        item_name = request.POST.get('name')
        
        if content and item_name:
            contenido_obj, data = _get_cv_data(request.user)
            # A diferencia de repos, se pueden añadir varios resúmenes IA (tienen UUID aleatorio)
            data['items'].append({
                'platform': 'IA Summary',
                'id': str(uuid.uuid4()),  # Genera un ID único para poder borrarlo luego
                'name': f'Resumen IA - {item_name}',
                'content': content
            })
            contenido_obj.contenido = json.dumps(data)
            contenido_obj.save()
            messages.success(request, f'Resumen de "{item_name}" añadido a tu CV Profesional.')
                
        return redirect('cv_builder')
    return redirect('index')

@login_required
def eliminar_del_cv(request):
    """Elimina un ítem específico de la cesta del CV (por su índice en el array JSON)"""
    if request.method == 'POST':
        item_uuid = request.POST.get('index')  # El botón de borrar envía el índice numérico
        try:
            index = int(item_uuid)
            contenido_obj, data = _get_cv_data(request.user)
            if 0 <= index < len(data['items']):
                removed = data['items'].pop(index)  # Elimina el ítem de esa posición
                contenido_obj.contenido = json.dumps(data)  # Guarda la cesta modificada
                contenido_obj.save()
                messages.success(request, f'"{removed["name"]}" eliminado de tu CV.')
        except (ValueError, TypeError):
            pass
            
    return redirect('cv_builder')

@login_required
def descargar_cv_completo(request):
    """
    Compila el CV profesional.
    Por cada ítem en la cesta, hace una llamada a su API correspondiente para obtener
    datos actualizados (descripción, lenguaje) y renderiza el PDF/HTML unificado.
    """
    _, data = _get_cv_data(request.user)
    profile = get_object_or_404(UserProfile, user=request.user)
    
    # 1. Enriquecer los datos: descargar info de cada repo en tiempo real
    enriched_items = []
    for item in data.get('items', []):
        try:
            nuevo_item = item.copy()
            if item['platform'] == 'GitHub':
                headers = {"Authorization": f"Bearer {profile.github_token}", "Accept": "application/vnd.github.v3+json"}
                resp = requests.get(f"{GITHUB_API_URL}/repos/{item['id']}", headers=headers, timeout=5)
                if resp.status_code == 200:
                    rdata = resp.json()
                    nuevo_item['description'] = rdata.get('description', '')
                    nuevo_item['url'] = rdata.get('html_url', '')
                    nuevo_item['language'] = rdata.get('language', '')
                    
            elif item['platform'] == 'GitLab':
                headers = {"PRIVATE-TOKEN": profile.gitlab_token}
                resp = requests.get(f"{gitlab_api_url(profile)}/projects/{item['id']}", headers=headers, timeout=5, allow_redirects=False)
                if resp.status_code == 200:
                    rdata = resp.json()
                    nuevo_item['description'] = rdata.get('description', '')
                    nuevo_item['url'] = rdata.get('web_url', '')
                    
            elif item['platform'] == 'OpenAlex':
                params = {}
                if profile.openalex_token:
                    params['api_key'] = profile.openalex_token
                resp = requests.get(f"https://api.openalex.org/works/{item['id']}", params=params, timeout=5)
                if resp.status_code == 200:
                    wdata = resp.json()
                    authors = ", ".join([a.get('author', {}).get('display_name', '') for a in wdata.get('authorships', [])])
                    nuevo_item['description'] = authors
                    nuevo_item['url'] = wdata.get('id', '')
                    nuevo_item['language'] = "Publicación OpenAlex"
            
            enriched_items.append(nuevo_item)
        except Exception:
            enriched_items.append(item)  # Si falla, añade el ítem original sin enriquecer
            
    data['items'] = enriched_items
            
    # 2. Descargar como HTML si lo pide el botón (útil cuando Playwright falla)
    if request.GET.get('format') == 'html':
        from django.template.loader import render_to_string
        import markdown
        if data['personal_info'].get('about'):
            data['personal_info']['about_html'] = markdown.markdown(data['personal_info']['about'], extensions=['fenced_code', 'tables'])
        else:
            data['personal_info']['about_html'] = ""
            
        # Parsear Markdown de los resúmenes de IA
        for item in data['items']:
            if item.get('platform') == 'IA Summary':
                item['content_html'] = markdown.markdown(item.get('content', ''), extensions=['fenced_code', 'tables'])
                
        context = {'user': request.user, 'cv': data}
        html_string = render_to_string('portfolioCV/cv_web_portfolio_template.html', context)
        response = HttpResponse(html_string, content_type='text/html; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="cv_profesional.html"'
        return response
        
    # 3. Descargar como PDF (comportamiento por defecto)
    return _generar_pdf_completo(request.user, data)


# ─── Integración Inteligencia Artificial (Gemini/Local) ────────
@login_required
def generar_resumen_gemini(request):
    """Página intermedia que muestra el formulario de chat para la IA"""
    if request.method != 'POST':
        return redirect('index')

    platform = request.POST.get('platform', '')
    item_id = request.POST.get('id', '')
    cv_type = request.POST.get('cv_type', 'extenso')  # extenso, una_pagina, tecnologia, tfg
    item_name = request.POST.get('name', 'Proyecto')
    llm_model = modelo_permitido(request)  # local o nube

    cv_type_labels = {'extenso': 'CV Extenso', 'una_pagina': 'CV de Una Página', 'tecnologia': 'CV de Tecnología', 'tfg': 'CV de TFG'}

    # Devuelve el HTML de gemini_resumen que, mediante JavaScript, llamará a la vista de streaming
    return render(request, 'portfolioCV/gemini_resumen.html', {
        'platform': platform,
        'item_id': item_id,
        'item_name': item_name,
        'cv_type': cv_type,
        'cv_type_label': cv_type_labels.get(cv_type, cv_type),
        'llm_model': llm_model,
        'used_model': llm_model,
    })


from django.http import StreamingHttpResponse

@login_required
def stream_resumen_gemini(request):
    """
    Vista de streaming para devolver chunks (trozos) de texto de la IA en tiempo real.
    Esta técnica evita timeouts en peticiones largas y crea el efecto "máquina de escribir".
    """
    if request.method != 'POST':
        return HttpResponse("Method not allowed", status=405)

    profile = get_object_or_404(UserProfile, user=request.user)

    platform = request.POST.get('platform', '')
    item_id = request.POST.get('id', '')
    cv_type = request.POST.get('cv_type', 'extenso')
    item_name = request.POST.get('name', 'Proyecto')
    llm_model = modelo_permitido(request)

    def event_stream():
        """Generador en Python (yield): va devolviendo texto a medida que la IA lo genera"""
        # 1. Recopilar contenido del repo/obra descargándolo de su API original
        contenido_texto = f"Proyecto: {item_name}\nPlataforma: {platform}\n"
        
        try:
            if platform == 'GitHub':
                headers = {"Authorization": f"Bearer {profile.github_token}", "Accept": "application/vnd.github.v3+json"}
                resp = requests.get(f"{GITHUB_API_URL}/repos/{item_id}", headers=headers, timeout=10)
                if resp.status_code == 200:
                    rdata = resp.json()
                    contenido_texto += f"Descripción: {rdata.get('description', 'N/A')}\n"
                    contenido_texto += f"Lenguaje principal: {rdata.get('language', 'N/A')}\n"
                    contenido_texto += f"URL: {rdata.get('html_url', '')}\n"
                headers_raw = {"Authorization": f"Bearer {profile.github_token}", "Accept": "application/vnd.github.v3.raw"}
                resp_r = requests.get(f"{GITHUB_API_URL}/repos/{item_id}/readme", headers=headers_raw, timeout=10)
                if resp_r.status_code == 200:
                    contenido_texto += f"\nREADME:\n{resp_r.text[:4000]}\n"

            elif platform == 'GitLab':
                headers = {"PRIVATE-TOKEN": profile.gitlab_token}
                resp = requests.get(f"{gitlab_api_url(profile)}/projects/{item_id}", headers=headers, timeout=10, allow_redirects=False)
                if resp.status_code == 200:
                    rdata = resp.json()
                    contenido_texto += f"Descripción: {rdata.get('description', 'N/A')}\n"
                    contenido_texto += f"URL: {rdata.get('web_url', '')}\n"
                    default_branch = rdata.get('default_branch', 'main')
                else:
                    default_branch = 'main'
                resp_r = requests.get(f"{gitlab_api_url(profile)}/projects/{item_id}/repository/files/README.md/raw", headers=headers, params={"ref": default_branch}, timeout=10, allow_redirects=False)
                if resp_r.status_code == 200:
                    contenido_texto += f"\nREADME:\n{resp_r.text[:4000]}\n"

            elif platform == 'OpenAlex':
                params = {}
                if profile.openalex_token:
                    params['api_key'] = profile.openalex_token
                resp = requests.get(f"https://api.openalex.org/works/{item_id}", params=params, timeout=10)
                if resp.status_code == 200:
                    wdata = resp.json()
                    contenido_texto += f"Título: {wdata.get('title', 'N/A')}\n"
                    authors = ", ".join([a.get('author', {}).get('display_name', '') for a in wdata.get('authorships', [])])
                    contenido_texto += f"Autores: {authors}\n"
                    contenido_texto += f"Año: {wdata.get('publication_year', 'N/A')}\n"
                    abs_idx = wdata.get('abstract_inverted_index')
                    if abs_idx:
                        words = {}
                        for word, pos_list in abs_idx.items():
                            for pos in pos_list:
                                words[pos] = word
                        abstract = " ".join([words[p] for p in sorted(words.keys())])
                        contenido_texto += f"\nAbstract:\n{abstract}\n"
        except Exception as e:
            yield f"Error al recuperar datos del repositorio: {str(e)}"
            return

        # 2. Configurar el Prompt (instrucción) base según el tipo de CV pedido
        prompts_map = {
            'extenso': "RESPONDE OBLIGATORIAMENTE Y SIEMPRE EN ESPAÑOL. Genera un CV/portfolio EXTENSO y detallado a partir de este proyecto. Incluye secciones: Resumen ejecutivo, Descripción del proyecto, Tecnologías utilizadas, Estructura (DEBES incluir obligatoriamente el árbol de directorios con los archivos ordenados), Competencias demostradas y Conclusiones. Sé completo y profesional.",
            'una_pagina': "RESPONDE OBLIGATORIAMENTE Y SIEMPRE EN ESPAÑOL. Genera un CV/portfolio CONCISO de UNA SOLA PÁGINA. Máximo 300 palabras. Incluye solo: Resumen breve, Tecnologías clave, y Logro principal. Sé directo y profesional.",
            'tecnologia': "RESPONDE OBLIGATORIAMENTE Y SIEMPRE EN ESPAÑOL. Genera un análisis TECNOLÓGICO detallado. Céntrate exclusivamente en: Stack técnico, Frameworks, Librerías, Herramientas de desarrollo, Arquitectura, y Buenas prácticas observadas.",
            'tfg': "RESPONDE OBLIGATORIAMENTE Y SIEMPRE EN ESPAÑOL. Genera un resumen en formato de TRABAJO FIN DE GRADO (TFG) académico. Incluye: Título, Resumen/Abstract, Introducción, Objetivos, Metodología, Tecnologías, Resultados esperados, y Conclusiones. Usa tono académico formal.",
        }
        prompt = prompts_map.get(cv_type, prompts_map['extenso'])
        prompt += f"\n\nContenido del proyecto:\n{contenido_texto}"

        try:
            if llm_model == 'local':
                # --- OPCIÓN 1: LLM LOCAL (LM STUDIO) ---
                # Petición a un servidor de IA local ejecutándose en el ordenador (ej: Qwen, Llama)
                import json
                if not profile.lm_studio_url:
                    yield "Error: Configura tu URL de LM Studio Local en los tokens."
                    return
                url = f"{profile.lm_studio_url.rstrip('/')}/v1/chat/completions"
                payload = {
                    "model": "qwen2.5-7b-instruct",  # Modelo local usado
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "stream": True  # IMPORTANTE: pedimos respuesta en streaming
                }
                resp = requests.post(url, json=payload, stream=True, timeout=180)
                if resp.status_code == 200:
                    for line in resp.iter_lines():
                        if line:
                            line_str = line.decode('utf-8')
                            if line_str.startswith('data: '):
                                data_str = line_str[6:]
                                if data_str == '[DONE]':
                                    break
                                try:
                                    data_json = json.loads(data_str)
                                    chunk = data_json.get('choices', [{}])[0].get('delta', {}).get('content', '')
                                    if chunk:
                                        yield chunk
                                except json.JSONDecodeError:
                                    pass
                else:
                    yield f"\n\nError de LM Studio ({resp.status_code}): {resp.text}"
            else:
                # --- OPCIÓN 2: LLM NUBE (NVIDIA GEMMA) ---
                # Usamos la librería oficial de OpenAI (porque NVIDIA usa API compatible)
                from openai import OpenAI
                if not profile.nvidia_api_key:
                    yield "Error: Configura tu API Key de NVIDIA en los tokens."
                    return
                
                client = OpenAI(
                  base_url="https://integrate.api.nvidia.com/v1",
                  api_key=profile.nvidia_api_key,
                )
                
                # Petición a NVIDIA
                response = client.chat.completions.create(
                  model="google/gemma-2-2b-it",
                  messages=[{"role":"user", "content": prompt}],
                  temperature=0.2,
                  top_p=0.7,
                  max_tokens=2048,
                  stream=True  # IMPORTANTE: activa el streaming
                )
                
                # Bucle: a medida que NVIDIA envía fragmentos (chunks), hacemos yield al navegador
                for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content is not None:
                        yield chunk.choices[0].delta.content
        except Exception as e:
            yield f"\n\nError al generar resumen con IA: {str(e)}"

    # Retornamos el StreamingHttpResponse, que mantiene la conexión HTTP abierta
    # y va enviando los textos según se ejecutan los "yield" en event_stream()
    return StreamingHttpResponse(event_stream(), content_type='text/plain; charset=utf-8')


def _generar_pdf_completo(user, cv_data):
    """
    Generador del PDF final para el CV Unificado.
    Carga todos los datos de la cesta, preprocesa los resúmenes IA (Markdown a HTML),
    los pasa por un template y luego captura el PDF usando Playwright.
    """
    from django.template.loader import render_to_string
    import markdown
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        error_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Error PDF</title>
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; background-color: #0d1117; color: #c9d1d9; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
                .container { background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 40px; max-width: 600px; text-align: center; box-shadow: 0 8px 24px rgba(0,0,0,0.5); }
                h1 { color: #ff7b72; margin-top: 0; }
                p { line-height: 1.6; font-size: 16px; margin-bottom: 20px; }
                .btn { display: inline-block; background-color: #238636; color: #ffffff; text-decoration: none; padding: 10px 20px; border-radius: 6px; font-weight: 500; border: 1px solid rgba(240, 246, 252, 0.1); }
                .btn:hover { background-color: #2ea043; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>⚠️ Generación de PDF no disponible</h1>
                <p>No se pudo generar el PDF en este servidor.</p>
                <p>Por favor, utiliza la opción <strong>Descargar HTML</strong> para exportar tu CV profesional desde aquí.</p>
                <a href="javascript:history.back()" class="btn">Volver Atrás</a>
            </div>
        </body>
        </html>
        """
        return HttpResponse(error_html, status=501)

    buffer = io.BytesIO()
    
    if cv_data['personal_info'].get('about'):
        cv_data['personal_info']['about_html'] = markdown.markdown(cv_data['personal_info']['about'], extensions=['fenced_code', 'tables'])
    else:
        cv_data['personal_info']['about_html'] = ""
        
    # Parse IA Summaries markdown for PDF view
    for item in cv_data['items']:
        if item.get('platform') == 'IA Summary':
            item['content_html'] = markdown.markdown(item.get('content', ''), extensions=['fenced_code', 'tables'])
    
    context = {'user': user, 'cv': cv_data}
    html_string = render_to_string('portfolioCV/cv_profesional_template.html', context)
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content(html_string, wait_until='networkidle')
            
            header_html = f'<div style="font-size:9px; color:#57606a; text-align:right; width:100%; padding-right:15mm;">CV Profesional — {user.username}</div>'
            footer_html = '<div style="font-size:8px; color:#57606a; text-align:center; width:100%; border-top:1px solid #eaecef; padding-top:5px; margin:0 15mm;"><span class="pageNumber"></span> / <span class="totalPages"></span></div>'
            
            pdf_bytes = page.pdf(
                format="A4", print_background=True,
                margin={'top': '25mm', 'bottom': '25mm', 'left': '15mm', 'right': '15mm'},
                display_header_footer=True, header_template=header_html, footer_template=footer_html
            )
            browser.close()
    except Exception as e:
        return HttpResponse(f"<h1>Error al generar PDF</h1><p>{str(e)}</p>", status=500)

    buffer.write(pdf_bytes)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="CV_Profesional_Completo.pdf"'
    return response
