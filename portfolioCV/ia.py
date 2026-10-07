"""
Proveedores de IA en la nube compatibles con la API de OpenAI.

El usuario solo tiene que pegar su API Key: el proveedor se deduce del prefijo de la
clave y se usa un modelo rápido y barato por defecto. La URL y el modelo que escriba
el usuario en Tokens tienen siempre prioridad.

Los proveedores retiran modelos de vez en cuando (gemma-2-2b-it dejó de existir el
2026-07-27): si un modelo por defecto desaparece, basta con cambiarlo aquí.
"""
import requests
from django.conf import settings

# El orden importa: los prefijos más específicos ("sk-or-", "sk-ant-") van antes que "sk-"
PROVEEDORES = [
    {'id': 'nvidia', 'nombre': 'NVIDIA', 'prefijo': 'nvapi-',
     'base_url': settings.NVIDIA_BASE_URL, 'modelo': settings.NVIDIA_MODEL},
    {'id': 'openrouter', 'nombre': 'OpenRouter', 'prefijo': 'sk-or-',
     'base_url': 'https://openrouter.ai/api/v1', 'modelo': 'google/gemini-3.5-flash-lite'},
    {'id': 'groq', 'nombre': 'Groq', 'prefijo': 'gsk_',
     'base_url': 'https://api.groq.com/openai/v1', 'modelo': 'openai/gpt-oss-20b'},
    {'id': 'anthropic', 'nombre': 'Anthropic', 'prefijo': 'sk-ant-',
     'base_url': 'https://api.anthropic.com/v1', 'modelo': 'claude-haiku-4-5'},
    {'id': 'google', 'nombre': 'Google Gemini', 'prefijo': 'AIza',
     'base_url': 'https://generativelanguage.googleapis.com/v1beta/openai', 'modelo': 'gemini-3.5-flash-lite'},
    {'id': 'xai', 'nombre': 'xAI', 'prefijo': 'xai-',
     'base_url': 'https://api.x.ai/v1', 'modelo': 'grok-4.3'},
    # "sk-" también lo usa DeepSeek: quien use DeepSeek debe poner la URL a mano
    {'id': 'openai', 'nombre': 'OpenAI', 'prefijo': 'sk-',
     'base_url': 'https://api.openai.com/v1', 'modelo': 'gpt-4.1-mini'},
]


def detectar_proveedor(api_key):
    """Devuelve el proveedor que corresponde al prefijo de la clave, o None"""
    api_key = (api_key or '').strip()
    for proveedor in PROVEEDORES:
        if api_key.startswith(proveedor['prefijo']):
            return proveedor
    return None


def _proveedor_por_url(base_url):
    url = base_url.rstrip('/')
    for proveedor in PROVEEDORES:
        if proveedor['base_url'] == url:
            return proveedor
    return None


def configuracion_ia(profile):
    """
    Resuelve qué URL y modelo usar para el usuario.
    Prioridad: lo que escribió en Tokens > lo deducido de la clave.
    Devuelve un dict con base_url, modelo, nombre y proveedor (el id, o None si es
    una URL personalizada). base_url es None si no se pudo deducir.
    """
    detectado = detectar_proveedor(profile.nvidia_api_key)
    if profile.ia_base_url:
        # URL manual: si coincide con un proveedor conocido se aprovecha su modelo por defecto
        proveedor = _proveedor_por_url(profile.ia_base_url)
        base_url = profile.ia_base_url
    else:
        proveedor = detectado
        base_url = proveedor['base_url'] if proveedor else None
    return {
        'base_url': base_url,
        'modelo': profile.ia_model or (proveedor['modelo'] if proveedor else ''),
        'nombre': proveedor['nombre'] if proveedor else 'Proveedor personalizado',
        'proveedor': proveedor['id'] if proveedor else None,
    }


def comprobar_configuracion(profile):
    """
    Revisa la configuración de IA al guardar los tokens. Devuelve un aviso (texto) si
    algo no cuadra, o None si todo parece correcto. Nunca bloquea el guardado: si el
    proveedor no responde o no deja listar modelos, no se avisa de nada.
    """
    if not profile.nvidia_api_key:
        return None
    config = configuracion_ia(profile)
    if not config['base_url']:
        return ("No reconozco el proveedor de tu API Key de IA. "
                "Indica la URL del proveedor de IA para poder usarla.")
    if not config['modelo']:
        return "Indica el modelo de IA que quieres usar con tu proveedor."
    if config['proveedor'] == 'anthropic':
        # Su listado de modelos no acepta "Bearer", solo su cabecera propia
        headers = {'x-api-key': profile.nvidia_api_key, 'anthropic-version': '2023-06-01'}
    else:
        headers = {'Authorization': f'Bearer {profile.nvidia_api_key}'}
    try:
        resp = requests.get(f"{config['base_url'].rstrip('/')}/models", headers=headers, timeout=8)
    except requests.exceptions.RequestException:
        return None
    if resp.status_code in (401, 403):
        return f"{config['nombre']} ha rechazado tu API Key de IA. Revisa que esté bien copiada."
    if resp.status_code != 200:
        return None
    try:
        modelos = {m.get('id', '') for m in resp.json().get('data', [])}
    except (ValueError, AttributeError):
        return None
    # Google antepone "models/" a los nombres
    modelos |= {m.removeprefix('models/') for m in modelos}
    if modelos and config['modelo'] not in modelos:
        return (f"El modelo «{config['modelo']}» no aparece en {config['nombre']}. "
                "Puede que lo hayan retirado: escribe otro en Modelo de IA.")
    return None
