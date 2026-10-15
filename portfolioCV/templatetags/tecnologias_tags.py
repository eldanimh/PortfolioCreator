"""Logo oficial de un lenguaje en las páginas de la web: {% load tecnologias_tags %}."""
from django import template
from django.utils.html import format_html

from portfolioCV import tecnologias

register = template.Library()


@register.simple_tag
def logo_tec(lenguaje):
    """SVG del logo con el color de marca (legible en modo claro y oscuro), o '' si no lo tenemos."""
    datos = tecnologias.icono(lenguaje)
    if not datos:
        return ''
    return format_html(
        '<svg class="logo-tec" viewBox="0 0 24 24" aria-hidden="true" style="--claro: {}; --oscuro: {};"><path d="{}"/></svg>',
        datos['claro'], datos['oscuro'], datos['path'],
    )
