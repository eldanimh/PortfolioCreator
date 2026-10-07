# Importamos path para definir rutas URL
from django.urls import path
# Importamos las vistas de nuestra app
from . import views

# Lista de TODAS las URLs de la app portfolioCV
# Django recorre esta lista de ARRIBA a ABAJO buscando coincidencias
urlpatterns = [
    # ─── Página principal (/): muestra GitHub, GitLab, OpenAlex y Hugging Face ───
    path('', views.index, name='index'),

    # ─── Autenticación ─────────────────────────────────────────────
    path('registro/', views.registro_view, name='registro'),       # Formulario de registro
    path('login/', views.login_view, name='login'),                # Formulario de login
    path('logout/', views.logout_view, name='logout'),             # Cerrar sesión

    # ─── Configuración de tokens de API ────────────────────────────
    path('tokens/', views.configurar_tokens, name='configurar_tokens'),

    # ─── GitLab ──────────────────────────────────────────────
    path('gitlab/', views.gitlab_repos, name='gitlab_repos'),                          # Lista todos los repos
    path('gitlab/<int:repo_id>/', views.gitlab_repo_detalle, name='gitlab_repo_detalle'),  # Detalle de un repo (ID numérico)
    path('gitlab/<int:repo_id>/cv/', views.generar_cv_gitlab, name='generar_cv_gitlab'),   # Descargar PDF de ese repo

    # ─── GitHub ────────────────────────────────────────────────────
    path('github/', views.github_repos, name='github_repos'),                                       # Lista repos
    path('github/<str:owner>/<str:repo_name>/', views.github_repo_detalle, name='github_repo_detalle'),  # Detalle: /github/eldanimh/mi-repo/
    path('github/<str:owner>/<str:repo_name>/cv/', views.generar_cv_github, name='generar_cv_github'),   # PDF de ese repo

    # ─── Hugging Face (modelos, datasets y Spaces) ────────────────
    path('huggingface/', views.huggingface_repos, name='huggingface_repos'),
    path('huggingface/<str:tipo>/<str:owner>/<str:repo_name>/', views.huggingface_repo_detalle, name='huggingface_repo_detalle'),  # /huggingface/model/eldanimh/mi-modelo/
    path('huggingface/<str:tipo>/<str:owner>/<str:repo_name>/cv/', views.generar_cv_huggingface, name='generar_cv_huggingface'),

    # ─── OpenAlex API (búsqueda de bibliografía) ──────────────────
    path('openalex/', views.openalex_repos, name='openalex_repos'),                          # Buscador con query string ?search=
    path('openalex/<str:work_id>/', views.openalex_repo_detalle, name='openalex_repo_detalle'),  # Detalle de una obra
    path('openalex/<str:work_id>/cv/', views.generar_cv_openalex, name='generar_cv_openalex'),   # PDF de esa obra

    # ─── CV Profesional Builder (cesta de proyectos) ──────────────
    path('mi-cv/', views.cv_builder, name='cv_builder'),                                    # Panel del constructor de CV
    path('mi-cv/add/', views.agregar_al_cv, name='agregar_al_cv'),                          # POST: añadir repo al CV
    path('mi-cv/add-ia/', views.agregar_resumen_ia_al_cv, name='agregar_resumen_ia_al_cv'), # POST: añadir resumen IA al CV
    path('mi-cv/remove/', views.eliminar_del_cv, name='eliminar_del_cv'),                   # POST: quitar item del CV
    path('mi-cv/descargar/', views.descargar_cv_completo, name='descargar_cv_completo'),     # GET: descargar PDF/HTML del CV

    # ─── Inteligencia Artificial (NVIDIA/LM Studio) ───────────────
    path('gemini/resumen/', views.generar_resumen_gemini, name='generar_resumen_gemini'),    # POST: página del resumen IA
    path('gemini/stream/', views.stream_resumen_gemini, name='stream_resumen_gemini'),       # POST: streaming de texto IA

    # ─── Página legal ─────────────────────────────────────────────
    path('privacidad/', views.privacidad, name='privacidad'),
    path('condiciones/', views.condiciones, name='condiciones'),

    # ─── Recursos genéricos (DEBEN ir AL FINAL) ──────────────────
    # <str:recurso> captura CUALQUIER texto → si fuera antes, interceptaría /gitlab/, /github/, etc.
    path('<str:recurso>/eliminar/', views.eliminar_recurso, name='eliminar_recurso'),  # Borrar recurso
    path('<str:recurso>/', views.detalle_recurso, name='detalle_recurso'),             # Ver detalle de recurso
]
