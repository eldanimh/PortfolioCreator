from django.urls import path
from . import views

urlpatterns = [
    # Página principal
    path('', views.index, name='index'),

    # Autenticación
    path('registro/', views.registro_view, name='registro'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Configuración de tokens
    path('tokens/', views.configurar_tokens, name='configurar_tokens'),

    # GitLab URJC
    path('gitlab/', views.gitlab_repos, name='gitlab_repos'),
    path('gitlab/<int:repo_id>/', views.gitlab_repo_detalle, name='gitlab_repo_detalle'),
    path('gitlab/<int:repo_id>/cv/', views.generar_cv_gitlab, name='generar_cv_gitlab'),

    # GitHub
    path('github/', views.github_repos, name='github_repos'),
    path('github/<str:owner>/<str:repo_name>/', views.github_repo_detalle, name='github_repo_detalle'),
    path('github/<str:owner>/<str:repo_name>/cv/', views.generar_cv_github, name='generar_cv_github'),

    # OpenAlex API
    path('openalex/', views.openalex_repos, name='openalex_repos'),
    path('openalex/<str:work_id>/', views.openalex_repo_detalle, name='openalex_repo_detalle'),
    path('openalex/<str:work_id>/cv/', views.generar_cv_openalex, name='generar_cv_openalex'),

    # CV Profesional Builder
    path('mi-cv/', views.cv_builder, name='cv_builder'),
    path('mi-cv/add/', views.agregar_al_cv, name='agregar_al_cv'),
    path('mi-cv/remove/', views.eliminar_del_cv, name='eliminar_del_cv'),
    path('mi-cv/descargar/', views.descargar_cv_completo, name='descargar_cv_completo'),

    # Gemini AI
    path('gemini/resumen/', views.generar_resumen_gemini, name='generar_resumen_gemini'),
    path('gemini/stream/', views.stream_resumen_gemini, name='stream_resumen_gemini'),

    # Recursos genéricos (debe ir al final para no interferir con las rutas anteriores)
    path('<str:recurso>/eliminar/', views.eliminar_recurso, name='eliminar_recurso'),
    path('<str:recurso>/', views.detalle_recurso, name='detalle_recurso'),
]
