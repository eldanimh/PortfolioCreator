from django.conf import settings


def flags(request):
    """Expone a todas las plantillas los flags de entorno que cambian la interfaz"""
    return {
        "SOCIAL_LOGIN": settings.SOCIAL_LOGIN,
        "ALLOW_LOCAL_LLM": settings.ALLOW_LOCAL_LLM,
        "NVIDIA_MODEL": settings.NVIDIA_MODEL,
    }
