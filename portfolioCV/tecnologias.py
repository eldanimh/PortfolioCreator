"""
Logos y colores oficiales de lenguajes y tecnologías para las etiquetas del CV.

Iconos de Simple Icons 16.30.0 (https://simpleicons.org, licencia CC0), solo los de
lenguajes habituales en GitHub/GitLab: portfolioCV/datos/tecnologias.json.
Algunas marcas retiraron su logo de Simple Icons (Java, C#...): se usa el más cercano
(OpenJDK, .NET) y, si no hay ninguno, la etiqueta sale sin logo.
"""
import json
import os

with open(os.path.join(os.path.dirname(__file__), 'datos', 'tecnologias.json'), encoding='utf-8') as f:
    _DATOS = json.load(f)

COLORES_PROPIOS = {'java': '#ED8B00'}  # el logo de OpenJDK es negro; Java se reconoce por su naranja


def _rgb(hexa):
    return tuple(int(hexa[i:i + 2], 16) for i in (1, 3, 5))


def _hexa(rgb):
    return '#' + ''.join(f'{max(0, min(255, round(c))):02X}' for c in rgb)


def _luminancia(rgb):
    """Luminancia relativa (WCAG): 0 = negro, 1 = blanco."""
    def canal(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (canal(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _mezcla(rgb, otro, t):
    return tuple(a + (b - a) * t for a, b in zip(rgb, otro))


def _legible(rgb, fondo_claro):
    """El color de marca, oscurecido (fondo claro) o aclarado (fondo oscuro) hasta que se lea bien."""
    color = rgb
    for _ in range(12):
        lum = _luminancia(color)
        if (fondo_claro and lum <= 0.18) or (not fondo_claro and lum >= 0.30):
            break
        color = _mezcla(color, (0, 0, 0) if fondo_claro else (255, 255, 255), 0.2)
    return _hexa(color)


def icono(lenguaje):
    """
    Datos para pintar la etiqueta de un lenguaje, o None si no tenemos su logo:
    path (SVG 24×24), color (de marca, para el fondo tintado), claro/oscuro (texto e icono
    legibles sobre fondo claro u oscuro).
    """
    clave = (lenguaje or '').strip().lower()
    slug = _DATOS['lenguajes'].get(clave)
    if not slug:
        return None
    datos = _DATOS['iconos'][slug]
    color = COLORES_PROPIOS.get(clave, datos['color'])
    rgb = _rgb(color)
    return {'path': datos['path'], 'color': color, 'claro': _legible(rgb, True), 'oscuro': _legible(rgb, False)}


def con_iconos(items):
    """Añade el logo a cada lenguaje de los ítems del CV (y al lenguaje principal si no hay lista)."""
    resultado = []
    for item in items:
        if not isinstance(item, dict):
            continue
        item = dict(item)
        if item.get('lenguajes'):
            item['lenguajes'] = [{**l, 'icono': icono(l.get('name'))} for l in item['lenguajes'] if isinstance(l, dict)]
        elif item.get('language'):
            item['lenguaje_icono'] = icono(item['language'])
        resultado.append(item)
    return resultado
