"""
Integración con Hugging Face: modelos, datasets y Spaces del usuario.

Los tres son repositorios git con README (la "model card"). Se identifican por su tipo
y su id "autor/nombre"; en la app se usa la ruta "<tipo>/<autor>/<nombre>", p. ej.
"model/eldanimh/mi-modelo".

El token es opcional: sin él se ven los repos públicos del usuario indicado en Tokens;
con él, también los privados (y no hace falta escribir el usuario).
"""
import requests

HF_URL = "https://huggingface.co"

# tipo → (endpoint de la API, prefijo en las URLs web, nombre para mostrar)
TIPOS = {
    'model': ('models', '', 'Modelo'),
    'dataset': ('datasets', 'datasets/', 'Dataset'),
    'space': ('spaces', 'spaces/', 'Space'),
}


def _headers(profile):
    if profile.huggingface_token:
        return {"Authorization": f"Bearer {profile.huggingface_token}"}
    return {}


def usuario_hf(profile):
    """El usuario de Hugging Face: el escrito en Tokens o, si no, el dueño del token"""
    if profile.huggingface_username:
        return profile.huggingface_username
    if profile.huggingface_token:
        resp = requests.get(f"{HF_URL}/api/whoami-v2", headers=_headers(profile), timeout=10)
        if resp.status_code == 200:
            return resp.json().get('name', '')
    return ''


def url_web(tipo, repo_id):
    return f"{HF_URL}/{TIPOS[tipo][1]}{repo_id}"


def listar_repos(profile, autor=None, busqueda=None):
    """
    Modelos, datasets y Spaces, del más reciente al más antiguo:
    - busqueda: los que contienen ese texto en su nombre (de cualquier autor)
    - autor: los de ese usuario
    - sin nada: los del propio usuario (el de Tokens o el dueño del token)
    """
    if busqueda:
        filtro = {"search": busqueda, "limit": 20}
    else:
        autor = autor or usuario_hf(profile)
        if not autor:
            return []
        filtro = {"author": autor, "limit": 50}
    repos = []
    for tipo, (endpoint, _, etiqueta) in TIPOS.items():
        resp = requests.get(
            f"{HF_URL}/api/{endpoint}",
            headers=_headers(profile),
            params={**filtro, "sort": "lastModified", "direction": -1, "full": "true"},
            timeout=10,
        )
        resp.raise_for_status()
        for r in resp.json():
            owner, _, name = r['id'].partition('/')
            repos.append({
                'tipo': tipo,
                'tipo_label': etiqueta,
                'id': r['id'],
                'owner': owner,
                'name': name,
                'private': r.get('private', False),
                'likes': r.get('likes', 0),
                'downloads': r.get('downloads'),
                'last_modified': r.get('lastModified', ''),
                # Lo más parecido a un "lenguaje": la tarea del modelo o el SDK del Space
                'subtitulo': r.get('pipeline_tag') or r.get('sdk') or '',
            })
    repos.sort(key=lambda r: r['last_modified'], reverse=True)
    return repos


def detalle_repo(profile, tipo, repo_id):
    """Datos del repo con los mismos nombres de campo que GitHub, para reutilizar plantillas y PDF"""
    endpoint = TIPOS[tipo][0]
    resp = requests.get(f"{HF_URL}/api/{endpoint}/{repo_id}", headers=_headers(profile), timeout=10)
    if resp.status_code != 200:
        return None
    r = resp.json()
    card = r.get('cardData') or {}
    licencia = card.get('license')
    if isinstance(licencia, list):
        licencia = ", ".join(licencia)
    return {
        'name': repo_id.split('/', 1)[-1],
        'full_name': repo_id,
        'description': r.get('description') or card.get('description') or '',
        'html_url': url_web(tipo, repo_id),
        'created_at': r.get('createdAt', ''),
        'updated_at': r.get('lastModified', ''),
        'default_branch': 'main',
        # Específico de Hugging Face
        'hf_tipo': tipo,
        'hf_tipo_label': TIPOS[tipo][2],
        'private': r.get('private', False),
        'likes': r.get('likes', 0),
        'downloads': r.get('downloads'),
        'tarea': r.get('pipeline_tag') or r.get('sdk') or '',
        'libreria': r.get('library_name', ''),
        'licencia': licencia or '',
        # Las etiquetas "técnicas" (arxiv:..., region:...) no aportan en un CV
        'tags': [t for t in r.get('tags', []) if ':' not in t][:15],
        'ficheros': [s['rfilename'] for s in r.get('siblings', []) if 'rfilename' in s],
    }


def readme_repo(profile, tipo, repo_id):
    """README del repo sin la cabecera YAML (--- ... ---) que llevan las model cards"""
    resp = requests.get(
        f"{HF_URL}/{TIPOS[tipo][1]}{repo_id}/raw/main/README.md",
        headers=_headers(profile), timeout=10,
    )
    if resp.status_code != 200:
        return ''
    texto = resp.text
    if texto.startswith('---'):
        fin = texto.find('\n---', 3)
        if fin != -1:
            texto = texto[fin + 4:].lstrip('\n')
    return texto
