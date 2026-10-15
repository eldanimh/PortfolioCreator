"""
Protección del servidor ante muchas descargas de PDF/HTML a la vez (2 GB de RAM, 2 vCPU).

- limitar_descargas: cada usuario, una descarga a la vez y como mucho MAX_POR_MINUTO por
  minuto. Un usuario (o un script) no puede acaparar el servidor a base de clics.
- cachear_descarga: la respuesta (PDF) se guarda en la caché de disco unos minutos por
  usuario y URL. Repetir la descarga no vuelve a llamar a las APIs ni a generar nada.
"""
import hashlib
import time
from functools import wraps

from django.contrib import messages
from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme

MAX_POR_MINUTO = 10
DURACION_MAXIMA = 120          # s: si un proceso muere a mitad, el candado caduca solo
CACHE_DESCARGAS = 15 * 60      # s que se reutiliza un PDF ya generado


def _volver(request, mensaje):
    """De vuelta a la página anterior (si es de esta web) con el aviso."""
    messages.warning(request, mensaje)
    anterior = request.META.get('HTTP_REFERER', '')
    if url_has_allowed_host_and_scheme(anterior, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(anterior)
    return redirect('cv_builder')


def limitar_descargas(vista):
    """Una descarga a la vez y MAX_POR_MINUTO por minuto, por usuario."""
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        usuario = request.user.pk
        minuto = f'descargas:{usuario}:{int(time.time() // 60)}'
        cache.add(minuto, 0, 120)
        try:
            hechas = cache.incr(minuto)
        except ValueError:  # la clave caducó justo entre add e incr
            hechas = 1
        if hechas > MAX_POR_MINUTO:
            return _volver(request, 'Has hecho muchas descargas seguidas. Espera un minuto y vuelve a intentarlo.')

        candado = f'descargando:{usuario}'
        if not cache.add(candado, 1, DURACION_MAXIMA):
            return _volver(request, 'Ya tienes una descarga en marcha. Espera a que termine.')
        try:
            return vista(request, *args, **kwargs)
        finally:
            cache.delete(candado)
    return envoltura


def respuesta_desde_cache(clave):
    """La respuesta guardada con guardar_respuesta, o None."""
    guardada = cache.get(clave)
    if guardada is None:
        return None
    contenido, tipo, disposicion = guardada
    respuesta = HttpResponse(contenido, content_type=tipo)
    if disposicion:
        respuesta['Content-Disposition'] = disposicion
    return respuesta


def guardar_respuesta(clave, respuesta, segundos=CACHE_DESCARGAS):
    """Guarda una respuesta correcta (200) para servirla de nuevo sin generarla."""
    if respuesta.status_code == 200 and not respuesta.streaming and not getattr(respuesta, 'sin_cache', False):
        cache.set(clave, (respuesta.content, respuesta['Content-Type'], respuesta.get('Content-Disposition')), segundos)


def cachear_descarga(vista):
    """Guarda el resultado por usuario y URL (cada usuario ve sus repos privados con su token)."""
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        ruta = hashlib.sha256(request.get_full_path().encode()).hexdigest()
        clave = f'descarga:{request.user.pk}:{ruta}'
        respuesta = respuesta_desde_cache(clave)
        if respuesta is None:
            respuesta = vista(request, *args, **kwargs)
            guardar_respuesta(clave, respuesta)
        return respuesta
    return envoltura
