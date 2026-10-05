import ipaddress
import socket
from urllib.parse import urlparse


def url_externa_segura(url):
    """True si la URL es https, sin credenciales ni parámetros, y su host
    no resuelve a una IP privada, local o reservada (evita SSRF)."""
    try:
        p = urlparse((url or "").strip())
        if p.scheme != "https" or not p.hostname:
            return False
        if p.username or p.password or p.query or p.fragment or p.port not in (None, 443):
            return False
        infos = socket.getaddrinfo(p.hostname, 443, proto=socket.IPPROTO_TCP)
    except (ValueError, socket.gaierror):
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])  # quita el scope de IPv6 (fe80::1%en0)
        if ip.version == 6 and ip.ipv4_mapped:                  # ::ffff:127.0.0.1 → 127.0.0.1
            ip = ip.ipv4_mapped
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                or ip.is_multicast or ip.is_unspecified):
            return False
    return bool(infos)
