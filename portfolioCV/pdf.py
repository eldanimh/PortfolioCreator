"""
Conversión de HTML a PDF con Chromium (Playwright), limitada para un servidor pequeño.

Cada PDF arranca un Chromium que ocupa 150-250 MB de RAM. Con 2 GB, varios a la vez
pueden tumbar el servidor, así que como máximo se generan MAX_PDFS_SIMULTANEOS a la vez
entre TODOS los procesos de gunicorn (un candado de fichero por hueco), y el resto espera.
"""
import fcntl
import os
import tempfile
import time

from .seguridad import pagina_pdf_segura

MAX_PDFS_SIMULTANEOS = 2
ESPERA_MAXIMA_HUECO = 30      # segundos esperando a que quede un hueco libre
TIMEOUT_PAGINA_MS = 20000     # tiempo máximo para cargar el HTML (imágenes incluidas)
MARGENES = {'top': '25mm', 'bottom': '25mm', 'left': '15mm', 'right': '15mm'}
# Ahorro de memoria en Docker: /dev/shm suele ser de 64 MB y Chromium lo agota
ARGS_CHROMIUM = ['--disable-dev-shm-usage', '--disable-gpu', '--disable-extensions']


class ServidorOcupado(Exception):
    """No ha quedado ningún hueco libre para generar el PDF a tiempo."""


def _ocupar_hueco():
    """Devuelve el fichero bloqueado de un hueco libre; esperando como mucho ESPERA_MAXIMA_HUECO."""
    limite = time.monotonic() + ESPERA_MAXIMA_HUECO
    while True:
        for i in range(MAX_PDFS_SIMULTANEOS):
            ruta = os.path.join(tempfile.gettempdir(), f'portfoliocv-pdf-{i}.lock')
            fichero = open(ruta, 'w')
            try:
                fcntl.flock(fichero, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return fichero  # el candado se libera al cerrar el fichero (o si muere el proceso)
            except BlockingIOError:
                fichero.close()
        if time.monotonic() > limite:
            raise ServidorOcupado()
        time.sleep(0.2)


def html_a_pdf(html_string, header_html, footer_html):
    """Renderiza el HTML a un PDF A4 con cabecera y pie. Lanza ServidorOcupado si no hay hueco."""
    from playwright.sync_api import sync_playwright

    hueco = _ocupar_hueco()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=ARGS_CHROMIUM)
            try:
                page = pagina_pdf_segura(browser)  # Sin JavaScript ni peticiones a la red interna
                page.set_default_timeout(TIMEOUT_PAGINA_MS)
                # 'load' ya espera a imágenes y CSS; 'networkidle' añadía 500 ms de espera fija
                page.set_content(html_string, wait_until='load')
                return page.pdf(
                    format="A4",
                    print_background=True,  # Imprimir colores de fondo y CSS
                    margin=MARGENES,
                    display_header_footer=True,
                    header_template=header_html,
                    footer_template=footer_html,
                )
            finally:
                browser.close()
    finally:
        hueco.close()

