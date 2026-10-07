import ipaddress
import socket
from urllib.parse import urljoin, urlparse


def _host_publico(hostname, port):
    """True si el host resuelve solo a IPs públicas (ni privadas, ni locales, ni reservadas)"""
    try:
        infos = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
    except (ValueError, socket.gaierror, UnicodeError):
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])  # quita el scope de IPv6 (fe80::1%en0)
        if ip.version == 6 and ip.ipv4_mapped:                  # ::ffff:127.0.0.1 → 127.0.0.1
            ip = ip.ipv4_mapped
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                or ip.is_multicast or ip.is_unspecified):
            return False
    return bool(infos)


def url_externa_segura(url):
    """True si la URL es https, sin credenciales ni parámetros, y su host
    no resuelve a una IP privada, local o reservada (evita SSRF)."""
    try:
        p = urlparse((url or "").strip())
        if p.scheme != "https" or not p.hostname:
            return False
        if p.username or p.password or p.query or p.fragment or p.port not in (None, 443):
            return False
    except ValueError:
        return False
    return _host_publico(p.hostname, 443)


def recurso_publico(url):
    """Versión más permisiva para lo que carga el PDF (imágenes, badges...): admite
    http/https y parámetros, pero el host tiene que ser público igualmente."""
    try:
        p = urlparse(url or "")
        if p.scheme not in ("http", "https") or not p.hostname or p.username or p.password:
            return False
        puerto = p.port or (443 if p.scheme == "https" else 80)
    except ValueError:
        return False
    return _host_publico(p.hostname, puerto)


MAX_REDIRECCIONES = 5


def pagina_pdf_segura(browser):
    """
    Página de Playwright para convertir HTML a PDF sin riesgos: el HTML incluye el README
    de cualquier repositorio público, que puede traer <script>, <iframe> o imágenes que
    apunten a direcciones internas del servidor (p. ej. los metadatos de AWS).
    - JavaScript desactivado.
    - Cada petición (y cada redirección) solo sale si va a un host público.
    """
    page = browser.new_page(java_script_enabled=False)

    def filtrar(route):
        url = route.request.url
        for _ in range(MAX_REDIRECCIONES + 1):
            if not recurso_publico(url):
                return route.abort()
            try:
                # max_redirects=0: las redirecciones se siguen a mano para revisar cada salto
                respuesta = route.fetch(url=url, max_redirects=0, timeout=10000)
            except Exception:
                return route.abort()
            if 300 <= respuesta.status < 400 and respuesta.headers.get("location"):
                url = urljoin(url, respuesta.headers["location"])
                continue
            return route.fulfill(response=respuesta)
        return route.abort()

    page.route("**/*", filtrar)
    return page
