"""
Foto de perfil: cualquier formato de imagen (JPEG, PNG, GIF, BMP, TIFF, WebP, AVIF,
HEIC de iPhone...) se convierte a WebP pequeño al subirla.

Una foto de móvil de 4 MB acababa en el CV como ~5,5 MB de base64, que se cargaba en
cada petición y engordaba el PDF y el HTML exportado. Reducida a 512 px en WebP
ocupa unos 20-50 KB y en el CV se ve igual (se muestra a 100-250 px).
"""
import base64
import io

from PIL import Image, ImageOps, UnidentifiedImageError

try:  # HEIC/HEIF (fotos de iPhone); si no está instalado, el resto de formatos sigue funcionando
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:  # pragma: no cover
    pass

LADO_MAXIMO = 512                    # px: nítida incluso en pantallas retina
CALIDAD_WEBP = 82
MAX_BYTES_SUBIDA = 15 * 1024 * 1024  # 15 MB
MAX_DATA_URI_OPTIMIZADA = 300_000    # una foto ya optimizada nunca pasa de aquí
# Una imagen de 50 megapíxeles ya es enorme para una foto de perfil; más es sospechoso
# (bomba de descompresión: un fichero pequeño que ocupa GB de RAM al abrirlo)
Image.MAX_IMAGE_PIXELS = 50_000_000


class ImagenNoValida(Exception):
    """El fichero no es una imagen que sepamos leer."""


def a_webp(contenido):
    """Bytes de cualquier imagen → bytes WebP de como mucho LADO_MAXIMO px de lado."""
    try:
        with Image.open(io.BytesIO(contenido)) as original:
            # JPEG: decodifica ya a menor resolución (una foto de 12 MP no ocupa 48 MB de RAM)
            original.draft('RGB', (LADO_MAXIMO * 2, LADO_MAXIMO * 2))
            imagen = ImageOps.exif_transpose(original)  # respeta la orientación de la cámara (primer fotograma si es animada)
            transparente = imagen.mode in ('RGBA', 'LA', 'PA') or 'transparency' in imagen.info
            # Antes de reducir: Pillow no sabe reducir modos como PNG de 16 bits o CMYK
            imagen = imagen.convert('RGBA' if transparente else 'RGB')
            imagen.thumbnail((LADO_MAXIMO, LADO_MAXIMO), Image.Resampling.LANCZOS)
            salida = io.BytesIO()
            imagen.save(salida, 'WEBP', quality=CALIDAD_WEBP)
            return salida.getvalue()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError, SyntaxError) as e:
        raise ImagenNoValida() from e


def a_data_uri_webp(contenido):
    """La foto lista para guardarla en el CV: data:image/webp;base64,..."""
    return 'data:image/webp;base64,' + base64.b64encode(a_webp(contenido)).decode('ascii')


def data_uri_a_webp(data_uri):
    """Convierte una foto ya guardada (otro formato o un WebP enorme) a WebP pequeño. '' si no es una imagen válida."""
    if not data_uri or (data_uri.startswith('data:image/webp;base64,') and len(data_uri) <= MAX_DATA_URI_OPTIMIZADA):
        return data_uri
    try:
        _, b64 = data_uri.split(';base64,', 1)
        return a_data_uri_webp(base64.b64decode(b64))
    except (ValueError, ImagenNoValida):
        return ''
