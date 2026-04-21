import io
import json
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, Http404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from .models import UserProfile, ContenidoData
from .forms import RegistroForm, TokensForm, ContenidoForm

# ─── API URLs ───────────────────────────────────────────────
GITLAB_URJC_URL = "https://gitlab.eif.urjc.es/api/v4"
GITHUB_API_URL = "https://api.github.com"


# ─── Página principal ──────────────────────────────────────
def index(request):
    """Página principal con dos apartados: GitLab URJC y GitHub"""
    contenidos = ContenidoData.objects.all()

    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, 'Debes iniciar sesión para crear recursos.')
            return redirect('login')
        form = ContenidoForm(request.POST)
        if form.is_valid():
            contenido = form.save(commit=False)
            contenido.usuario = request.user
            contenido.save()
            messages.success(request, f'Recurso "{contenido.recurso}" creado correctamente.')
            return redirect('index')
    else:
        form = ContenidoForm()

    return render(request, 'portfolioCV/index.html', {
        'contenidos': contenidos,
        'form': form,
    })


# ─── Detalle de recurso ────────────────────────────────────
def detalle_recurso(request, recurso):
    """Muestra el contenido de un recurso específico"""
    try:
        contenido = ContenidoData.objects.get(recurso=recurso)
    except ContenidoData.DoesNotExist:
        return render(request, 'portfolioCV/404.html', {
            'recurso': recurso,
        }, status=404)

    return render(request, 'portfolioCV/detalle.html', {
        'contenido': contenido,
    })


# ─── Eliminar recurso ──────────────────────────────────────
@login_required
def eliminar_recurso(request, recurso):
    """Elimina un recurso de la base de datos"""
    contenido = get_object_or_404(ContenidoData, recurso=recurso)
    contenido.delete()
    messages.success(request, f'Recurso "{recurso}" eliminado correctamente.')
    return redirect('index')


# ─── Autenticación ─────────────────────────────────────────
def registro_view(request):
    """Registro de nuevo usuario"""
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user)
            login(request, user)
            messages.success(request, '¡Cuenta creada correctamente! Configura tus tokens.')
            return redirect('configurar_tokens')
    else:
        form = RegistroForm()
    return render(request, 'portfolioCV/registro.html', {'form': form})


def login_view(request):
    """Inicio de sesión"""
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Crear perfil si no existe
            UserProfile.objects.get_or_create(user=user)
            messages.success(request, f'¡Bienvenido, {user.username}!')
            return redirect('index')
    else:
        form = AuthenticationForm()
    return render(request, 'portfolioCV/login.html', {'form': form})


def logout_view(request):
    """Cerrar sesión"""
    logout(request)
    messages.info(request, 'Has cerrado sesión correctamente.')
    return redirect('index')


# ─── Configurar tokens ─────────────────────────────────────
@login_required
def configurar_tokens(request):
    """Página para configurar los tokens de GitHub y GitLab"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = TokensForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, '¡Tokens actualizados correctamente!')
            return redirect('index')
    else:
        form = TokensForm(instance=profile)
    return render(request, 'portfolioCV/tokens.html', {'form': form})


# ─── GitLab URJC - Repositorios ────────────────────────────
@login_required
def gitlab_repos(request):
    """Lista los repositorios del usuario en GitLab URJC"""
    profile = get_object_or_404(UserProfile, user=request.user)

    if not profile.gitlab_token:
        messages.warning(request, 'Configura tu token de GitLab URJC primero.')
        return redirect('configurar_tokens')

    headers = {"PRIVATE-TOKEN": profile.gitlab_token}
    repos = []
    error_msg = None

    try:
        response = requests.get(
            f"{GITLAB_URJC_URL}/projects",
            headers=headers,
            params={"owned": True, "per_page": 50},
            timeout=10
        )
        if response.status_code == 200:
            repos = response.json()
        else:
            error_msg = f"Error al conectar con GitLab URJC (código {response.status_code}). Verifica tu token."
    except requests.exceptions.RequestException as e:
        error_msg = f"No se pudo conectar con GitLab URJC: {str(e)}"

    return render(request, 'portfolioCV/gitlab_repos.html', {
        'repos': repos,
        'error_msg': error_msg,
        'platform': 'GitLab URJC',
    })


# ─── GitHub - Repositorios ─────────────────────────────────
@login_required
def github_repos(request):
    """Lista los repositorios del usuario en GitHub"""
    profile = get_object_or_404(UserProfile, user=request.user)

    if not profile.github_token:
        messages.warning(request, 'Configura tu token de GitHub primero.')
        return redirect('configurar_tokens')

    headers = {
        "Authorization": f"Bearer {profile.github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    repos = []
    error_msg = None

    try:
        response = requests.get(
            f"{GITHUB_API_URL}/user/repos",
            headers=headers,
            params={"per_page": 50, "sort": "updated"},
            timeout=10
        )
        if response.status_code == 200:
            repos = response.json()
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
    """Busca bibliografías e información utilizando OpenAlex API"""
    profile = get_object_or_404(UserProfile, user=request.user)
    query = request.GET.get('search', '').strip()
    
    repos = []
    error_msg = None

    if query:
        url = "https://api.openalex.org/works"
        params = {"search": query, "per_page": 30}
        if profile.openalex_token:
            params["api_key"] = profile.openalex_token
            
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                for work in results:
                    authors = ", ".join([a.get('author', {}).get('display_name', '') for a in work.get('authorships', [])])
                    repos.append({
                        'id': work.get('id', '').split('/')[-1],
                        'name': work.get('title', 'Sin título')[:100],
                        'description': authors,
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
        'query': query
    })

@login_required
def openalex_repo_detalle(request, work_id):
    """Muestra detalle de una obra científica y permite generar CV"""
    profile = get_object_or_404(UserProfile, user=request.user)
    repo = None
    languages = {}
    error_msg = None
    
    url = f"https://api.openalex.org/works/{work_id}"
    params = {}
    if profile.openalex_token:
        params["api_key"] = profile.openalex_token
        
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            work = resp.json()
            repo = {
                'name': work.get('title', 'Sin título'),
                'description': f"Publicado en {work.get('publication_year', 'Desconocido')}",
                'web_url': work.get('id'),
                'created_at': work.get('publication_date'),
                'default_branch': work.get('type', 'N/A')
            }
            topics = work.get('topics', [])
            total_score = sum([t.get('score', 0) for t in topics])
            if total_score > 0:
                for t in topics:
                    languages[t.get('display_name')] = int((t.get('score', 0) / total_score) * 100)
            else:
                languages = {work.get('language', 'N/A'): 100}
        else:
            error_msg = f"Obra no encontrada (Error {resp.status_code})"
    except requests.exceptions.RequestException as e:
        error_msg = str(e)

    return render(request, 'portfolioCV/repo_detalle.html', {
        'repo': repo,
        'languages': languages,
        'error_msg': error_msg,
        'platform': 'OpenAlex',
        'work_id': work_id,
    })



# ─── Detalle de repo GitLab ────────────────────────────────
@login_required
def gitlab_repo_detalle(request, repo_id):
    """Muestra detalle de un repo de GitLab y permite generar CV"""
    profile = get_object_or_404(UserProfile, user=request.user)
    headers = {"PRIVATE-TOKEN": profile.gitlab_token}
    repo = None
    languages = {}
    error_msg = None

    try:
        # Obtener info del proyecto
        resp = requests.get(f"{GITLAB_URJC_URL}/projects/{repo_id}", headers=headers, timeout=10)
        if resp.status_code == 200:
            repo = resp.json()

        # Obtener lenguajes
        resp_lang = requests.get(f"{GITLAB_URJC_URL}/projects/{repo_id}/languages", headers=headers, timeout=10)
        if resp_lang.status_code == 200:
            languages = resp_lang.json()
    except requests.exceptions.RequestException as e:
        error_msg = str(e)

    return render(request, 'portfolioCV/repo_detalle.html', {
        'repo': repo,
        'languages': languages,
        'error_msg': error_msg,
        'platform': 'GitLab URJC',
        'repo_id': repo_id,
    })


# ─── Detalle de repo GitHub ────────────────────────────────
@login_required
def github_repo_detalle(request, owner, repo_name):
    """Muestra detalle de un repo de GitHub y permite generar CV"""
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
        'languages': languages,
        'error_msg': error_msg,
        'platform': 'GitHub',
        'owner': owner,
        'repo_name': repo_name,
    })


# ─── Generar CV en PDF ─────────────────────────────────────
@login_required
def generar_cv_gitlab(request, repo_id):
    """Genera un CV en PDF a partir de un repo de GitLab URJC"""
    profile = get_object_or_404(UserProfile, user=request.user)
    headers = {"PRIVATE-TOKEN": profile.gitlab_token}

    repo = {}
    languages = {}
    tree = []
    readme = ""
    try:
        resp = requests.get(f"{GITLAB_URJC_URL}/projects/{repo_id}", headers=headers, timeout=10)
        if resp.status_code == 200:
            repo = resp.json()
        
        default_branch = repo.get('default_branch', 'main')

        resp_lang = requests.get(f"{GITLAB_URJC_URL}/projects/{repo_id}/languages", headers=headers, timeout=10)
        if resp_lang.status_code == 200:
            languages = resp_lang.json()

        # Árbol de archivos
        resp_tree = requests.get(f"{GITLAB_URJC_URL}/projects/{repo_id}/repository/tree", headers=headers, params={"recursive": "true", "ref": default_branch}, timeout=10)
        if resp_tree.status_code == 200:
            tree = [item['path'] for item in resp_tree.json() if item.get('type') == 'blob']
        
        # README
        # Intentamos obtenerlo asumiendo que se llama README.md
        resp_readme = requests.get(f"{GITLAB_URJC_URL}/projects/{repo_id}/repository/files/README.md/raw", headers=headers, params={"ref": default_branch}, timeout=10)
        if resp_readme.status_code == 200:
            readme = resp_readme.text
        else:
            readme = "No se encontró README.md u ocurrió un error."

    except requests.exceptions.RequestException:
        pass

    return _generar_pdf(request.user, repo, languages, tree, readme, 'GitLab URJC')


@login_required
def generar_cv_github(request, owner, repo_name):
    """Genera un CV en PDF a partir de un repo de GitHub"""
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

        resp_lang = requests.get(f"{GITHUB_API_URL}/repos/{owner}/{repo_name}/languages", headers=headers, timeout=10)
        if resp_lang.status_code == 200:
            languages = resp_lang.json()

        # Árbol de archivos
        resp_tree = requests.get(f"{GITHUB_API_URL}/repos/{owner}/{repo_name}/git/trees/{default_branch}", headers=headers, params={"recursive": "1"}, timeout=10)
        if resp_tree.status_code == 200:
             # filtramos para obtener solo paths de archivos que no sean subárboles (blob)
            tree_data = resp_tree.json().get('tree', [])
            tree = [item['path'] for item in tree_data if item.get('type') == 'blob']
            
        # README formato RAW
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
    """Genera un PDF con formato de artículo a partir de OpenAlex usando la estructura de _generar_pdf"""
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
            
            abs_idx = work.get('abstract_inverted_index')
            if abs_idx:
                words = {}
                for word, pos_list in abs_idx.items():
                    for pos in pos_list:
                        words[pos] = word
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

def _generar_pdf(user, repo, languages, tree, readme, platform):
    """Genera el PDF del CV/Portfolio usando Playwright para un renderizado HTML/CSS nativo tipo GitHub."""
    from django.template.loader import render_to_string
    import markdown
    from playwright.sync_api import sync_playwright

    buffer = io.BytesIO()
    
    # Preprocesar Markdown
    readme_html = ""
    if readme:
        readme_html = markdown.markdown(
            readme, 
            extensions=['extra', 'codehilite', 'tables', 'fenced_code']
        )
    
    # Procesar lenguajes
    processed_languages = []
    if languages:
        total = sum(languages.values())
        for lang, valor in languages.items():
            if isinstance(valor, (int, float)) and total > 0:
                pct = (valor / total * 100) if total > 100 else valor
            else:
                pct = 0
            processed_languages.append({'name': lang, 'pct': pct})
            
    # Ordenar árbol de ficheros
    tree_sorted = sorted(tree) if tree else []
            
    # Contexto para el template
    context = {
        'user': user,
        'proyecto': repo,
        'url': repo.get('web_url', repo.get('html_url', 'N/A')),
        'act_date': repo.get('last_activity_at', repo.get('updated_at', 'N/A')),
        'platform': platform,
        'processed_languages': processed_languages,
        'tree': tree_sorted,
        'readme_html': readme_html,
    }

    html_string = render_to_string('portfolioCV/cv_template.html', context)
    
    # Render PDF using Headless Chromium
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html_string, wait_until='networkidle')
        
        # Header/Footer content para Playwright (debe ser HTML)
        repo_name = repo.get('name', repo.get('path', 'Repositorio'))
        header_html = f'<div style="font-size:9px; color:#57606a; text-align:right; width:100%; padding-right:15mm;">Portfolio CV — {user.username} — {platform}</div>'
        footer_html = '<div style="font-size:8px; color:#57606a; text-align:center; width:100%; border-top:1px solid #eaecef; padding-top:5px; margin:0 15mm;"><span class="pageNumber"></span> / <span class="totalPages"></span></div>'
        
        pdf_bytes = page.pdf(
            format="A4",
            print_background=True,
            margin={'top': '25mm', 'bottom': '25mm', 'left': '15mm', 'right': '15mm'},
            display_header_footer=True,
            header_template=header_html,
            footer_template=footer_html
        )
        browser.close()

    buffer.write(pdf_bytes)
    buffer.seek(0)
    
    filename = f"CV_{repo_name}_{platform}.pdf".replace(" ", "_")
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ─── CV Profesional Unificado ──────────────────────────────
def _get_cv_data(user):
    recurso_name = f"cv_profesional_{user.username}"
    contenido_obj, created = ContenidoData.objects.get_or_create(
        recurso=recurso_name,
        defaults={'usuario': user.username, 'contenido': '{}'}
    )
    try:
        data = json.loads(contenido_obj.contenido)
    except json.JSONDecodeError:
        data = {}
        
    if not isinstance(data, dict):
        data = {}
    
    if 'personal_info' not in data:
        data['personal_info'] = {'photo': '', 'linkedin': '', 'phone': '', 'about': ''}
    if 'items' not in data:
        data['items'] = []
        
    return contenido_obj, data

@login_required
def cv_builder(request):
    """Renderiza el panel de control del CV unificado"""
    contenido_obj, data = _get_cv_data(request.user)
    
    if request.method == 'POST':
        data['personal_info']['photo'] = request.POST.get('photo', '').strip()
        data['personal_info']['linkedin'] = request.POST.get('linkedin', '').strip()
        data['personal_info']['phone'] = request.POST.get('phone', '').strip()
        data['personal_info']['about'] = request.POST.get('about', '').strip()
        
        contenido_obj.contenido = json.dumps(data)
        contenido_obj.save()
        messages.success(request, 'Información del CV guardada correctamente.')
        return redirect('cv_builder')

    return render(request, 'portfolioCV/cv_builder.html', {
        'cv_data': data
    })

@login_required
def agregar_al_cv(request):
    """Agrega un repositorio u obra a la cesta del CV (espera un POST)"""
    if request.method == 'POST':
        platform = request.POST.get('platform')
        item_id = request.POST.get('id')
        name = request.POST.get('name')
        
        if platform and item_id and name:
            contenido_obj, data = _get_cv_data(request.user)
            # Evitar duplicados
            if not any(str(item['id']) == str(item_id) and item['platform'] == platform for item in data['items']):
                data['items'].append({
                    'platform': platform,
                    'id': item_id,
                    'name': name
                })
                contenido_obj.contenido = json.dumps(data)
                contenido_obj.save()
                messages.success(request, f'"{name}" añadido a tu CV Profesional.')
            else:
                messages.info(request, f'"{name}" ya estaba en tu CV Profesional.')
                
        return redirect(request.META.get('HTTP_REFERER', 'cv_builder'))
    return redirect('index')

@login_required
def eliminar_del_cv(request):
    """Elimina un ítem específico del CV"""
    if request.method == 'POST':
        item_uuid = request.POST.get('index')
        try:
            index = int(item_uuid)
            contenido_obj, data = _get_cv_data(request.user)
            if 0 <= index < len(data['items']):
                removed = data['items'].pop(index)
                contenido_obj.contenido = json.dumps(data)
                contenido_obj.save()
                messages.success(request, f'"{removed["name"]}" eliminado de tu CV.')
        except (ValueError, TypeError):
            pass
            
    return redirect('cv_builder')

@login_required
def descargar_cv_completo(request):
    """Compila y descarga el CV profesional con todos los ítems agregados"""
    _, data = _get_cv_data(request.user)
    profile = get_object_or_404(UserProfile, user=request.user)
    
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
                    
            elif item['platform'] == 'GitLab URJC':
                headers = {"PRIVATE-TOKEN": profile.gitlab_token}
                resp = requests.get(f"{GITLAB_URJC_URL}/projects/{item['id']}", headers=headers, timeout=5)
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
            enriched_items.append(item)
            
    data['items'] = enriched_items
            
    return _generar_pdf_completo(request.user, data)


def _generar_pdf_completo(user, cv_data):
    """Generador subyacente de PDF para el CV Unificado usando Playwright"""
    from django.template.loader import render_to_string
    import markdown
    from playwright.sync_api import sync_playwright

    buffer = io.BytesIO()
    
    if cv_data['personal_info'].get('about'):
        cv_data['personal_info']['about_html'] = markdown.markdown(cv_data['personal_info']['about'])
    else:
        cv_data['personal_info']['about_html'] = ""
    
    context = {'user': user, 'cv': cv_data}
    html_string = render_to_string('portfolioCV/cv_profesional_template.html', context)
    
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

    buffer.write(pdf_bytes)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="CV_Profesional_Completo.pdf"'
    return response
