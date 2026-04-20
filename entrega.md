# Entrega — Trabajo Final LTAW

## Fases realizadas

### Fase 1: Configuración del proyecto
- Creación del entorno virtual `venv-django`
- Creación del proyecto Django `PortfolioGenerator`
- Creación de la app `portfolioCV`
- Configuración de `settings.py` (idioma, zona horaria, app registrada)

### Fase 2: Modelos y base de datos
- Modelo `UserProfile`: perfil extendido con tokens de GitHub y GitLab URJC
- Modelo `ContenidoData`: tabla de contenidos/recursos con campos según especificación
- Migraciones ejecutadas con SQLite3

### Fase 3: Autenticación
- Sistema de registro de usuarios con Django Auth
- Inicio/cierre de sesión
- Protección de vistas con `@login_required`
- Formulario de configuración de tokens API

### Fase 4: Integración con APIs
- Integración con API de GitLab URJC (`https://gitlab.eif.urjc.es/api/v4`)
  - Listado de repositorios propios
  - Detalle de repositorio (info + lenguajes)
- Integración con API de GitHub (`https://api.github.com`)
  - Listado de repositorios propios
  - Detalle de repositorio (info + lenguajes)

### Fase 5: Generación de CV en PDF
- Generación de CV/Portfolio en PDF con ReportLab
- Descarga directa del PDF desde la vista de detalle del repositorio
- Diseño profesional del PDF con colores, barras de progreso de lenguajes y secciones

### Fase 6: Recursos genéricos
- CRUD de recursos: crear, ver detalle, eliminar
- Conversor `<str:recurso>` en URLs
- Manejo de error 404 personalizado

### Fase 7: Diseño y CSS
- CSS profesional y elegante
- Diseño responsive
- Tarjetas de plataforma con iconos y efectos hover
- Formularios estilizados
- Sistema de alertas/mensajes
