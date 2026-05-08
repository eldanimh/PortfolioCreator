# Entrega práctica mayo

## Datos

* Nombre: Daniel Martín Hurtado
* Titulación: GISAM, Grado en Ingeniería en Sistemas Audiovisuales y Multimedia
* Cuenta en laboratorios: eldanimh
* Cuenta URJC: d.martinh.2021@alumnos.urjc.es
* Vídeo básico (URL): [VÍDEO BÁSICO](https://youtu.be/mNSdh4ArwdQ)
* Vídeo parte opcional (URL): [VÍDEO PARTE OPCIONAL](https://youtu.be/COsI5Ajd0cg)
* Despliegue (URL): [ENLACE A PYTHONANYWHERE/RENDER](https://eldanimh.pythonanywhere.com)
* Usuarios y contraseñas: testuser / testpassword123 (también se puede iniciar sesión con GitHub o Google)
* Cuenta Admin Site: admin / ovVf0YtxSpZGhIK

## Recursos y métodos HTTP

* Recurso: `/`
  * Métodos permitidos: GET, POST
* Recurso: `/registro/`
  * Métodos permitidos: GET, POST
* Recurso: `/login/`
  * Métodos permitidos: GET, POST
* Recurso: `/logout/`
  * Métodos permitidos: GET
* Recurso: `/tokens/`
  * Métodos permitidos: GET, POST
* Recurso: `/gitlab/`
  * Métodos permitidos: GET
* Recurso: `/gitlab/<int:repo_id>/`
  * Métodos permitidos: GET
* Recurso: `/github/`
  * Métodos permitidos: GET
* Recurso: `/github/<str:owner>/<str:repo_name>/`
  * Métodos permitidos: GET
* Recurso: `/openalex/`
  * Métodos permitidos: GET
* Recurso: `/openalex/<str:work_id>/`
  * Métodos permitidos: GET
* Recurso: `/mi-cv/`
  * Métodos permitidos: GET, POST
* Recurso: `/mi-cv/add/`
  * Métodos permitidos: POST
* Recurso: `/mi-cv/add-ia/`
  * Métodos permitidos: POST
* Recurso: `/mi-cv/remove/`
  * Métodos permitidos: POST
* Recurso: `/mi-cv/descargar/`
  * Métodos permitidos: GET
* Recurso: `/gemini/resumen/` (Página de resumen IA)
  * Métodos permitidos: POST
* Recurso: `/gemini/stream/` (Endpoint streaming NVIDIA/OpenAI)
  * Métodos permitidos: POST
* Recurso: `/accounts/github/login/` (OAuth GitHub - django-allauth)
  * Métodos permitidos: GET
* Recurso: `/accounts/google/login/` (OAuth Google - django-allauth)
  * Métodos permitidos: GET
* Recurso: `/<str:recurso>/eliminar/`
  * Métodos permitidos: POST
* Recurso: `/<str:recurso>/`
  * Métodos permitidos: GET

## Resumen parte obligatoria

Se ha implementado una aplicación web "Portfolio Creator" orientada a extraer repositorios y documentos de plataformas externas (GitHub, GitLab URJC y OpenAlex) para confeccionar un currículum o portfolio profesional unificado.

Se ha cubierto más del 80% del temario del curso aplicando los siguientes conceptos:
- **Modelos y Base de Datos:** Uso de SQLite con modelos relacionales extendiendo el modelo nativo (`UserProfile` con relación `OneToOneField`) y tablas genéricas (`ContenidoData`) almacenando estructuras JSON avanzadas.
- **Formularios y Validación:** Uso de formularios de Django (`ModelForm`, `UserCreationForm`) con validación de datos, manejo de errores y protección contra ataques CSRF.
- **Autenticación y Sesiones:** Sistema completo de registro, login y logout con validación de errores en español. Protección estricta de rutas con `@login_required` y manejo de información efímera mediante `request.session`. Integración de **django-allauth** para login social con **GitHub y Google** (OAuth 2.0).
- **Plantillas y HTML:** Arquitectura de plantillas anidadas (herencia de `base.html`), uso intensivo de *tags* lógicos de Django, paso de contextos complejos, renderizado dinámico del DOM y saludo personalizado al usuario en la barra de navegación.
- **Integraciones HTTP (APIs REST):** Consumo de APIs externas utilizando la librería `requests`. Se han manejado peticiones GET y POST con autenticación basada en *Bearer Tokens* y cabeceras *PRIVATE-TOKEN* para conexiones seguras con GitHub, GitLab y OpenAlex.

## Lista partes opcionales

* **Motor Generativo de IA (NVIDIA Gemma 2 / LM Studio):** Integración avanzada de Inteligencia Artificial (en la nube y local) mediante el protocolo de `openai`. La aplicación es capaz de realizar lecturas contextuales de código fuente o metadatos científicos para redactar resúmenes profesionales y estéticos en formato Markdown.
* **Streaming de Respuestas HTTP:** La redacción de textos mediante IA se transmite al cliente en vivo (*streaming*) gracias al uso de generadores (`yield`) en las vistas de Django acoplados a un `StreamingHttpResponse`, evitando el bloqueo del servidor y creando un efecto visual de "máquina de escribir" muy inmersivo para el usuario final.
* **Exportación Avanzada Multipropósito (PDF y HTML):** El generador de CV no se limita a mostrar datos en pantalla; cuenta con un motor de exportación que convierte las plantillas renderizadas de Django en documentos PDF de alta fidelidad o en un archivo estático HTML 100% responsivo y autocontenido, listo para ser alojado gratuitamente en servidores como GitHub Pages.
* **Testing Automatizado Exhaustivo (Mocks):** Para garantizar la robustez, se ha desarrollado una batería de 15 pruebas unitarias (`tests.py`) que cubren autenticación, formularios y modelos. Destaca el uso avanzado de *Mocking* (`unittest.mock.patch`) para simular respuestas de red de las APIs externas y de la red neuronal de IA, logrando ejecutar la suite completa en segundos sin depender de internet y con 0 fallos detectados.
* **Login Social (OAuth 2.0):** Integración de `django-allauth` para permitir inicio de sesión con un clic mediante cuentas de **GitHub** y **Google**, con creación automática de perfil de usuario mediante signals de Django.
