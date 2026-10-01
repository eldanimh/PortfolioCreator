import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models

# Prefijo para distinguir valores cifrados de datos antiguos en texto plano
PREFIX = "enc::"


def _fernet():
    key = getattr(settings, "FIELD_ENCRYPTION_KEY", "")
    if not key:
        # Fallback: derivar una clave válida de SECRET_KEY
        key = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())
    return Fernet(key)


def encrypt(value):
    if not value or value.startswith(PREFIX):
        return value
    return PREFIX + _fernet().encrypt(value.encode()).decode()


def decrypt(value):
    if not value or not value.startswith(PREFIX):
        return value  # vacío o texto plano heredado
    try:
        return _fernet().decrypt(value[len(PREFIX):].encode()).decode()
    except InvalidToken:
        return ""  # clave incorrecta: tratar como token no configurado


class EncryptedCharField(models.TextField):
    """Campo de texto cifrado con Fernet; transparente para el resto del código."""

    def from_db_value(self, value, expression, connection):
        return decrypt(value)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return encrypt(value) if value else value
