"""
Generación de los PDF con Typst, sin navegador: unos 30-50 ms y pocos MB de RAM por PDF.

Seguridad:
- Los datos del usuario (nombres, descripciones, README, textos de IA) van como JSON en
  sys_inputs y nunca se pegan dentro del código Typst, así que no pueden inyectar marcado.
- El Markdown se renderiza con cmarker con raw-typst desactivado (si no, un README podría
  ejecutar código Typst con <!--raw-typst ... -->).
- Typst solo puede leer la carpeta temporal de cada PDF. Las imágenes de internet las
  descarga antes Python, solo desde hosts públicos (anti-SSRF), y se guardan allí.

Fuentes y paquetes van dentro del repo: el PDF sale igual en el Mac y en el servidor
(Ubuntu) y nunca se descarga nada al compilar.
"""
import base64
import json
import os
import re
import shutil
import tempfile
import time
from urllib.parse import urljoin

import requests
import typst

from .seguridad import recurso_publico, MAX_REDIRECCIONES

CARPETA_TYPST = os.path.join(os.path.dirname(__file__), 'typst')
FUENTES = os.path.join(CARPETA_TYPST, 'fuentes')      # Inter + Noto Color Emoji (la de Ubuntu)
PAQUETES = os.path.join(CARPETA_TYPST, 'paquetes')    # cmarker (Markdown → Typst)

EXTENSIONES_FOTO = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/jpg': 'jpg', 'image/gif': 'gif', 'image/webp': 'webp'}

MAX_IMAGENES_README = 15
MAX_BYTES_IMAGEN = 5 * 1024 * 1024
TIEMPO_MAXIMO_IMAGENES = 15   # segundos en total para descargar las imágenes de un README


class ErrorPDF(Exception):
    """Typst no ha podido generar el PDF."""


def _compilar(plantilla, datos, ficheros=None):
    """Compila portfolioCV/typst/<plantilla> con los datos (JSON) y los ficheros que pueda leer."""
    with tempfile.TemporaryDirectory() as carpeta:
        for typ in os.listdir(CARPETA_TYPST):  # la plantilla y las piezas que importa (comun.typ)
            if typ.endswith('.typ'):
                shutil.copy(os.path.join(CARPETA_TYPST, typ), carpeta)
        principal = os.path.join(carpeta, plantilla)
        for nombre, contenido in (ficheros or {}).items():
            with open(os.path.join(carpeta, nombre), 'wb') as f:
                f.write(contenido)
        try:
            return typst.compile(
                principal,
                root=carpeta,                       # Typst no puede leer nada fuera de aquí
                font_paths=[FUENTES],
                ignore_system_fonts=True,           # mismas fuentes en cualquier máquina
                package_path=PAQUETES,
                package_cache_path=PAQUETES,        # nunca descarga paquetes de internet
                sys_inputs={'data': json.dumps(datos)},
            )
        except Exception as e:
            raise ErrorPDF(str(e)) from e


def _tipo_imagen(contenido):
    """Extensión según los primeros bytes (no nos fiamos del Content-Type), o None."""
    if contenido.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    if contenido.startswith(b'\xff\xd8\xff'):
        return 'jpg'
    if contenido.startswith((b'GIF87a', b'GIF89a')):
        return 'gif'
    if contenido[:4] == b'RIFF' and contenido[8:12] == b'WEBP':
        return 'webp'
    if b'<svg' in contenido[:1024].lower():
        return 'svg'
    return None


def _descargar_imagen(url, limite):
    """Descarga una imagen siguiendo las redirecciones a mano y comprobando cada salto."""
    for _ in range(MAX_REDIRECCIONES + 1):
        if not recurso_publico(url) or time.monotonic() > limite:
            return None
        try:
            with requests.get(url, timeout=5, stream=True, allow_redirects=False) as r:
                if r.is_redirect and r.headers.get('location'):
                    url = urljoin(url, r.headers['location'])
                    continue
                if r.status_code != 200:
                    return None
                contenido = b''
                for trozo in r.iter_content(64 * 1024):
                    contenido += trozo
                    if len(contenido) > MAX_BYTES_IMAGEN or time.monotonic() > limite:
                        return None
                return contenido
        except requests.RequestException:
            return None
    return None


def _imagenes_readme(readme, base):
    """
    Descarga las imágenes del README. Devuelve ({src original: fichero}, {fichero: bytes}).
    Las rutas relativas (capturas del repo) se buscan en el fichero en bruto del repositorio.
    """
    fuentes = re.findall(r'!\[[^\]]*\]\(\s*<?([^)\s>]+)', readme)
    fuentes += re.findall(r'<img\b[^>]*?\bsrc\s*=\s*["\']([^"\']+)["\']', readme, flags=re.IGNORECASE)

    mapa, ficheros = {}, {}
    limite = time.monotonic() + TIEMPO_MAXIMO_IMAGENES
    for src in dict.fromkeys(fuentes):  # sin repetidas y en orden
        if len(ficheros) >= MAX_IMAGENES_README:
            break
        if src.startswith(('http://', 'https://')):
            url = src
        elif src.startswith('//'):
            url = 'https:' + src
        elif base and not src.startswith(('data:', '#')):
            url = base + re.sub(r'^\./|^/', '', src)
        else:
            continue
        contenido = _descargar_imagen(url, limite)
        extension = _tipo_imagen(contenido) if contenido else None
        if extension:
            nombre = f'img{len(ficheros)}.{extension}'
            mapa[src] = nombre
            ficheros[nombre] = contenido
    return mapa, ficheros


def _base_raw(repo, platform):
    """URL donde están los ficheros en bruto del repo, para las imágenes con ruta relativa."""
    rama = repo.get('default_branch') or 'main'
    if platform == 'GitHub' and repo.get('full_name'):
        return f"https://raw.githubusercontent.com/{repo['full_name']}/{rama}/"
    if platform == 'GitLab' and repo.get('web_url'):
        return f"{repo['web_url'].rstrip('/')}/-/raw/{rama}/"
    if platform == 'Hugging Face' and repo.get('html_url'):
        return f"{repo['html_url'].rstrip('/')}/resolve/{rama}/"
    return None


def cv_repo(user, repo, lenguajes, tree, readme, platform):
    """PDF de un repositorio u obra: datos, lenguajes ([{name, pct}]), árbol de ficheros y README."""
    readme = readme or ''
    datos = {
        'username': user.username,
        'platform': platform,
        'nombre': repo.get('name') or repo.get('path') or 'Repositorio',
        'descripcion': repo.get('description') or 'Sin descripción',
        'url': repo.get('web_url') or repo.get('html_url') or 'N/A',
        'creado': (repo.get('created_at') or 'N/A')[:10],
        'actividad': (repo.get('last_activity_at') or repo.get('updated_at') or 'N/A')[:10],
        'lenguajes': lenguajes,
        'arbol': sorted(str(f) for f in tree) if tree else [],
        'readme': readme,
        'imagenes': {},
    }
    if not readme.strip():
        return _compilar('cv_repo.typ', datos)

    datos['imagenes'], ficheros = _imagenes_readme(readme, _base_raw(repo, platform))
    try:
        return _compilar('cv_repo.typ', datos, ficheros)
    except ErrorPDF:
        if not ficheros:
            raise
        # Alguna imagen que Typst no sabe leer: mejor el PDF sin imágenes que ningún PDF
        datos['imagenes'] = {}
        return _compilar('cv_repo.typ', datos)


def cv_profesional(user, cv_data):
    """PDF del CV profesional (la cesta): datos personales, foto, Sobre mí y proyectos."""
    info = dict(cv_data.get('personal_info') or {})
    foto = info.pop('photo', '') or ''
    linkedin = (info.get('linkedin') or '').strip()
    datos = {
        'username': user.username,
        'personal_info': info,
        'linkedin_url': linkedin if linkedin.startswith(('http://', 'https://')) else 'https://' + linkedin,
        'items': [i for i in cv_data.get('items', []) if isinstance(i, dict)],
        'foto': None,
    }
    ficheros = {}
    # La foto es un data URI en base64: solo imágenes, nunca una URL externa
    if foto.startswith('data:image/') and ';base64,' in foto:
        mime, b64 = foto[5:].split(';base64,', 1)
        extension = EXTENSIONES_FOTO.get(mime)
        if extension:
            try:
                ficheros[f'foto.{extension}'] = base64.b64decode(b64)
                datos['foto'] = f'foto.{extension}'
            except ValueError:
                pass
    try:
        return _compilar('cv_profesional.typ', datos, ficheros)
    except ErrorPDF:
        if not ficheros:
            raise
        datos['foto'] = None  # una foto que Typst no sabe leer no debe impedir el PDF
        return _compilar('cv_profesional.typ', datos)
